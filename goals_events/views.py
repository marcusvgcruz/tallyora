"""Views for savings boxes."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.models import ZERO, to_money

from .forms import GoalBoxForm
from .models import GoalBox

GOAL_LIST_URL = reverse_lazy('goals:list')


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
