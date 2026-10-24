"""Tests for the event plans and the supplier balances behind them."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from users.models import CustomUser

from .models import EventExpenseItem, EventPlan

ZERO = Decimal('0.00')
COST = Decimal('1000.00')


class EventExpenseItemTest(TestCase):
    """Pending balance of one supplier inside an event plan."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='owner@example.com',
            password='secret123',
        )
        self.event = EventPlan.objects.create(
            user=self.user,
            title='Casamento',
            event_date=date(2026, 12, 1),
        )

    def _make_item(self, total_cost, amount_paid, supplier='Buffet'):
        """Create a supplier item with the given money amounts."""
        return EventExpenseItem.objects.create(
            event=self.event,
            supplier_name=supplier,
            total_cost=Decimal(total_cost),
            amount_paid=Decimal(amount_paid),
        )

    def test_partially_paid_supplier_has_partial_status(self):
        item = self._make_item('1000.00', '400.00')
        self.assertEqual(item.remaining_amount, Decimal('600.00'))
        self.assertEqual(
            item.payment_status,
            EventExpenseItem.PaymentStatus.PARTIAL,
        )

    def test_unpaid_supplier_owes_the_whole_cost(self):
        item = self._make_item('1000.00', '0.00')
        self.assertEqual(
            item.payment_status,
            EventExpenseItem.PaymentStatus.PENDING,
        )
        self.assertEqual(item.remaining_amount, COST)

    def test_fully_paid_supplier_owes_nothing(self):
        item = self._make_item('1000.00', '1000.00')
        self.assertEqual(
            item.payment_status,
            EventExpenseItem.PaymentStatus.PAID,
        )
        self.assertEqual(item.remaining_amount, ZERO)

    def test_overpayment_is_stored_as_is_by_save(self):
        """``save`` only flips the status; it never caps the paid value."""
        item = self._make_item('1000.00', '1200.00')
        item.refresh_from_db()
        self.assertEqual(item.amount_paid, Decimal('1200.00'))
        self.assertEqual(
            item.payment_status,
            EventExpenseItem.PaymentStatus.PAID,
        )
        self.assertEqual(item.remaining_amount, ZERO)

    def test_overpayment_is_rejected_by_full_clean(self):
        item = EventExpenseItem(
            event=self.event,
            supplier_name='Buffet',
            total_cost=COST,
            amount_paid=Decimal('1200.00'),
        )
        with self.assertRaises(ValidationError) as context:
            item.full_clean()
        self.assertIn('amount_paid', context.exception.message_dict)


class EventPlanBalanceTest(TestCase):
    """Consolidated balances of the event plan."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='owner@example.com',
            password='secret123',
        )
        self.event = EventPlan.objects.create(
            user=self.user,
            title='Casamento',
            event_date=date(2026, 12, 1),
        )

    def _add_supplier(self, name, total_cost, amount_paid):
        return EventExpenseItem.objects.create(
            event=self.event,
            supplier_name=name,
            total_cost=Decimal(total_cost),
            amount_paid=Decimal(amount_paid),
        )

    def test_event_totals_sum_every_supplier(self):
        self._add_supplier('Buffet', '1000.00', '400.00')
        self._add_supplier('Fotógrafo', '500.00', '500.00')
        self.assertEqual(self.event.total_cost, Decimal('1500.00'))
        self.assertEqual(self.event.total_paid, Decimal('900.00'))
        self.assertEqual(
            self.event.remaining_to_pay,
            Decimal('600.00'),
        )

    def test_amount_still_needed_discounts_what_is_saved(self):
        self._add_supplier('Buffet', '6000.00', '0.00')
        self._add_supplier('Fotógrafo', '4000.00', '0.00')
        self.event.already_saved_amount = Decimal('2500.00')
        self.event.save()
        self.assertEqual(
            self.event.remaining_to_pay,
            Decimal('10000.00'),
        )
        self.assertEqual(
            self.event.amount_still_needed,
            Decimal('7500.00'),
        )
        self.assertEqual(self.event.saved_percentage, Decimal('25.00'))

    def test_saved_percentage_never_passes_one_hundred(self):
        self._add_supplier('Buffet', '10000.00', '0.00')
        self.event.already_saved_amount = Decimal('12000.00')
        self.event.save()
        self.assertEqual(self.event.amount_still_needed, ZERO)
        self.assertEqual(
            self.event.saved_percentage,
            Decimal('100.00'),
        )

    def test_event_without_suppliers_counts_as_fully_saved(self):
        """With nothing left to pay the progress is reported as 100%."""
        self.assertEqual(self.event.remaining_to_pay, ZERO)
        self.assertEqual(self.event.amount_still_needed, ZERO)
        self.assertEqual(
            self.event.saved_percentage,
            Decimal('100.00'),
        )


class EventPlanContributionTest(TestCase):
    """Monthly contribution of the event plan."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='owner@example.com',
            password='secret123',
        )
        self.event = EventPlan.objects.create(
            user=self.user,
            title='Viagem',
            event_date=date(2026, 7, 1),
        )

    def _set_contribution(self, contribution_type, value):
        self.event.monthly_contribution_type = contribution_type
        self.event.monthly_contribution_value = Decimal(value)
        self.event.save()
        return self.event

    def test_fixed_contribution_ignores_the_income(self):
        event = self._set_contribution(
            EventPlan.ContributionType.FIXED,
            '800.00',
        )
        self.assertEqual(
            event.monthly_contribution(Decimal('5000.00')),
            Decimal('800.00'),
        )

    def test_percentage_contribution_uses_the_net_income(self):
        event = self._set_contribution(
            EventPlan.ContributionType.PERCENTAGE,
            '10.00',
        )
        self.assertEqual(
            event.monthly_contribution(Decimal('5000.00')),
            Decimal('500.00'),
        )

    def test_percentage_contribution_without_income_is_zero(self):
        event = self._set_contribution(
            EventPlan.ContributionType.PERCENTAGE,
            '10.00',
        )
        self.assertEqual(event.monthly_contribution(), ZERO)
        self.assertEqual(
            event.monthly_contribution(Decimal('0.00')),
            ZERO,
        )
