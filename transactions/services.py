"""Financial calculation engine for a selected period."""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from core.models import ZERO, to_money
from goals_events.models import GoalBox
from profiles.models import UserProfile
from transactions.models import RecurringExpense, Transaction

PERIOD_FULL = 'full'
PERIOD_FIRST_HALF = 'first'
PERIOD_SECOND_HALF = 'second'

PERIOD_CHOICES = (
    (PERIOD_FULL, 'Mês completo'),
    (PERIOD_FIRST_HALF, '1ª quinzena'),
    (PERIOD_SECOND_HALF, '2ª quinzena'),
)

MONTH_NAMES = (
    'Janeiro',
    'Fevereiro',
    'Março',
    'Abril',
    'Maio',
    'Junho',
    'Julho',
    'Agosto',
    'Setembro',
    'Outubro',
    'Novembro',
    'Dezembro',
)

ONE_HUNDRED = Decimal('100.00')


@dataclass(frozen=True)
class Period:
    """Month, year and the slice of the month being analysed.

    ``kind`` is one of ``PERIOD_FULL``, ``PERIOD_FIRST_HALF`` or
    ``PERIOD_SECOND_HALF``; the first half always ends on day 15.
    """

    year: int
    month: int
    kind: str = PERIOD_FULL

    @classmethod
    def from_query(cls, params, today=None):
        """Build a period from request GET parameters, with fallbacks."""
        today = today or timezone.localdate()
        try:
            month = int(params.get('mes', today.month))
        except (TypeError, ValueError):
            month = today.month
        try:
            year = int(params.get('ano', today.year))
        except (TypeError, ValueError):
            year = today.year
        if not 1 <= month <= 12:
            month = today.month
        if not 2000 <= year <= 2100:
            year = today.year
        kind = params.get('periodo', PERIOD_FULL)
        valid_kinds = {choice[0] for choice in PERIOD_CHOICES}
        if kind not in valid_kinds:
            kind = PERIOD_FULL
        return cls(year=year, month=month, kind=kind)

    @property
    def last_day(self):
        """Last calendar day of the month."""
        return calendar.monthrange(self.year, self.month)[1]

    @property
    def start_date(self):
        """First day included in the period."""
        if self.kind == PERIOD_SECOND_HALF:
            return date(self.year, self.month, 16)
        return date(self.year, self.month, 1)

    @property
    def end_date(self):
        """Last day included in the period."""
        if self.kind == PERIOD_FIRST_HALF:
            return date(self.year, self.month, 15)
        return date(self.year, self.month, self.last_day)

    @property
    def kind_label(self):
        """Human readable slice name."""
        return dict(PERIOD_CHOICES)[self.kind]

    @property
    def label(self):
        """Full label, e.g. ``Outubro de 2026 — 1ª quinzena``."""
        month_name = MONTH_NAMES[self.month - 1]
        if self.kind == PERIOD_FULL:
            return f'{month_name} de {self.year}'
        return f'{month_name} de {self.year} — {self.kind_label}'

    @property
    def billing_cycles(self):
        """Billing cycles of fixed expenses that fall in this period.

        ``MONTHLY`` expenses are charged every month, so they are
        accepted in any period; the due day decides which half of the
        month they belong to (see ``day_range``).
        """
        cycle = RecurringExpense.BillingCycle
        if self.kind == PERIOD_FIRST_HALF:
            return (cycle.MONTHLY, cycle.FIRST_HALF)
        if self.kind == PERIOD_SECOND_HALF:
            return (cycle.MONTHLY, cycle.SECOND_HALF)
        return (cycle.MONTHLY, cycle.FIRST_HALF, cycle.SECOND_HALF)

    @property
    def day_range(self):
        """First and last day of the month included in the period."""
        return self.start_date.day, self.end_date.day

    @property
    def query(self):
        """Query string parameters that reproduce this period."""
        return {'mes': self.month, 'ano': self.year, 'periodo': self.kind}


class FinancialCalculationService:
    """Consolidate the numbers of one user inside one period.

    The order follows ``docs/05-regras-de-negocio-financeiras.md``:
    net income, expenses paid from the account, credit card bill once,
    investments, savings boxes, event contributions, free balance.
    """

    def __init__(self, user, period):
        self.user = user
        self.period = period

    def summary(self):
        """Return every number of the period in one dictionary."""
        profile = self._profile()
        transactions = list(self._period_transactions())
        recurring = list(self._period_recurring_expenses())

        net_income = self._net_income(profile, transactions)
        cash_expenses = self._cash_expenses(transactions, recurring)
        credit_card_bill = self._credit_card_bill(transactions, recurring)
        balance_after_expenses = to_money(
            net_income - cash_expenses - credit_card_bill
        )

        investment = self._investment_allocation(profile, net_income)
        available_for_boxes = to_money(balance_after_expenses - investment)
        boxes, boxes_total = self._goal_box_contributions(available_for_boxes)
        events_total = self._event_contributions()

        free_balance = to_money(
            available_for_boxes - boxes_total - events_total
        )

        return {
            'period': self.period,
            'profile': profile,
            'net_income': net_income,
            'cash_expenses': cash_expenses,
            'credit_card_bill': credit_card_bill,
            'balance_after_expenses': balance_after_expenses,
            'investment_allocation': investment,
            'goal_box_contributions': boxes_total,
            'event_contributions': events_total,
            'free_balance': free_balance,
            'recurring_expenses': recurring,
            'transactions': transactions,
            'goal_boxes': boxes,
            'has_credit_card_bill_entry': any(
                item.is_card_bill for item in transactions
            ),
        }

    # ------------------------------------------------------------------
    # data sources
    # ------------------------------------------------------------------
    def _profile(self):
        """Profile of the user, created on demand when missing."""
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        return profile

    def _period_transactions(self):
        """Transactions whose reference date falls inside the period."""
        return Transaction.objects.filter(
            user=self.user,
            reference_date__gte=self.period.start_date,
            reference_date__lte=self.period.end_date,
        )

    def _period_recurring_expenses(self):
        """Active fixed expenses charged in this period.

        A fixed expense belongs to a period when its billing cycle is
        accepted (``MONTHLY`` always is) and its due day falls inside
        the day range of the period. Due days beyond the end of a short
        month (e.g. 31 in February) count in the full month and in the
        second half, never disappearing from the calculation.
        """
        first_day, last_day = self.period.day_range
        due_filter = Q(due_day__gte=first_day, due_day__lte=last_day)
        if self.period.end_date == date(
            self.period.year, self.period.month, self.period.last_day
        ):
            due_filter |= Q(due_day__gt=self.period.last_day)
        return RecurringExpense.objects.filter(
            due_filter,
            user=self.user,
            is_active=True,
            billing_cycle__in=self.period.billing_cycles,
        )

    # ------------------------------------------------------------------
    # income
    # ------------------------------------------------------------------
    def _net_income(self, profile, transactions):
        """Net income of the period.

        CLT salaries come from the profile (gross minus payroll
        deductions, split in halves when the payment is biweekly).
        PJ income is the realised revenue: the INCOME transactions
        registered inside the period.
        """
        if profile.work_regime == profile.WorkRegime.PJ:
            total = sum(
                (item.amount for item in transactions if item.is_income),
                ZERO,
            )
            return to_money(total)
        if self.period.kind == PERIOD_FIRST_HALF:
            return to_money(profile.first_half_income)
        if self.period.kind == PERIOD_SECOND_HALF:
            return to_money(profile.second_half_income)
        return to_money(profile.net_income)

    # ------------------------------------------------------------------
    # expenses
    # ------------------------------------------------------------------
    def _cash_expenses(self, transactions, recurring):
        """Fixed and variable expenses paid straight from the account."""
        fixed = sum(
            (item.amount for item in recurring if not item.is_on_credit_card),
            ZERO,
        )
        variable = sum(
            (
                item.amount
                for item in transactions
                if item.transaction_type == Transaction.TransactionType.EXPENSE
                and not item.is_on_credit_card
            ),
            ZERO,
        )
        return to_money(fixed + variable)

    def _credit_card_bill(self, transactions, recurring):
        """Credit card bill of the period, counted exactly once.

        A consolidated ``CREDIT_CARD_BILL`` entry wins: when it exists,
        the individual items marked as being on the card are only a
        detail of the same money and must not be summed again.
        """
        consolidated = sum(
            (item.amount for item in transactions if item.is_card_bill),
            ZERO,
        )
        if consolidated > ZERO:
            return to_money(consolidated)
        card_fixed = sum(
            (item.amount for item in recurring if item.is_on_credit_card),
            ZERO,
        )
        card_variable = sum(
            (
                item.amount
                for item in transactions
                if item.transaction_type == Transaction.TransactionType.EXPENSE
                and item.is_on_credit_card
            ),
            ZERO,
        )
        return to_money(card_fixed + card_variable)

    # ------------------------------------------------------------------
    # deductions from the available balance
    # ------------------------------------------------------------------
    def _investment_allocation(self, profile, net_income):
        """Amount reserved for investments, from the profile choice."""
        if not profile.has_investments:
            return ZERO
        value = profile.investment_allocation_value
        if value <= ZERO:
            return ZERO
        if profile.investment_allocation_type == (
            profile.InvestmentAllocationType.PERCENTAGE
        ):
            return to_money(net_income * value / ONE_HUNDRED)
        return to_money(value)

    def _goal_box_contributions(self, available_balance):
        """Savings of each box, deducted sequentially from the balance."""
        remaining = to_money(available_balance)
        contributions = []
        total = ZERO
        for box in GoalBox.objects.filter(user=self.user):
            contribution = box.calculate_period_contribution(remaining)
            if contribution > ZERO:
                contributions.append(
                    {'box': box, 'contribution': contribution}
                )
                remaining = to_money(remaining - contribution)
                total = to_money(total + contribution)
        return contributions, total

    def _event_contributions(self):
        """Monthly contributions of active event plans.

        ``EventPlan`` is a Sprint 4 model; until it exists the leg
        contributes zero and the rest of the calculation is unaffected.
        """
        try:
            from goals_events.models import EventPlan
        except ImportError:
            return ZERO
        plans = EventPlan.objects.filter(user=self.user, is_active=True)
        total = ZERO
        for plan in plans:
            total = to_money(total + plan.monthly_contribution())
        return total
