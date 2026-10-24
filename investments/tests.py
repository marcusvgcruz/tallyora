"""Tests for the portfolio profitability and the quote updater."""

import json
import urllib.error
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from users.models import CustomUser

from .models import AssetClass, InvestmentAsset
from .services import QuoteUpdaterService

ZERO = Decimal('0.00')
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
