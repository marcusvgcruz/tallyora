"""Views for the daily reminders."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView

from .forms import DailyReminderForm
from .models import DailyReminder
from .services import GoogleCalendarSyncService

REMINDER_LIST_URL = reverse_lazy('reminders:list')
PAGE_SIZE = 10
SYNC_NOT_CONFIGURED = (
    'Google Calendar não está configurado neste ambiente. Defina '
    'GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e GOOGLE_REFRESH_TOKEN '
    'para importar os eventos da agenda.'
)
SYNC_SUCCESS = 'Agenda sincronizada: {created} {events} e {updated} {updates}.'
SYNC_FAILED = (
    'Não foi possível sincronizar com o Google Calendar agora. '
    'Nenhum lembrete foi apagado.'
)


def _plural_label(count, singular, plural):
    """Return the pt-BR label that matches ``count``."""
    return singular if count == 1 else plural


class ReminderListView(LoginRequiredMixin, ListView):
    """List the reminders of the logged user from today on."""

    model = DailyReminder
    template_name = 'reminders/reminder_list.html'
    context_object_name = 'reminders'
    paginate_by = PAGE_SIZE

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


class ReminderSyncView(LoginRequiredMixin, View):
    """Import today's Google Calendar events on a manual request.

    Only POST is accepted: the sync writes to the database, so a simple
    link (GET) would be able to trigger it. Every branch redirects back
    to the reminder list with a message; the failure branch keeps every
    existing reminder untouched.
    """

    def post(self, request, *args, **kwargs):
        service = GoogleCalendarSyncService(request.user)
        if not service.is_configured:
            messages.warning(request, SYNC_NOT_CONFIGURED)
            return redirect(REMINDER_LIST_URL)
        result = service.sync_today()
        if result['errors']:
            messages.error(request, SYNC_FAILED)
        else:
            messages.success(
                request,
                SYNC_SUCCESS.format(
                    created=result['created'],
                    updated=result['updated'],
                    events=_plural_label(
                        result['created'],
                        'evento importado',
                        'eventos importados',
                    ),
                    updates=_plural_label(
                        result['updated'],
                        'atualizado',
                        'atualizados',
                    ),
                ),
            )
        return redirect(REMINDER_LIST_URL)
