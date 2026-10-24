"""Views for transactions and recurring fixed expenses."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.models import ZERO, to_money

from .forms import RecurringExpenseForm, TransactionForm
from .models import RecurringExpense, Transaction
from .services import MONTH_NAMES, PERIOD_CHOICES, Period

TRANSACTION_LIST_URL = reverse_lazy('transactions:list')
RECURRING_LIST_URL = reverse_lazy('transactions:recurring_list')


def _money_sum(queryset, **filters):
    """Sum the amount column of ``queryset`` honouring extra filters."""
    result = queryset.filter(**filters).aggregate(total=Sum('amount'))
    return to_money(result['total'] or ZERO)


class TransactionListView(LoginRequiredMixin, ListView):
    """List the transactions of the logged user inside one period."""

    model = Transaction
    template_name = 'transactions/transaction_list.html'
    context_object_name = 'transactions'

    @property
    def period(self):
        """Period selected in the query string, resolved only once."""
        if not hasattr(self, '_period'):
            self._period = Period.from_query(self.request.GET)
        return self._period

    def get_queryset(self):
        period = self.period
        return super().get_queryset().filter(
            user=self.request.user,
            reference_date__gte=period.start_date,
            reference_date__lte=period.end_date,
        )

    def get_totals(self, queryset):
        """Totals of each transaction type inside the filtered period."""
        transaction_type = Transaction.TransactionType
        return {
            'income': _money_sum(
                queryset,
                transaction_type=transaction_type.INCOME,
            ),
            'expense': _money_sum(
                queryset,
                transaction_type=transaction_type.EXPENSE,
            ),
            'card_bill': _money_sum(
                queryset,
                transaction_type=transaction_type.CREDIT_CARD_BILL,
            ),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.period
        context['period'] = period
        context['filters'] = {
            'mes': period.month,
            'ano': period.year,
            'periodo': period.kind,
        }
        context['period_choices'] = PERIOD_CHOICES
        context['month_names'] = MONTH_NAMES
        context['totals'] = self.get_totals(context['transactions'])
        context['title'] = 'Transações'
        return context


class TransactionCreateView(LoginRequiredMixin, CreateView):
    """Create a transaction for the logged user."""

    model = Transaction
    form_class = TransactionForm
    template_name = 'transactions/transaction_form.html'
    success_url = TRANSACTION_LIST_URL

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nova transação'
        context['submit_label'] = 'Salvar transação'
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Transação criada com sucesso.')
        return super().form_valid(form)


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    """Update a transaction of the logged user."""

    model = Transaction
    form_class = TransactionForm
    template_name = 'transactions/transaction_form.html'
    success_url = TRANSACTION_LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar transação'
        context['submit_label'] = 'Atualizar transação'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Transação atualizada com sucesso.')
        return super().form_valid(form)


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a transaction of the logged user."""

    model = Transaction
    template_name = 'transactions/transaction_confirm_delete.html'
    success_url = TRANSACTION_LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Excluir transação'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Transação removida com sucesso.')
        return super().form_valid(form)


class RecurringExpenseListView(LoginRequiredMixin, ListView):
    """List the fixed expenses of the logged user."""

    model = RecurringExpense
    template_name = 'transactions/recurring_list.html'
    context_object_name = 'recurring_expenses'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total = context['recurring_expenses'].aggregate(
            total=Sum('amount')
        )['total']
        context['total'] = to_money(total or ZERO)
        context['title'] = 'Despesas fixas'
        return context


class RecurringExpenseCreateView(LoginRequiredMixin, CreateView):
    """Create a fixed expense for the logged user."""

    model = RecurringExpense
    form_class = RecurringExpenseForm
    template_name = 'transactions/recurring_form.html'
    success_url = RECURRING_LIST_URL

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nova despesa fixa'
        context['submit_label'] = 'Salvar despesa fixa'
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Despesa fixa criada com sucesso.')
        return super().form_valid(form)


class RecurringExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """Update a fixed expense of the logged user."""

    model = RecurringExpense
    form_class = RecurringExpenseForm
    template_name = 'transactions/recurring_form.html'
    success_url = RECURRING_LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar despesa fixa'
        context['submit_label'] = 'Atualizar despesa fixa'
        return context

    def form_valid(self, form):
        messages.success(
            self.request,
            'Despesa fixa atualizada com sucesso.',
        )
        return super().form_valid(form)


class RecurringExpenseDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a fixed expense of the logged user."""

    model = RecurringExpense
    template_name = 'transactions/recurring_confirm_delete.html'
    success_url = RECURRING_LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Excluir despesa fixa'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Despesa fixa removida com sucesso.')
        return super().form_valid(form)
