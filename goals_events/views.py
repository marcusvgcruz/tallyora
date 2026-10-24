"""Views for savings boxes and event plans."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from core.models import ZERO, to_money

from .forms import EventExpenseItemForm, EventPlanForm, GoalBoxForm
from .models import EventExpenseItem, EventPlan, GoalBox

GOAL_LIST_URL = reverse_lazy('goals:list')
EVENT_LIST_URL = reverse_lazy('goals:event_list')


class GoalBoxListView(LoginRequiredMixin, ListView):
    """List the savings boxes of the logged user."""

    model = GoalBox
    template_name = 'goals_events/goalbox_list.html'
    context_object_name = 'goal_boxes'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aggregates = context['goal_boxes'].aggregate(
            total_balance=Sum('current_balance'),
            total_target=Sum('target_amount'),
        )
        context['total_balance'] = to_money(
            aggregates['total_balance'] or ZERO
        )
        context['total_target'] = to_money(
            aggregates['total_target'] or ZERO
        )
        context['title'] = 'Caixinhas'
        return context


class GoalBoxCreateView(LoginRequiredMixin, CreateView):
    """Create a savings box for the logged user."""

    model = GoalBox
    form_class = GoalBoxForm
    template_name = 'goals_events/goalbox_form.html'
    success_url = GOAL_LIST_URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nova caixinha'
        context['submit_label'] = 'Salvar caixinha'
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Caixinha criada com sucesso.')
        return super().form_valid(form)


class GoalBoxUpdateView(LoginRequiredMixin, UpdateView):
    """Update a savings box of the logged user."""

    model = GoalBox
    form_class = GoalBoxForm
    template_name = 'goals_events/goalbox_form.html'
    success_url = GOAL_LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar caixinha'
        context['submit_label'] = 'Atualizar caixinha'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Caixinha atualizada com sucesso.')
        return super().form_valid(form)


class GoalBoxDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a savings box of the logged user."""

    model = GoalBox
    template_name = 'goals_events/goalbox_confirm_delete.html'
    success_url = GOAL_LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Excluir caixinha'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Caixinha removida com sucesso.')
        return super().form_valid(form)


class EventPlanListView(LoginRequiredMixin, ListView):
    """List the event plans of the logged user with their totals."""

    model = EventPlan
    template_name = 'goals_events/event_list.html'
    context_object_name = 'event_plans'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(user=self.request.user)
            .select_related('linked_goal_box')
            .prefetch_related('expense_items')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_plans = context['event_plans']
        saved = sum(
            (plan.already_saved_amount for plan in event_plans),
            ZERO,
        )
        needed = sum(
            (plan.amount_still_needed for plan in event_plans),
            ZERO,
        )
        context['total_saved'] = to_money(saved)
        context['total_needed'] = to_money(needed)
        context['title'] = 'Eventos'
        return context


class EventPlanCreateView(LoginRequiredMixin, CreateView):
    """Create an event plan for the logged user."""

    model = EventPlan
    form_class = EventPlanForm
    template_name = 'goals_events/event_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Novo evento'
        context['submit_label'] = 'Salvar evento'
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Evento criado com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('goals:event_detail', args=[self.object.pk])


class EventPlanUpdateView(LoginRequiredMixin, UpdateView):
    """Update an event plan of the logged user."""

    model = EventPlan
    form_class = EventPlanForm
    template_name = 'goals_events/event_form.html'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar evento'
        context['submit_label'] = 'Atualizar evento'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Evento atualizado com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('goals:event_detail', args=[self.object.pk])


class EventPlanDetailView(LoginRequiredMixin, DetailView):
    """Show one event plan with its supplier costs."""

    model = EventPlan
    template_name = 'goals_events/event_detail.html'
    context_object_name = 'event'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(user=self.request.user)
            .prefetch_related('expense_items')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expense_items'] = self.object.expense_items.all()
        context['payment_status_choices'] = (
            EventExpenseItem.PaymentStatus.choices
        )
        context['title'] = self.object.title
        return context


class EventPlanDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an event plan of the logged user."""

    model = EventPlan
    template_name = 'goals_events/event_confirm_delete.html'
    success_url = EVENT_LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Excluir evento'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Evento removido com sucesso.')
        return super().form_valid(form)


class EventExpenseItemCreateView(LoginRequiredMixin, CreateView):
    """Add a supplier cost to an event plan of the logged user."""

    model = EventExpenseItem
    form_class = EventExpenseItemForm
    template_name = 'goals_events/eventitem_form.html'

    def get_event(self):
        return get_object_or_404(
            EventPlan,
            pk=self.kwargs['event_pk'],
            user=self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.get_event()
        context['title'] = 'Novo item de despesa'
        context['submit_label'] = 'Salvar item'
        return context

    def form_valid(self, form):
        form.instance.event = self.get_event()
        messages.success(self.request, 'Item de despesa criado com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('goals:event_detail', args=[self.object.event_id])


class EventExpenseItemUpdateView(LoginRequiredMixin, UpdateView):
    """Update a supplier cost of the logged user."""

    model = EventExpenseItem
    form_class = EventExpenseItemForm
    template_name = 'goals_events/eventitem_form.html'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(event__user=self.request.user)
            .select_related('event')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.object.event
        context['title'] = 'Editar item de despesa'
        context['submit_label'] = 'Atualizar item'
        return context

    def form_valid(self, form):
        messages.success(
            self.request, 'Item de despesa atualizado com sucesso.'
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('goals:event_detail', args=[self.object.event_id])


class EventExpenseItemDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a supplier cost of the logged user."""

    model = EventExpenseItem
    template_name = 'goals_events/eventitem_confirm_delete.html'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(event__user=self.request.user)
            .select_related('event')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.object.event
        context['title'] = 'Excluir item de despesa'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Item de despesa removido com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('goals:event_detail', args=[self.object.event_id])
