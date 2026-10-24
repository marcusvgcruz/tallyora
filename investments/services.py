"""Quote update service for the investment portfolio."""

import json
import os
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.utils import timezone

from core.models import ZERO, to_money

from .models import InvestmentAsset

B3_URL = (
    'https://cotacao.b3.com.br/mds/api/v1/DailyFluctuationHistory/{ticker}'
)
BRAPI_URL = 'https://brapi.dev/api/quote/{tickers}'
YAHOO_URL = (
    'https://query1.finance.yahoo.com/v8/finance/chart/'
    '{ticker}.SA?interval=1d&range=1d'
)
COINGECKO_URL = (
    'https://api.coingecko.com/api/v3/simple/price'
    '?ids={coin_id}&vs_currencies=brl'
)
BRAPI_BATCH_SIZE = 10
SOURCE_B3 = 'b3'
SOURCE_BRAPI = 'brapi'
SOURCE_YAHOO = 'yahoo'
SOURCE_COINGECKO = 'coingecko'
MANUAL_QUOTE_REASON = 'cotação manual'
NO_QUOTE_REASON = 'sem cotação na resposta da fonte'
CRYPTO_UNKNOWN_REASON = 'cripto sem par conhecido no CoinGecko'
COINGECKO_TIMEOUT = 8
COINGECKO_IDS = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
    'XRP': 'ripple',
    'ADA': 'cardano',
    'DOGE': 'dogecoin',
    'LTC': 'litecoin',
    'BNB': 'binancecoin',
    'USDT': 'tether',
    'MATIC': 'matic-network',
    'DOT': 'polkadot',
    'LINK': 'chainlink',
}
ONE_HUNDRED = Decimal('100')
WEIGHT_TOLERANCE = Decimal('1.00')
ACTION_BUY = 'APORTAR'
ACTION_WAIT = 'AGUARDAR'
ACTION_HOLD = 'MANTER'
BROWSER_USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
)
PRICE_PLACES = Decimal('0.0001')


class QuoteError(Exception):
    """Failure while asking a quote provider for a price."""


def to_price(value):
    """Round a raw quote to the four decimals stored by the model."""
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise QuoteError('preço inválido na resposta da fonte')
    if not price.is_finite() or price <= ZERO:
        raise QuoteError('preço inválido na resposta da fonte')
    return price.quantize(PRICE_PLACES, rounding=ROUND_HALF_UP)


def _share(part, total):
    """Percentage of ``part`` over ``total``, zero when total is zero."""
    if total <= ZERO:
        return ZERO
    return to_money(part / total * ONE_HUNDRED)


def weight_action(weight, target):
    """Action suggested by the weight of one asset inside its class.

    The target is the equal share of the class, so one asset among four
    aims at 25%. A drift of up to one percentage point still counts as
    on target and keeps the neutral action.
    """
    if weight < target - WEIGHT_TOLERANCE:
        return ACTION_BUY
    if weight > target + WEIGHT_TOLERANCE:
        return ACTION_WAIT
    return ACTION_HOLD


def _class_weights(class_assets):
    """Weight rows of the assets of a single class."""
    total = sum(
        (asset.current_total_value for asset in class_assets),
        ZERO,
    )
    target = to_money(ONE_HUNDRED / len(class_assets))
    rows = {}
    for asset in class_assets:
        weight = _share(asset.current_total_value, total)
        rows[asset.pk] = {
            'weight': weight,
            'target': target,
            'diff': to_money(weight - target),
            'action': weight_action(weight, target),
        }
    return rows


def asset_weights(assets):
    """Map ``asset.pk`` to the weight of the asset inside its class.

    The class target is split evenly between the assets of the class,
    which is the only comparison available when the user does not type
    a weight per asset by hand.
    """
    by_class = {}
    for asset in assets:
        by_class.setdefault(asset.asset_class, []).append(asset)
    rows = {}
    for class_assets in by_class.values():
        rows.update(_class_weights(class_assets))
    return rows


def _read_json(request, timeout):
    """Fetch ``request`` and decode its body as JSON."""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as error:
        raise QuoteError(f'HTTP {error.code}')
    except urllib.error.URLError as error:
        raise QuoteError(f'falha de rede: {error.reason}')
    except (TimeoutError, OSError) as error:
        raise QuoteError(f'falha de rede: {error}')
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise QuoteError('resposta inválida da fonte')


def _b3_request(ticker):
    """Build the request for one ticker on the official B3 API."""
    url = B3_URL.format(ticker=ticker)
    return urllib.request.Request(
        url,
        headers={
            'Accept': 'application/json',
            'User-Agent': BROWSER_USER_AGENT,
        },
    )


def brapi_token():
    """Token of the free brapi.dev plan, when configured."""
    return (os.environ.get('BRAPI_TOKEN') or '').strip()


def _brapi_request(tickers):
    """Build the request for one batch of tickers on brapi.dev."""
    url = BRAPI_URL.format(tickers=','.join(tickers))
    token = brapi_token()
    if token:
        url = f'{url}?token={token}'
    return urllib.request.Request(
        url,
        headers={
            'Accept': 'application/json',
            'User-Agent': BROWSER_USER_AGENT,
        },
    )


def _yahoo_request(ticker):
    """Build the request for a single ticker on Yahoo Finance."""
    url = YAHOO_URL.format(ticker=ticker)
    return urllib.request.Request(
        url,
        headers={
            'Accept': 'application/json',
            'User-Agent': BROWSER_USER_AGENT,
        },
    )


def _coingecko_request(coin_id):
    """Build the request for one coin on the public CoinGecko API."""
    url = COINGECKO_URL.format(coin_id=coin_id)
    return urllib.request.Request(
        url,
        headers={
            'Accept': 'application/json',
            'User-Agent': BROWSER_USER_AGENT,
        },
    )


class QuoteUpdaterService:
    """Refresh the automatic quotes of the user assets.

    FII and STOCK assets are quoted on B3 (brapi and Yahoo as fallback),
    CRYPTO assets are quoted on CoinGecko and fixed income is reported
    as skipped because its price is typed by hand. Every network problem
    is reported in the result, never raised, and never overwrites the
    price already stored.
    """

    def __init__(self, user, timeout=10):
        self.user = user
        self.timeout = timeout
        self.sources_used = set()
        self.errors = {}

    def update_user_assets(self):
        """Update the quotes of the user assets and report what happened."""
        result = {
            'updated': [],
            'failed': [],
            'skipped': [],
            'source': SOURCE_B3,
        }
        assets = list(
            InvestmentAsset.objects.filter(user=self.user).order_by('ticker')
        )
        quoted = []
        for asset in assets:
            if asset.is_quoted:
                quoted.append(asset)
            else:
                result['skipped'].append(
                    {
                        'ticker': asset.ticker,
                        'reason': MANUAL_QUOTE_REASON,
                    }
                )
        if not quoted:
            return result

        prices, unknown_crypto = self._collect_all_prices(quoted)
        for ticker in unknown_crypto:
            result['skipped'].append(
                {
                    'ticker': ticker,
                    'reason': CRYPTO_UNKNOWN_REASON,
                }
            )
        self._apply_prices(quoted, prices, unknown_crypto, result)
        result['source'] = '+'.join(sorted(self.sources_used))
        return result

    def _collect_all_prices(self, assets):
        """Return ``{ticker: price}`` and the crypto tickers left out."""
        traded = [asset.ticker for asset in assets if not asset.is_crypto]
        crypto = [asset.ticker for asset in assets if asset.is_crypto]
        prices = self._collect_prices(traded) if traded else {}
        known = []
        unknown = []
        for ticker in crypto:
            if ticker in COINGECKO_IDS:
                known.append(ticker)
            else:
                unknown.append(ticker)
        prices.update(self._collect_crypto_prices(known))
        return prices, unknown

    def _apply_prices(self, assets, prices, skipped, result):
        """Persist the prices and record the assets left without one."""
        for asset in assets:
            if asset.ticker in skipped:
                continue
            price = prices.get(asset.ticker)
            if price is None:
                result['failed'].append(
                    {
                        'ticker': asset.ticker,
                        'reason': self.errors.get(
                            asset.ticker, NO_QUOTE_REASON
                        ),
                    }
                )
                continue
            try:
                self._store_quote(asset, price)
            except Exception as error:  # noqa: BLE001 - never leak out
                result['failed'].append(
                    {
                        'ticker': asset.ticker,
                        'reason': f'erro ao salvar: {error}',
                    }
                )
                continue
            result['updated'].append(
                {
                    'ticker': asset.ticker,
                    'price': asset.current_price,
                }
            )

    def _collect_crypto_prices(self, tickers):
        """Return ``{ticker: price}`` asking CoinGecko for each coin."""
        prices = {}
        for ticker in tickers:
            price = self._fetch_coingecko(ticker)
            if price is not None:
                prices[ticker] = price
                self.sources_used.add(SOURCE_COINGECKO)
        return prices

    def _fetch_coingecko(self, ticker):
        """Ask CoinGecko for the price of one crypto ticker in BRL."""
        coin_id = COINGECKO_IDS.get(ticker)
        if coin_id is None:
            return None
        timeout = min(self.timeout, COINGECKO_TIMEOUT)
        try:
            payload = _read_json(_coingecko_request(coin_id), timeout)
        except QuoteError as error:
            self._mark_error([ticker], f'coingecko: {error}')
            return None
        price = self._extract_coingecko_price(payload, coin_id)
        if price is None:
            self.errors[ticker] = 'coingecko: ' + NO_QUOTE_REASON
            return None
        return price

    @staticmethod
    def _extract_coingecko_price(payload, coin_id):
        """Read ``payload[coin_id]['brl']`` without trusting the shape."""
        if not isinstance(payload, dict):
            return None
        entry = payload.get(coin_id)
        if not isinstance(entry, dict):
            return None
        raw_price = entry.get('brl')
        if raw_price is None:
            return None
        try:
            return to_price(raw_price)
        except QuoteError:
            return None

    def _collect_prices(self, tickers):
        """Return ``{ticker: price}`` using B3, brapi and Yahoo.

        The official B3 endpoint is the primary source because it needs
        no token and keeps working when the third party APIs throttle
        the server. brapi.dev is tried only when ``BRAPI_TOKEN`` is
        configured, and Yahoo is the last resort for each missing ticker.
        """
        prices = {}
        missing = []
        for ticker in tickers:
            price = self._fetch_b3(ticker)
            if price is None:
                missing.append(ticker)
            else:
                prices[ticker] = price
                self.sources_used.add(SOURCE_B3)

        if missing and brapi_token():
            still_missing = []
            for start in range(0, len(missing), BRAPI_BATCH_SIZE):
                batch = missing[start : start + BRAPI_BATCH_SIZE]
                batch_prices = self._fetch_brapi(batch)
                if batch_prices:
                    self.sources_used.add(SOURCE_BRAPI)
                    prices.update(batch_prices)
                for ticker in batch:
                    if ticker not in batch_prices:
                        still_missing.append(ticker)
            missing = still_missing

        for ticker in missing:
            price = self._fetch_yahoo(ticker)
            if price is not None:
                self.sources_used.add(SOURCE_YAHOO)
                prices[ticker] = price
        return prices

    def _fetch_b3(self, ticker):
        """Ask the official B3 API for the last traded price."""
        try:
            payload = _read_json(_b3_request(ticker), self.timeout)
        except QuoteError as error:
            self._mark_error([ticker], f'b3: {error}')
            return None
        price = self._extract_b3_price(payload)
        if price is None:
            self.errors[ticker] = 'b3: ' + NO_QUOTE_REASON
            return None
        return price

    @staticmethod
    def _extract_b3_price(payload):
        """Read the close price of the last trade in the B3 payload."""
        if not isinstance(payload, dict):
            return None
        trading_floor = payload.get('TradgFlr')
        if not isinstance(trading_floor, dict):
            return None
        security = trading_floor.get('scty')
        if not isinstance(security, dict):
            return None
        quotes = security.get('lstQtn')
        if not isinstance(quotes, list) or not quotes:
            return None
        last = quotes[-1]
        if not isinstance(last, dict):
            return None
        raw_price = last.get('closPric')
        if raw_price is None:
            return None
        try:
            return to_price(raw_price)
        except QuoteError:
            return None

    def _fetch_brapi(self, tickers):
        """Ask brapi.dev for one batch of tickers."""
        if not tickers:
            return {}
        try:
            payload = _read_json(_brapi_request(tickers), self.timeout)
        except QuoteError as error:
            self._mark_error(tickers, f'brapi: {error}')
            return {}
        results = payload.get('results') if isinstance(payload, dict) else None
        if not isinstance(results, list):
            self._mark_error(tickers, 'brapi: resposta sem resultados')
            return {}
        prices = self._parse_brapi_results(results)
        self._mark_missing(tickers, prices)
        return prices

    def _parse_brapi_results(self, results):
        """Turn the brapi result list into a ``{ticker: price}`` map."""
        prices = {}
        for entry in results:
            symbol, price = self._read_brapi_entry(entry)
            if symbol is not None:
                prices[symbol] = price
        return prices

    def _read_brapi_entry(self, entry):
        """Read one brapi entry and record a bad price in ``errors``."""
        if not isinstance(entry, dict):
            return None, None
        symbol = str(entry.get('symbol') or '').strip().upper()
        raw_price = entry.get('regularMarketPrice')
        if not symbol or raw_price is None:
            return None, None
        try:
            return symbol, to_price(raw_price)
        except QuoteError as error:
            self.errors[symbol] = f'brapi: {error}'
            return None, None

    def _mark_missing(self, tickers, prices):
        """Record every brapi ticker that came back without a price."""
        for ticker in tickers:
            if ticker not in prices:
                self.errors.setdefault(
                    ticker,
                    'brapi: ' + NO_QUOTE_REASON,
                )

    def _fetch_yahoo(self, ticker):
        """Ask Yahoo Finance for the price of one B3 ticker."""
        try:
            payload = _read_json(_yahoo_request(ticker), self.timeout)
        except QuoteError as error:
            self._mark_error([ticker], f'yahoo: {error}')
            return None
        price = self._extract_yahoo_price(payload)
        if price is None:
            self.errors[ticker] = 'yahoo: ' + NO_QUOTE_REASON
            return None
        return price

    @staticmethod
    def _extract_yahoo_price(payload):
        """Read ``chart.result[0].meta.regularMarketPrice`` safely."""
        if not isinstance(payload, dict):
            return None
        chart = payload.get('chart')
        if not isinstance(chart, dict):
            return None
        results = chart.get('result')
        if not isinstance(results, list) or not results:
            return None
        first = results[0]
        if not isinstance(first, dict):
            return None
        meta = first.get('meta')
        if not isinstance(meta, dict):
            return None
        raw_price = meta.get('regularMarketPrice')
        if raw_price is None:
            return None
        try:
            return to_price(raw_price)
        except QuoteError:
            return None

    def _mark_error(self, tickers, reason):
        """Keep every failure reason of each ticker."""
        for ticker in tickers:
            current = self.errors.get(ticker)
            if not current:
                self.errors[ticker] = reason
            elif reason not in current:
                self.errors[ticker] = f'{current} | {reason}'

    @staticmethod
    def _store_quote(asset, price):
        """Persist the new price keeping the previous one on failure."""
        asset.current_price = price
        asset.last_quote_update = timezone.now()
        asset.save(
            update_fields=[
                'current_price',
                'last_quote_update',
                'updated_at',
            ],
        )
