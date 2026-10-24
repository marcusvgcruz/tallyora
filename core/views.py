from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from core.models import ZERO, to_money
from goals_events.models import EventPlan, GoalBox
from investments.models import InvestmentAsset
from reminders.models import DailyReminder
from transactions.services import (
    MONTH_NAMES,
    PERIOD_CHOICES,
    FinancialCalculationService,
    Period,
)

YEAR_RANGE = 3
ONE_HUNDRED = Decimal('100.00')


class LandingPageView(TemplateView):
    """Public landing page; authenticated users go to the dashboard."""

    template_name = 'core/landing.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().get(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    """Consolidated dashboard for the selected period.

    Every money number comes from ``FinancialCalculationService.summary()``.
    The view only adds the side data the screen needs: boxes, active
    events, portfolio and the reminders of the day.
    """

    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        """Compose the dashboard context for the selected period."""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        period = Period.from_query(self.request.GET)
        summary = FinancialCalculationService(user, period).summary()

        goal_boxes = list(GoalBox.objects.filter(user=user).order_by('name'))
        active_events = list(
            EventPlan.objects.filter(user=user, is_active=True).order_by(
                'event_date'
            )
        )
        assets = list(
            InvestmentAsset.objects.filter(user=user).order_by(
                'asset_class', 'ticker'
            )
        )

        today = timezone.localdate()
        reminders_today = list(
            DailyReminder.objects.filter(user=user, reminder_date=today)
        )
        external_events, calendar_configured = self._calendar_events(user)

        committed = to_money(
            summary['investment_allocation']
            + summary['goal_box_contributions']
            + summary['event_contributions']
        )

        context.update(
            {
                'title': f'Dashboard — {period.label}',
                'period': period,
                'period_choices': PERIOD_CHOICES,
                'month_names': MONTH_NAMES,
                'years': list(
                    range(
                        period.year - YEAR_RANGE, period.year + YEAR_RANGE + 1
                    )
                ),
                'filters': {
                    'month': period.month,
                    'year': period.year,
                    'period': period.kind,
                },
                'summary': summary,
                'net_income': summary['net_income'],
                'cash_expenses': summary['cash_expenses'],
                'credit_card_bill': summary['credit_card_bill'],
                'investment_allocation': summary['investment_allocation'],
                'goal_box_contributions': summary['goal_box_contributions'],
                'event_contributions': summary['event_contributions'],
                'free_balance': summary['free_balance'],
                'total_committed': committed,
                'chart_data': self._chart_data(summary, committed),
                'goal_boxes': goal_boxes,
                'total_box_balance': to_money(
                    sum((box.current_balance for box in goal_boxes), ZERO)
                ),
                'active_events': active_events,
                'total_event_paid': to_money(
                    sum((event.total_paid for event in active_events), ZERO)
                ),
                'total_event_cost': to_money(
                    sum((event.total_cost for event in active_events), ZERO)
                ),
                'assets': assets,
                'portfolio_value': to_money(
                    sum((asset.current_total_value for asset in assets), ZERO)
                ),
                'reminders_today': reminders_today,
                'reminders_count': len(reminders_today),
                'external_events': external_events,
                'calendar_configured': calendar_configured,
            }
        )
        return context

    @staticmethod
    def _chart_data(summary, committed):
        """Budget split used by the donut chart of the dashboard."""
        spent = to_money(
            summary['cash_expenses'] + summary['credit_card_bill']
        )
        free_balance = summary['free_balance']
        values = [
            float(spent),
            float(committed),
            float(free_balance) if free_balance > ZERO else 0.0,
        ]
        labels = [
            'Gastos do período',
            'Compromissos do mês',
            'Saldo Livre',
        ]
        total = round(sum(values), 2)
        if total <= 0:
            return {'labels': [], 'values': [], 'total': 0.0}
        return {'labels': labels, 'values': values, 'total': total}

    @staticmethod
    def _calendar_events(user):
        """Read today's Google Calendar events, degrading to an empty list.

        The integration is optional: without an OAuth token the service
        reports ``is_configured = False`` and the dashboard keeps working
        with the manual reminders only.
        """
        try:
            from reminders.services import GoogleCalendarSyncService
        except ImportError:
            return [], False
        try:
            service = GoogleCalendarSyncService(user)
            return service.todays_events(), service.is_configured
        except Exception:  # noqa: BLE001 - the dashboard never fails
            return [], False
