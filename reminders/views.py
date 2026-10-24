"""Views for the daily reminders."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView

from .forms import DailyReminderForm
from .models import DailyReminder

REMINDER_LIST_URL = reverse_lazy('reminders:list')


class ReminderListView(LoginRequiredMixin, ListView):
    """List the reminders of the logged user from today on."""

    model = DailyReminder
    template_name = 'reminders/reminder_list.html'
    context_object_name = 'reminders'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                user=self.request.user,
                reminder_date__gte=timezone.localdate(),
            )
            .order_by('reminder_date', 'scheduled_time')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        reminders = list(context['reminders'])
        context['today_reminders'] = [
            reminder
            for reminder in reminders
            if reminder.reminder_date == today
        ]
        context['next_days_reminders'] = [
            reminder
            for reminder in reminders
            if reminder.reminder_date > today
        ]
        context['title'] = 'Lembretes'
        return context


class ReminderCreateView(LoginRequiredMixin, CreateView):
    """Create a daily reminder for the logged user."""

    model = DailyReminder
    form_class = DailyReminderForm
    template_name = 'reminders/reminder_form.html'
    success_url = REMINDER_LIST_URL

    def get_form(self, form_class=None):
        """Bind the owner before validation so duplicates are caught."""
        form = super().get_form(form_class)
        form.instance.user = self.request.user
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Novo lembrete'
        context['submit_label'] = 'Salvar lembrete'
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Lembrete criado com sucesso.')
        return super().form_valid(form)


class ReminderDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a daily reminder of the logged user."""

    model = DailyReminder
    template_name = 'reminders/reminder_confirm_delete.html'
    success_url = REMINDER_LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Excluir lembrete'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Lembrete removido com sucesso.')
        return super().form_valid(form)
