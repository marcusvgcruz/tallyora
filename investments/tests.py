"""Tests for the portfolio profitability and the quote updater."""

import json
import urllib.error
from decimal import Decimal
from email.message import Message
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import CustomUser

from .models import AssetClass, InvestmentAsset
from .services import (
    ACTION_BUY,
    ACTION_HOLD,
    ACTION_WAIT,
    CRYPTO_UNKNOWN_REASON,
    QuoteUpdaterService,
    asset_weights,
    weight_action,
)

ZERO = Decimal('0.00')
COINGECKO_PAYLOAD = {'bitcoin': {'brl': 350000.5}}
# The manifest storage of the project needs ``collectstatic`` first, so
# the rendering test uses the plain storage to stay self contained.
PLAIN_STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}
B3_PAYLOAD = {
    'TradgFlr': {
        'scty': {
            'lstQtn': [{'closPric': 12.5}],
        },
    },
}


class FakeResponse:
    """Minimal stand-in for the response returned by ``urlopen``."""

    def __init__(self, payload):
        self.body = json.dumps(payload).encode('utf-8')

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def _opener(routes):
    """Build a ``urlopen`` side effect that answers by URL fragment.

    Each key of ``routes`` is a fragment of the request URL and each
    value is either a JSON payload or an exception to raise. A URL that
    matches no route raises ``AssertionError`` so an unexpected provider
    call fails the test instead of being silently answered.
    """

    def opener(request, timeout=None):
        url = request.full_url
        for fragment, answer in routes.items():
            if fragment in url:
                if isinstance(answer, Exception):
                    raise answer
                return FakeResponse(answer)
        raise AssertionError(f'url inesperada: {url}')

    return opener


class InvestmentAssetTest(TestCase):
    """Profit and loss of a single asset and of the whole portfolio."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='owner@example.com',
            password='secret123',
        )

    def _make_asset(
        self,
        ticker='HGLG11',
        quantity='10',
        average_price='100.0000',
        current_price='120.0000',
        asset_class=AssetClass.FII,
        user=None,
    ):
        return InvestmentAsset.objects.create(
            user=user or self.user,
            asset_class=asset_class,
            ticker=ticker,
            quantity=Decimal(quantity),
            average_price=Decimal(average_price),
            current_price=Decimal(current_price),
        )

    def test_profit_on_appreciated_asset(self):
        asset = self._make_asset()
        self.assertEqual(asset.total_invested, Decimal('1000.00'))
        self.assertEqual(asset.current_total_value, Decimal('1200.00'))
        self.assertEqual(asset.profit_loss_amount, Decimal('200.00'))
        self.assertEqual(
            asset.profit_loss_percentage,
            Decimal('20.00'),
        )

    def test_loss_on_depreciated_asset(self):
        asset = self._make_asset(current_price='80.0000')
        self.assertEqual(asset.current_total_value, Decimal('800.00'))
        self.assertEqual(asset.profit_loss_amount, Decimal('-200.00'))
        self.assertEqual(
            asset.profit_loss_percentage,
            Decimal('-20.00'),
        )

    def test_asset_without_cost_does_not_divide_by_zero(self):
        asset = self._make_asset(average_price='0.0000')
        self.assertEqual(asset.total_invested, ZERO)
        self.assertEqual(
            asset.current_total_value,
            Decimal('1200.00'),
        )
        self.assertEqual(asset.profit_loss_amount, Decimal('1200.00'))
        self.assertEqual(asset.profit_loss_percentage, ZERO)

    def test_asset_quoted_at_the_average_price_is_neutral(self):
        asset = self._make_asset(current_price='100.0000')
        self.assertEqual(asset.current_total_value, Decimal('1000.00'))
        self.assertEqual(asset.profit_loss_amount, ZERO)
        self.assertEqual(asset.profit_loss_percentage, ZERO)

    def test_asset_without_a_quote_shows_the_whole_cost_as_loss(self):
        """``current_price`` defaults to zero, so it reads as total loss."""
        asset = self._make_asset(current_price='0.0000')
        self.assertEqual(asset.current_total_value, ZERO)
        self.assertEqual(asset.profit_loss_amount, Decimal('-1000.00'))
        self.assertEqual(
            asset.profit_loss_percentage,
            Decimal('-100.00'),
        )

    def test_portfolio_total_sums_every_asset_of_the_user(self):
        self._make_asset(ticker='HGLG11')
        self._make_asset(
            ticker='ITSA4',
            quantity='100',
            average_price='10.0000',
            current_price='8.0000',
            asset_class=AssetClass.STOCK,
        )
        assets = InvestmentAsset.objects.filter(user=self.user)
        invested = sum(
            (asset.total_invested for asset in assets),
            ZERO,
        )
        current = sum(
            (asset.current_total_value for asset in assets),
            ZERO,
        )
        profit = sum(
            (asset.profit_loss_amount for asset in assets),
            ZERO,
        )
        self.assertEqual(invested, Decimal('2000.00'))
        self.assertEqual(current, Decimal('2000.00'))
        self.assertEqual(profit, ZERO)
        self.assertEqual(assets.count(), 2)

    def test_assets_of_another_user_stay_out_of_the_portfolio(self):
        other = CustomUser.objects.create_user(
            email='other@example.com',
            password='secret123',
        )
        mine = self._make_asset(ticker='HGLG11')
        self._make_asset(ticker='HGLG11', user=other, current_price='90.0')
        assets = InvestmentAsset.objects.filter(user=self.user)
        self.assertEqual(assets.count(), 1)
        self.assertEqual(
            sum((asset.total_invested for asset in assets), ZERO),
            mine.total_invested,
        )
        self.assertEqual(mine.total_invested, Decimal('1000.00'))
        self.assertEqual(
            sum((asset.profit_loss_amount for asset in assets), ZERO),
            Decimal('200.00'),
        )


class QuoteUpdaterServiceTest(TestCase):
    """Quote refresh with the network layer mocked out."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='owner@example.com',
            password='secret123',
        )
        self.asset = InvestmentAsset.objects.create(
            user=self.user,
            asset_class=AssetClass.FII,
            ticker='HGLG11',
            quantity=Decimal('10'),
            average_price=Decimal('100.0000'),
            current_price=Decimal('110.0000'),
        )

    def test_quote_is_updated_with_the_price_of_the_source(self):
        with patch(
            'urllib.request.urlopen',
            return_value=FakeResponse(B3_PAYLOAD),
        ):
            result = QuoteUpdaterService(
                self.user,
                timeout=1,
            ).update_user_assets()
        self.asset.refresh_from_db()
        self.assertEqual(
            self.asset.current_price,
            Decimal('12.5000'),
        )
        self.assertIsNotNone(self.asset.last_quote_update)
        self.assertEqual(
            [entry['ticker'] for entry in result['updated']],
            ['HGLG11'],
        )
        self.assertEqual(result['failed'], [])
        self.assertIn('b3', result['source'])

    def test_network_failure_keeps_the_previous_quote(self):
        error = urllib.error.URLError('network unreachable')
        with patch('urllib.request.urlopen', side_effect=error):
            result = QuoteUpdaterService(
                self.user,
                timeout=1,
            ).update_user_assets()
        self.asset.refresh_from_db()
        self.assertEqual(
            self.asset.current_price,
            Decimal('110.0000'),
        )
        self.assertIsNone(self.asset.last_quote_update)
        self.assertEqual(result['updated'], [])
        self.assertEqual(
            [entry['ticker'] for entry in result['failed']],
            ['HGLG11'],
        )
        self.assertIn(
            'falha de rede',
            result['failed'][0]['reason'],
        )

    def test_manually_priced_asset_is_skipped_without_a_request(self):
        InvestmentAsset.objects.create(
            user=self.user,
            asset_class=AssetClass.FIXED_INCOME,
            ticker='CDB2028',
            quantity=Decimal('1'),
            average_price=Decimal('1000.0000'),
            current_price=Decimal('1050.0000'),
        )
        with patch('urllib.request.urlopen') as urlopen:
            urlopen.return_value = FakeResponse(B3_PAYLOAD)
            result = QuoteUpdaterService(
                self.user,
                timeout=1,
            ).update_user_assets()
        manual = InvestmentAsset.objects.get(ticker='CDB2028')
        self.assertEqual(manual.current_price, Decimal('1050.0000'))
        self.assertIsNone(manual.last_quote_update)
        self.assertEqual(
            [entry['ticker'] for entry in result['skipped']],
            ['CDB2028'],
        )
        self.assertEqual(
            [entry['ticker'] for entry in result['updated']],
            ['HGLG11'],
        )
        self.assertEqual(urlopen.call_count, 1)

    def test_update_of_one_user_does_not_touch_the_others(self):
        other = CustomUser.objects.create_user(
            email='other@example.com',
            password='secret123',
        )
        other_asset = InvestmentAsset.objects.create(
            user=other,
            asset_class=AssetClass.STOCK,
            ticker='ITSA4',
            quantity=Decimal('10'),
            average_price=Decimal('10.0000'),
            current_price=Decimal('9.0000'),
        )
        with patch(
            'urllib.request.urlopen',
            return_value=FakeResponse(B3_PAYLOAD),
        ):
            QuoteUpdaterService(self.user, timeout=1).update_user_assets()
        other_asset.refresh_from_db()
        self.assertEqual(
            other_asset.current_price,
            Decimal('9.0000'),
        )
        self.assertIsNone(other_asset.last_quote_update)


class CryptoQuoteServiceTest(TestCase):
    """Crypto quotes coming from the public CoinGecko API."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='crypto@example.com',
            password='secret123',
        )
        self.asset = InvestmentAsset.objects.create(
            user=self.user,
            asset_class=AssetClass.CRYPTO,
            ticker='BTC',
            quantity=Decimal('0.5'),
            average_price=Decimal('200000.0000'),
            current_price=Decimal('300000.0000'),
        )

    def _update(self):
        return QuoteUpdaterService(
            self.user,
            timeout=1,
        ).update_user_assets()

    def test_coingecko_price_updates_the_crypto_asset(self):
        with patch(
            'urllib.request.urlopen',
            side_effect=_opener({'api.coingecko.com': COINGECKO_PAYLOAD}),
        ) as urlopen:
            result = self._update()
        self.asset.refresh_from_db()
        self.assertEqual(
            self.asset.current_price,
            Decimal('350000.5000'),
        )
        self.assertIsNotNone(self.asset.last_quote_update)
        self.assertEqual(
            [entry['ticker'] for entry in result['updated']],
            ['BTC'],
        )
        self.assertEqual(result['failed'], [])
        self.assertEqual(result['skipped'], [])
        self.assertEqual(result['source'], 'coingecko')
        url = urlopen.call_args.args[0].full_url
        self.assertIn('ids=bitcoin', url)
        self.assertIn('vs_currencies=brl', url)

    def test_unknown_crypto_ticker_is_skipped_without_a_request(self):
        self.asset.delete()
        asset = InvestmentAsset.objects.create(
            user=self.user,
            asset_class=AssetClass.CRYPTO,
            ticker='XYZ',
            quantity=Decimal('10'),
            average_price=Decimal('10.0000'),
            current_price=Decimal('12.0000'),
        )
        with patch('urllib.request.urlopen') as urlopen:
            result = self._update()
        asset.refresh_from_db()
        urlopen.assert_not_called()
        self.assertEqual(asset.current_price, Decimal('12.0000'))
        self.assertIsNone(asset.last_quote_update)
        self.assertEqual(
            result['skipped'],
            [{'ticker': 'XYZ', 'reason': CRYPTO_UNKNOWN_REASON}],
        )
        self.assertEqual(result['failed'], [])
        self.assertEqual(result['updated'], [])

    def test_http_error_keeps_the_previous_crypto_quote(self):
        error = urllib.error.HTTPError(
            'https://api.coingecko.com/api/v3/simple/price',
            500,
            'erro do servidor',
            Message(),
            None,
        )
        with patch('urllib.request.urlopen', side_effect=error):
            result = self._update()
        self.asset.refresh_from_db()
        self.assertEqual(
            self.asset.current_price,
            Decimal('300000.0000'),
        )
        self.assertIsNone(self.asset.last_quote_update)
        self.assertEqual(result['updated'], [])
        self.assertEqual(
            [entry['ticker'] for entry in result['failed']],
            ['BTC'],
        )
        self.assertIn('HTTP 500', result['failed'][0]['reason'])

    def test_network_error_keeps_the_previous_crypto_quote(self):
        error = urllib.error.URLError('network unreachable')
        with patch('urllib.request.urlopen', side_effect=error):
            result = self._update()
        self.asset.refresh_from_db()
        self.assertEqual(
            self.asset.current_price,
            Decimal('300000.0000'),
        )
        self.assertIsNone(self.asset.last_quote_update)
        self.assertEqual(result['updated'], [])
        self.assertEqual(
            [entry['ticker'] for entry in result['failed']],
            ['BTC'],
        )
        self.assertIn(
            'falha de rede',
            result['failed'][0]['reason'],
        )

    def test_crypto_never_asks_b3_or_yahoo(self):
        InvestmentAsset.objects.create(
            user=self.user,
            asset_class=AssetClass.FII,
            ticker='HGLG11',
            quantity=Decimal('10'),
            average_price=Decimal('100.0000'),
            current_price=Decimal('110.0000'),
        )
        routes = {
            'cotacao.b3.com.br': B3_PAYLOAD,
            'api.coingecko.com': COINGECKO_PAYLOAD,
        }
        with patch.dict('os.environ', {'BRAPI_TOKEN': ''}):
            with patch(
                'urllib.request.urlopen',
                side_effect=_opener(routes),
            ) as urlopen:
                result = self._update()
        urls = [call.args[0].full_url for call in urlopen.call_args_list]
        joined = ' '.join(urls)
        self.assertEqual(len(urls), 2)
        self.assertIn('cotacao.b3.com.br', joined)
        self.assertIn('api.coingecko.com', joined)
        self.assertNotIn('yahoo', joined)
        self.assertNotIn('brapi', joined)
        self.assertEqual(
            sorted(entry['ticker'] for entry in result['updated']),
            ['BTC', 'HGLG11'],
        )
        self.assertEqual(result['failed'], [])


class AssetWeightTest(TestCase):
    """Weight of each asset inside its own class of the portfolio."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='weights@example.com',
            password='secret123',
        )

    def _asset(self, ticker, price, asset_class=AssetClass.STOCK):
        return InvestmentAsset.objects.create(
            user=self.user,
            asset_class=asset_class,
            ticker=ticker,
            quantity=Decimal('1'),
            average_price=Decimal('100.0000'),
            current_price=Decimal(price),
        )

    def test_three_actions_inside_the_same_class(self):
        big = self._asset('AAAA3', '500.0000')
        near = self._asset('BBBB3', '340.0000')
        small = self._asset('CCCC3', '160.0000')
        rows = asset_weights([big, near, small])
        self.assertEqual(rows[big.pk]['weight'], Decimal('50.00'))
        self.assertEqual(rows[near.pk]['weight'], Decimal('34.00'))
        self.assertEqual(rows[small.pk]['weight'], Decimal('16.00'))
        self.assertEqual(rows[big.pk]['target'], Decimal('33.33'))
        self.assertEqual(rows[big.pk]['action'], ACTION_WAIT)
        self.assertEqual(rows[near.pk]['action'], ACTION_HOLD)
        self.assertEqual(rows[small.pk]['action'], ACTION_BUY)

    def test_one_percentage_point_is_the_tolerance(self):
        target = Decimal('33.33')
        cases = (
            (Decimal('34.33'), ACTION_HOLD),
            (Decimal('34.34'), ACTION_WAIT),
            (Decimal('32.33'), ACTION_HOLD),
            (Decimal('32.32'), ACTION_BUY),
        )
        for weight, expected in cases:
            with self.subTest(weight=weight):
                self.assertEqual(
                    weight_action(weight, target),
                    expected,
                )

    def test_single_asset_class_stays_on_target(self):
        asset = self._asset('HGLG11', '1000.0000', AssetClass.FII)
        rows = asset_weights([asset])
        self.assertEqual(rows[asset.pk]['weight'], Decimal('100.00'))
        self.assertEqual(rows[asset.pk]['target'], Decimal('100.00'))
        self.assertEqual(rows[asset.pk]['diff'], ZERO)
        self.assertEqual(rows[asset.pk]['action'], ACTION_HOLD)

    def test_each_class_is_compared_on_its_own(self):
        stock = self._asset('AAAA3', '500.0000')
        crypto = self._asset('BTC', '1500.0000', AssetClass.CRYPTO)
        rows = asset_weights([stock, crypto])
        self.assertEqual(rows[stock.pk]['weight'], Decimal('100.00'))
        self.assertEqual(rows[crypto.pk]['weight'], Decimal('100.00'))
        self.assertEqual(rows[stock.pk]['action'], ACTION_HOLD)
        self.assertEqual(rows[crypto.pk]['action'], ACTION_HOLD)

    @override_settings(STORAGES=PLAIN_STORAGES)
    def test_portfolio_view_exposes_the_weight_of_each_asset(self):
        asset = self._asset('HGLG11', '1000.0000', AssetClass.FII)
        self.client.force_login(self.user)
        response = self.client.get(reverse('investments:portfolio'))
        self.assertEqual(response.status_code, 200)
        rows = response.context['asset_weights']
        self.assertEqual(rows[asset.pk]['weight'], Decimal('100.00'))
        self.assertEqual(rows[asset.pk]['action'], ACTION_HOLD)
        self.assertContains(response, 'Manter')
        self.assertContains(response, 'Peso na classe')
