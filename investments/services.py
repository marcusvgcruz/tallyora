"""Quote update service for the investment portfolio."""

import json
import os
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.utils import timezone

from core.models import ZERO

from .models import InvestmentAsset

B3_URL = (
    'https://cotacao.b3.com.br/mds/api/v1/DailyFluctuationHistory/{ticker}'
)
BRAPI_URL = 'https://brapi.dev/api/quote/{tickers}'
YAHOO_URL = (
    'https://query1.finance.yahoo.com/v8/finance/chart/'
    '{ticker}.SA?interval=1d&range=1d'
)
BRAPI_BATCH_SIZE = 10
SOURCE_B3 = 'b3'
SOURCE_BRAPI = 'brapi'
SOURCE_YAHOO = 'yahoo'
MANUAL_QUOTE_REASON = 'cotação manual'
NO_QUOTE_REASON = 'sem cotação na resposta da fonte'
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


class QuoteUpdaterService:
    """Refresh the quotes of the assets quoted on the Brazilian exchange.

    Only FII and STOCK assets are quoted automatically. Fixed income and
    crypto are reported as skipped because their price is typed by hand.
    Every network problem is reported in the result, never raised.
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
                result['skipped'].append({
                    'ticker': asset.ticker,
                    'reason': MANUAL_QUOTE_REASON,
                })
        if not quoted:
            return result

        prices = self._collect_prices([asset.ticker for asset in quoted])
        for asset in quoted:
            price = prices.get(asset.ticker)
            if price is None:
                result['failed'].append({
                    'ticker': asset.ticker,
                    'reason': self.errors.get(asset.ticker, NO_QUOTE_REASON),
                })
                continue
            try:
                self._store_quote(asset, price)
            except Exception as error:  # noqa: BLE001 - never leak out
                result['failed'].append({
                    'ticker': asset.ticker,
                    'reason': f'erro ao salvar: {error}',
                })
                continue
            result['updated'].append({
                'ticker': asset.ticker,
                'price': asset.current_price,
            })

        result['source'] = '+'.join(sorted(self.sources_used))
        return result

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
                batch = missing[start:start + BRAPI_BATCH_SIZE]
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
        prices = {}
        for entry in results:
            if not isinstance(entry, dict):
                continue
            symbol = str(entry.get('symbol') or '').strip().upper()
            raw_price = entry.get('regularMarketPrice')
            if not symbol or raw_price is None:
                continue
            try:
                prices[symbol] = to_price(raw_price)
            except QuoteError as error:
                self.errors[symbol] = f'brapi: {error}'
        for ticker in tickers:
            if ticker not in prices:
                self.errors.setdefault(
                    ticker,
                    'brapi: ' + NO_QUOTE_REASON,
                )
        return prices

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
