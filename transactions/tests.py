"""Tests for the financial engine of the transactions app.

Covers the credit card rule of RF09 (a card expense enters the bill
and never the account spending), the savings box allocation of RF11
(percentage and fixed) and the period slices used by the dashboard.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from goals_events.models import EventPlan, GoalBox
from profiles.models import UserProfile
from transactions.models import RecurringExpense, Transaction
from transactions.services import (
    PERIOD_FIRST_HALF,
    PERIOD_SECOND_HALF,
    FinancialCalculationService,
    Period,
)

ZERO = Decimal('0.00')


class EngineTestCase(TestCase):
    """Shared fixture: a PJ user whose income comes from transactions."""

    email = 'ana@example.com'
    year = 2026
    month = 10

    def setUp(self):
        """Create the user and force the PJ regime on the profile."""
        self.user = get_user_model().objects.create_user(
            email=self.email,
            password='secret',
        )
        self.profile = self.user.profile
        self.profile.work_regime = UserProfile.WorkRegime.PJ
        self.profile.save(update_fields=['work_regime'])
        self.period = Period(year=self.year, month=self.month)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def make_date(self, day, month=None):
        """Date inside the fixture year, defaulting to the fixture month."""
        return date(self.year, month or self.month, day)

    def make_period(self, kind):
        """Return another slice of the same month."""
        return Period(year=self.year, month=self.month, kind=kind)

    def add_income(self, amount, day=1, month=None, user=None):
        """Register an INCOME transaction inside the fixture month."""
        return Transaction.objects.create(
            user=user or self.user,
            title='Salary',
            amount=amount,
            transaction_type=Transaction.TransactionType.INCOME,
            reference_date=self.make_date(day, month),
        )

    def add_expense(self, amount, day=1, month=None, on_card=False, user=None):
        """Register an EXPENSE transaction, on the card or on the account."""
        return Transaction.objects.create(
            user=user or self.user,
            title='Groceries',
            amount=amount,
            transaction_type=Transaction.TransactionType.EXPENSE,
            reference_date=self.make_date(day, month),
            is_on_credit_card=on_card,
        )

    def add_card_bill(self, amount, day=20, user=None):
        """Register the consolidated credit card bill of the month."""
        return Transaction.objects.create(
            user=user or self.user,
            title='Card bill',
            amount=amount,
            transaction_type=(Transaction.TransactionType.CREDIT_CARD_BILL),
            reference_date=self.make_date(day),
        )

    def add_recurring(
        self, amount, due_day=10, on_card=False, user=None, cycle=None
    ):
        """Register a monthly fixed expense charged on ``due_day``."""
        billing_cycle = cycle or RecurringExpense.BillingCycle.MONTHLY
        return RecurringExpense.objects.create(
            user=user or self.user,
            title='Rent',
            amount=amount,
            due_day=due_day,
            billing_cycle=billing_cycle,
            is_on_credit_card=on_card,
        )

    def add_goal_box(self, allocation_type, value, name='Reserve', user=None):
        """Register a savings box with the given allocation."""
        return GoalBox.objects.create(
            user=user or self.user,
            name=name,
            allocation_type=allocation_type,
            allocation_value=value,
        )

    def add_event(self, value, name='Trip', user=None):
        """Register an active event plan with a fixed monthly aporte."""
        return EventPlan.objects.create(
            user=user or self.user,
            title=name,
            event_date=date(self.year + 1, 1, 10),
            monthly_contribution_type=(EventPlan.ContributionType.FIXED),
            monthly_contribution_value=value,
        )

    def summary(self, period=None, user=None):
        """Run the calculation service for the fixture period."""
        return FinancialCalculationService(
            user or self.user,
            period or self.period,
        ).summary()


class CreditCardBillTests(EngineTestCase):
    """RF09: the bill is counted once and never as account spending."""

    def test_card_expense_enters_only_the_bill(self):
        """A card expense is not subtracted twice from the balance."""
        self.add_income(Decimal('1000.00'))
        self.add_expense(Decimal('250.00'), on_card=True)

        summary = self.summary()

        self.assertEqual(summary['net_income'], Decimal('1000.00'))
        self.assertEqual(summary['cash_expenses'], ZERO)
        self.assertEqual(summary['credit_card_bill'], Decimal('250.00'))
        self.assertEqual(summary['balance_after_expenses'], Decimal('750.00'))
        self.assertEqual(summary['free_balance'], Decimal('750.00'))

    def test_cash_expense_enters_only_the_account(self):
        """The same expense off the card hits cash expenses instead."""
        self.add_income(Decimal('1000.00'))
        self.add_expense(Decimal('250.00'), on_card=False)

        summary = self.summary()

        self.assertEqual(summary['cash_expenses'], Decimal('250.00'))
        self.assertEqual(summary['credit_card_bill'], ZERO)
        self.assertEqual(summary['free_balance'], Decimal('750.00'))

    def test_equivalent_expenses_move_the_same_amount(self):
        """The card flag changes the bucket, not the total deducted."""
        self.add_income(Decimal('1000.00'))
        cash_item = self.add_expense(Decimal('250.00'), on_card=False)
        cash_summary = self.summary()

        cash_item.delete()
        self.add_expense(Decimal('250.00'), on_card=True)
        card_summary = self.summary()

        self.assertEqual(
            cash_summary['balance_after_expenses'],
            card_summary['balance_after_expenses'],
        )
        self.assertEqual(
            cash_summary['free_balance'],
            card_summary['free_balance'],
        )
        self.assertEqual(
            cash_summary['cash_expenses'] + cash_summary['credit_card_bill'],
            card_summary['cash_expenses'] + card_summary['credit_card_bill'],
        )

    def test_consolidated_bill_replaces_the_card_items(self):
        """The bill entry and the items are the same money."""
        self.add_income(Decimal('1000.00'))
        self.add_expense(Decimal('250.00'), on_card=True)
        self.add_card_bill(Decimal('250.00'))

        summary = self.summary()

        self.assertTrue(summary['has_credit_card_bill_entry'])
        self.assertEqual(summary['credit_card_bill'], Decimal('250.00'))
        self.assertEqual(summary['free_balance'], Decimal('750.00'))

    def test_bill_entry_is_never_summed_with_the_card_items(self):
        """A consolidated bill wins, even when it is bigger."""
        self.add_income(Decimal('1000.00'))
        self.add_expense(Decimal('250.00'), on_card=True)
        self.add_card_bill(Decimal('400.00'))

        summary = self.summary()

        self.assertEqual(summary['credit_card_bill'], Decimal('400.00'))
        self.assertEqual(summary['cash_expenses'], ZERO)
        self.assertEqual(summary['free_balance'], Decimal('600.00'))

    def test_smaller_bill_entry_still_wins_over_the_items(self):
        """The consolidated value is authoritative, even when lower."""
        self.add_income(Decimal('1000.00'))
        self.add_expense(Decimal('250.00'), on_card=True)
        self.add_card_bill(Decimal('100.00'))

        summary = self.summary()

        self.assertEqual(summary['credit_card_bill'], Decimal('100.00'))
        self.assertEqual(summary['free_balance'], Decimal('900.00'))

    def test_zero_valued_bill_falls_back_to_the_card_items(self):
        """A blank consolidated entry does not erase the card items."""
        self.add_income(Decimal('1000.00'))
        self.add_expense(Decimal('250.00'), on_card=True)
        self.add_card_bill(ZERO)

        summary = self.summary()

        self.assertTrue(summary['has_credit_card_bill_entry'])
        self.assertEqual(summary['credit_card_bill'], Decimal('250.00'))
        self.assertEqual(summary['free_balance'], Decimal('750.00'))

    def test_fixed_expense_on_the_card_leaves_the_account(self):
        """A recurring expense marked on the card goes to the bill."""
        self.add_income(Decimal('3000.00'))
        self.add_recurring(Decimal('480.00'), due_day=10, on_card=True)

        summary = self.summary()

        self.assertEqual(summary['cash_expenses'], ZERO)
        self.assertEqual(summary['credit_card_bill'], Decimal('480.00'))
        self.assertEqual(summary['free_balance'], Decimal('2520.00'))


class BillPeriodTests(EngineTestCase):
    """The bill of the month only takes items of that month."""

    def test_card_item_inside_the_month_enters_the_bill(self):
        """Items on the first and on the last day belong to the month."""
        self.add_expense(Decimal('120.00'), day=1, on_card=True)
        self.add_expense(Decimal('80.00'), day=31, on_card=True)

        summary = self.summary()

        self.assertEqual(summary['credit_card_bill'], Decimal('200.00'))
        self.assertEqual(len(summary['transactions']), 2)

    def test_card_item_from_another_month_stays_out(self):
        """A September item is not part of the October bill."""
        self.add_expense(Decimal('120.00'), day=25, month=9, on_card=True)

        summary = self.summary()

        self.assertEqual(summary['credit_card_bill'], ZERO)
        self.assertEqual(summary['cash_expenses'], ZERO)
        self.assertEqual(summary['transactions'], [])

    def test_mixed_dates_split_the_two_months(self):
        """Only the October item is counted, whichever month is asked."""
        self.add_income(Decimal('1000.00'), day=10, month=9)
        self.add_expense(Decimal('100.00'), day=10, month=9, on_card=True)
        self.add_expense(Decimal('200.00'), day=10, on_card=True)

        october = self.summary()
        september = self.summary(Period(year=self.year, month=9))

        self.assertEqual(october['credit_card_bill'], Decimal('200.00'))
        self.assertEqual(september['credit_card_bill'], Decimal('100.00'))


class GoalBoxContributionTests(EngineTestCase):
    """RF11: percentage and fixed allocations over what is left."""

    def test_percentage_box_takes_its_share_of_what_is_left(self):
        """10% of (4200 income - 100 expenses) is 410."""
        self.add_income(Decimal('4200.00'))
        self.add_expense(Decimal('100.00'))
        box = self.add_goal_box(
            GoalBox.AllocationType.PERCENTAGE,
            Decimal('10.00'),
        )

        summary = self.summary()

        self.assertEqual(summary['balance_after_expenses'], Decimal('4100.00'))
        self.assertEqual(summary['goal_box_contributions'], Decimal('410.00'))
        self.assertEqual(summary['goal_boxes'][0]['box'], box)
        self.assertEqual(
            summary['goal_boxes'][0]['contribution'],
            Decimal('410.00'),
        )
        self.assertEqual(summary['free_balance'], Decimal('3690.00'))

    def test_fixed_box_ignores_the_net_income(self):
        """A fixed box takes 300 out of a 5000 income as well."""
        self.add_income(Decimal('5000.00'))
        self.add_goal_box(
            GoalBox.AllocationType.FIXED,
            Decimal('300.00'),
        )

        summary = self.summary()

        self.assertEqual(summary['goal_box_contributions'], Decimal('300.00'))
        self.assertEqual(summary['free_balance'], Decimal('4700.00'))

    def test_fixed_box_bigger_than_the_balance_goes_negative(self):
        """The overflow is shown, never hidden as zero."""
        self.add_income(Decimal('200.00'))
        self.add_goal_box(
            GoalBox.AllocationType.FIXED,
            Decimal('300.00'),
        )

        summary = self.summary()

        self.assertEqual(summary['balance_after_expenses'], Decimal('200.00'))
        self.assertEqual(summary['goal_box_contributions'], Decimal('300.00'))
        self.assertEqual(summary['free_balance'], Decimal('-100.00'))
        self.assertLess(summary['free_balance'], ZERO)

    def test_fixed_box_takes_nothing_without_available_balance(self):
        """With nothing left after expenses the box is not funded."""
        self.add_income(Decimal('100.00'))
        self.add_expense(Decimal('100.00'))
        self.add_goal_box(
            GoalBox.AllocationType.FIXED,
            Decimal('300.00'),
        )

        summary = self.summary()

        self.assertEqual(summary['balance_after_expenses'], ZERO)
        self.assertEqual(summary['goal_box_contributions'], ZERO)
        self.assertEqual(summary['free_balance'], ZERO)

    def test_boxes_are_deducted_in_sequence(self):
        """The second box takes its share of what the first left."""
        self.add_income(Decimal('4200.00'))
        self.add_expense(Decimal('100.00'))
        self.add_goal_box(
            GoalBox.AllocationType.PERCENTAGE,
            Decimal('10.00'),
            name='Emergency',
        )
        self.add_goal_box(
            GoalBox.AllocationType.PERCENTAGE,
            Decimal('10.00'),
            name='Travel',
        )

        summary = self.summary()

        contributions = [
            item['contribution'] for item in summary['goal_boxes']
        ]
        self.assertEqual(
            contributions,
            [Decimal('410.00'), Decimal('369.00')],
        )
        self.assertEqual(summary['goal_box_contributions'], Decimal('779.00'))
        self.assertEqual(summary['free_balance'], Decimal('3321.00'))


class PeriodSplitTests(EngineTestCase):
    """Day 15 closes the first half; day 16 opens the second one."""

    def setUp(self):
        """Spread income and expenses across both halves of the month."""
        super().setUp()
        self.add_income(Decimal('1000.00'), day=5)
        self.add_income(Decimal('500.00'), day=20)
        self.add_expense(Decimal('100.00'), day=10)
        self.add_expense(Decimal('50.00'), day=15)
        self.add_expense(Decimal('30.00'), day=16)
        self.add_expense(Decimal('200.00'), day=20)

    def test_first_half_keeps_days_up_to_fifteen(self):
        """Days 1 to 15 stay in the first half."""
        summary = self.summary(self.make_period(PERIOD_FIRST_HALF))

        self.assertEqual(summary['period'].start_date, self.make_date(1))
        self.assertEqual(summary['period'].end_date, self.make_date(15))
        self.assertEqual(summary['net_income'], Decimal('1000.00'))
        self.assertEqual(summary['cash_expenses'], Decimal('150.00'))
        self.assertEqual(summary['free_balance'], Decimal('850.00'))

    def test_second_half_keeps_days_from_sixteen(self):
        """Days 16 to the end of the month stay in the second half."""
        summary = self.summary(self.make_period(PERIOD_SECOND_HALF))

        self.assertEqual(summary['period'].start_date, self.make_date(16))
        self.assertEqual(summary['period'].end_date, self.make_date(31))
        self.assertEqual(summary['net_income'], Decimal('500.00'))
        self.assertEqual(summary['cash_expenses'], Decimal('230.00'))
        self.assertEqual(summary['free_balance'], Decimal('270.00'))

    def test_both_halves_add_up_to_the_full_month(self):
        """No transaction is lost or counted twice between halves."""
        first = self.summary(self.make_period(PERIOD_FIRST_HALF))
        second = self.summary(self.make_period(PERIOD_SECOND_HALF))
        full = self.summary()

        self.assertEqual(
            first['cash_expenses'] + second['cash_expenses'],
            full['cash_expenses'],
        )
        self.assertEqual(
            first['net_income'] + second['net_income'],
            full['net_income'],
        )
        self.assertEqual(
            first['free_balance'] + second['free_balance'],
            full['free_balance'],
        )

    def test_each_transaction_belongs_to_a_single_half(self):
        """The transaction lists of the halves do not overlap."""
        first = self.summary(self.make_period(PERIOD_FIRST_HALF))
        second = self.summary(self.make_period(PERIOD_SECOND_HALF))
        full = self.summary()

        first_ids = {item.pk for item in first['transactions']}
        second_ids = {item.pk for item in second['transactions']}
        full_ids = {item.pk for item in full['transactions']}

        self.assertEqual(first_ids & second_ids, set())
        self.assertEqual(first_ids | second_ids, full_ids)
        self.assertTrue(
            all(
                item.reference_date.day <= 15 for item in first['transactions']
            )
        )
        self.assertTrue(
            all(
                item.reference_date.day >= 16
                for item in second['transactions']
            )
        )


class FreeBalanceTests(EngineTestCase):
    """The free balance closes the formula of RF10."""

    def setUp(self):
        """Build a month with every kind of commitment."""
        super().setUp()
        self.add_income(Decimal('5000.00'))
        self.add_expense(Decimal('300.00'))
        self.add_expense(Decimal('400.00'), on_card=True)
        self.add_recurring(Decimal('200.00'), due_day=10)
        self.profile.has_investments = True
        self.profile.investment_allocation_type = (
            UserProfile.InvestmentAllocationType.PERCENTAGE
        )
        self.profile.investment_allocation_value = Decimal('10.00')
        self.profile.save()
        self.add_goal_box(
            GoalBox.AllocationType.PERCENTAGE,
            Decimal('10.00'),
        )
        self.add_event(Decimal('150.00'))

    def test_every_component_matches_the_expected_amount(self):
        """Each step of the calculation returns the expected number."""
        summary = self.summary()

        self.assertEqual(summary['net_income'], Decimal('5000.00'))
        self.assertEqual(summary['cash_expenses'], Decimal('500.00'))
        self.assertEqual(summary['credit_card_bill'], Decimal('400.00'))
        self.assertEqual(summary['balance_after_expenses'], Decimal('4100.00'))
        self.assertEqual(summary['investment_allocation'], Decimal('500.00'))
        self.assertEqual(summary['goal_box_contributions'], Decimal('360.00'))
        self.assertEqual(summary['event_contributions'], Decimal('150.00'))
        self.assertEqual(summary['free_balance'], Decimal('3090.00'))

    def test_free_balance_subtracts_each_component_once(self):
        """Income minus every deduction equals the free balance."""
        summary = self.summary()

        expected = (
            summary['net_income']
            - summary['cash_expenses']
            - summary['credit_card_bill']
            - summary['investment_allocation']
            - summary['goal_box_contributions']
            - summary['event_contributions']
        )

        self.assertEqual(summary['free_balance'], expected)

    def test_deductions_explain_the_gap_after_expenses(self):
        """The difference between the two balances is the commitment."""
        summary = self.summary()

        committed = (
            summary['investment_allocation']
            + summary['goal_box_contributions']
            + summary['event_contributions']
        )

        self.assertEqual(
            summary['balance_after_expenses'] - committed,
            summary['free_balance'],
        )
        self.assertEqual(committed, Decimal('1010.00'))


class RecurringExpenseTests(EngineTestCase):
    """Fixed expenses enter the account side when off the card."""

    def test_recurring_expense_off_the_card_hits_the_account(self):
        """A rent paid from the account is a cash expense."""
        self.add_income(Decimal('3000.00'))
        self.add_recurring(Decimal('1200.00'), due_day=5)

        summary = self.summary()

        self.assertEqual(summary['cash_expenses'], Decimal('1200.00'))
        self.assertEqual(summary['credit_card_bill'], ZERO)
        self.assertEqual(summary['free_balance'], Decimal('1800.00'))

    def test_recurring_expenses_are_listed_for_the_period(self):
        """The summary exposes the fixed expenses behind the numbers."""
        rent = self.add_recurring(Decimal('1200.00'), due_day=5)

        summary = self.summary()

        self.assertEqual(summary['recurring_expenses'], [rent])

    def test_inactive_recurring_expense_is_skipped(self):
        """A paused fixed expense does not reduce the period."""
        self.add_income(Decimal('3000.00'))
        expense = self.add_recurring(Decimal('1200.00'), due_day=5)
        expense.is_active = False
        expense.save(update_fields=['is_active'])

        summary = self.summary()

        self.assertEqual(summary['cash_expenses'], ZERO)
        self.assertEqual(summary['free_balance'], Decimal('3000.00'))


class UserIsolationTests(EngineTestCase):
    """RNF08: the engine only reads the data of the given user."""

    def test_other_users_records_are_ignored(self):
        """User B income, expenses and boxes do not leak into A."""
        user_model = get_user_model()
        other = user_model.objects.create_user(
            email='bruno@example.com',
            password='secret',
        )
        other.profile.work_regime = UserProfile.WorkRegime.PJ
        other.profile.save(update_fields=['work_regime'])

        self.add_income(Decimal('1000.00'))
        self.add_expense(Decimal('100.00'))
        self.add_income(Decimal('9999.00'), user=other)
        self.add_expense(Decimal('5000.00'), on_card=True, user=other)
        self.add_recurring(Decimal('700.00'), user=other)
        self.add_goal_box(
            GoalBox.AllocationType.FIXED,
            Decimal('900.00'),
            user=other,
        )

        summary = self.summary()

        self.assertEqual(summary['net_income'], Decimal('1000.00'))
        self.assertEqual(summary['cash_expenses'], Decimal('100.00'))
        self.assertEqual(summary['credit_card_bill'], ZERO)
        self.assertEqual(summary['goal_box_contributions'], ZERO)
        self.assertEqual(summary['free_balance'], Decimal('900.00'))
        self.assertTrue(
            all(
                item.user_id == self.user.pk
                for item in summary['transactions']
            )
        )

    def test_other_user_gets_its_own_numbers(self):
        """The same period, run for B, reads only B records."""
        user_model = get_user_model()
        other = user_model.objects.create_user(
            email='bruno@example.com',
            password='secret',
        )
        other.profile.work_regime = UserProfile.WorkRegime.PJ
        other.profile.save(update_fields=['work_regime'])

        self.add_income(Decimal('1000.00'))
        self.add_income(Decimal('2000.00'), user=other)
        self.add_expense(Decimal('500.00'), on_card=True, user=other)

        summary = self.summary(user=other)

        self.assertEqual(summary['net_income'], Decimal('2000.00'))
        self.assertEqual(summary['cash_expenses'], ZERO)
        self.assertEqual(summary['credit_card_bill'], Decimal('500.00'))
        self.assertEqual(summary['free_balance'], Decimal('1500.00'))


class TransactionListPaginationTests(TestCase):
    """Pagination and title search of the transaction list."""

    def setUp(self):
        """Create twelve expenses inside the current month."""
        self.user = get_user_model().objects.create_user(
            email='lista@example.com',
            password='secret',
        )
        self.client.force_login(self.user)
        self.url = reverse('transactions:list')
        self.today = timezone.localdate()
        for index in range(1, 13):
            self.add_transaction(index)

    def add_transaction(self, index, user=None, title=None):
        """Create one expense of the current month."""
        return Transaction.objects.create(
            user=user or self.user,
            title=title or f'Compra {index:02d}',
            amount=Decimal('10.00'),
            transaction_type=Transaction.TransactionType.EXPENSE,
            reference_date=self.today,
        )

    def add_other_user(self, email='outro@example.com'):
        """Create a second user to check the isolation of the list."""
        return get_user_model().objects.create_user(
            email=email,
            password='secret',
        )

    def test_first_page_holds_ten_of_two_pages(self):
        """Ten rows on page 1 and two pages in total."""
        response = self.client.get(self.url)

        self.assertEqual(len(response.context['transactions']), 10)
        self.assertEqual(response.context['paginator'].num_pages, 2)
        self.assertContains(response, 'Página 1 de 2')

    def test_second_page_holds_the_remaining_two(self):
        """Page 2 brings the two rows left by page 1."""
        response = self.client.get(self.url, {'page': 2})

        self.assertEqual(len(response.context['transactions']), 2)
        self.assertContains(response, 'Página 2 de 2')

    def test_edges_of_the_list_disable_the_idle_button(self):
        """Page 1 disables 'Anterior'; the last page disables 'Próxima'."""
        first = self.client.get(self.url)
        last = self.client.get(self.url, {'page': 2})

        self.assertEqual(first.content.count(b'aria-disabled="true"'), 1)
        self.assertEqual(last.content.count(b'aria-disabled="true"'), 1)

    def test_search_is_case_insensitive(self):
        """The term finds the title whatever the case typed."""
        response = self.client.get(self.url, {'q': 'cOmPrA 03'})

        self.assertEqual(len(response.context['transactions']), 1)
        self.assertContains(response, 'Compra 03')
        self.assertContains(response, 'value="cOmPrA 03"')

    def test_search_without_match_uses_the_search_empty_state(self):
        """A term without results shows its own empty message."""
        response = self.client.get(self.url, {'q': 'notebook'})

        self.assertEqual(len(response.context['transactions']), 0)
        self.assertContains(
            response,
            'Nenhuma transação encontrada para “notebook”',
        )
        self.assertNotContains(
            response,
            'Nenhuma transação neste período',
        )

    def test_pagination_link_keeps_the_search_query(self):
        """The next page link carries the term typed in the search."""
        response = self.client.get(self.url, {'q': 'Compra'})

        self.assertContains(response, '?q=Compra')
        self.assertContains(response, 'page=2')

    def test_pagination_never_shows_another_user_item(self):
        """The pages only bring rows of the logged user."""
        other = self.add_other_user()
        for index in range(1, 13):
            self.add_transaction(
                index,
                user=other,
                title=f'Alheia {index:02d}',
            )

        response = self.client.get(self.url)
        page_two = self.client.get(self.url, {'page': 2})

        self.assertEqual(len(response.context['transactions']), 10)
        self.assertEqual(response.context['paginator'].num_pages, 2)
        self.assertEqual(len(page_two.context['transactions']), 2)
        self.assertContains(response, 'Compra')
        self.assertNotContains(response, 'Alheia')
        self.assertNotContains(page_two, 'Alheia')


class RecurringExpenseListPaginationTests(TestCase):
    """Pagination of the fixed expenses list."""

    def setUp(self):
        """Create twelve fixed expenses for one user."""
        self.user = get_user_model().objects.create_user(
            email='fixas@example.com',
            password='secret',
        )
        self.client.force_login(self.user)
        self.url = reverse('transactions:recurring_list')
        for index in range(1, 13):
            self.add_recurring(index)

    def add_recurring(self, index, user=None, title=None):
        """Create one fixed expense due on ``index``."""
        return RecurringExpense.objects.create(
            user=user or self.user,
            title=title or f'Fixa {index:02d}',
            amount=Decimal('100.00'),
            due_day=index,
        )

    def test_first_page_holds_ten_of_two_pages(self):
        """Ten rows on page 1 and two pages in total."""
        response = self.client.get(self.url)

        self.assertEqual(len(response.context['recurring_expenses']), 10)
        self.assertEqual(response.context['paginator'].num_pages, 2)
        self.assertContains(response, 'Página 1 de 2')

    def test_second_page_holds_the_remaining_two(self):
        """Page 2 brings the two rows left by page 1."""
        response = self.client.get(self.url, {'page': 2})

        self.assertEqual(len(response.context['recurring_expenses']), 2)

    def test_total_counts_every_page(self):
        """The monthly total is not limited to the visible page."""
        response = self.client.get(self.url)

        self.assertEqual(response.context['total'], Decimal('1200.00'))

    def test_pagination_never_shows_another_user_item(self):
        """The pages only bring rows of the logged user."""
        other = get_user_model().objects.create_user(
            email='fixas2@example.com',
            password='secret',
        )
        for index in range(1, 13):
            self.add_recurring(
                index,
                user=other,
                title=f'Alheia {index:02d}',
            )

        response = self.client.get(self.url)

        self.assertEqual(len(response.context['recurring_expenses']), 10)
        self.assertEqual(response.context['paginator'].num_pages, 2)
        self.assertEqual(
            response.context['total'],
            Decimal('1200.00'),
        )
        self.assertContains(response, 'Fixa')
        self.assertNotContains(response, 'Alheia')
