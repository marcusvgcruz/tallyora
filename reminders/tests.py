import os
from datetime import time
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from users.models import CustomUser

from .models import DailyReminder

SERVICE_PATH = 'reminders.views.GoogleCalendarSyncService'
EMPTY_CREDENTIALS = {
    'GOOGLE_CLIENT_ID': '',
    'GOOGLE_CLIENT_SECRET': '',
    'GOOGLE_REFRESH_TOKEN': '',
}


class DailyReminderModelTests(TestCase):
    """Daily reminders are a to-do list without a done state."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='lembrete@tallyora.test',
            password='Zx9#pKq7wLm2',
        )

    def test_reminder_defaults_to_today(self):
        """A new reminder belongs to the current day."""
        reminder = DailyReminder.objects.create(
            user=self.user,
            title='Tomar remédio',
            scheduled_time=time(7, 30),
        )
        self.assertEqual(reminder.reminder_date, timezone.localdate())

    def test_scheduled_label_is_formatted(self):
        """The time is shown as HH:MM."""
        reminder = DailyReminder.objects.create(
            user=self.user,
            title='Reunião',
            scheduled_time=time(15, 5),
        )
        self.assertEqual(reminder.scheduled_label, '15:05')

    def test_reminder_without_external_id_is_manual(self):
        """A local reminder is not marked as coming from the agenda."""
        reminder = DailyReminder.objects.create(
            user=self.user, title='Manual', scheduled_time=time(8, 0)
        )
        self.assertFalse(reminder.is_from_calendar)

    def test_reminder_with_external_id_is_from_calendar(self):
        """A mirrored reminder is flagged as coming from the agenda."""
        reminder = DailyReminder.objects.create(
            user=self.user,
            title='Evento',
            scheduled_time=time(9, 0),
            external_google_event_id='evt-123',
        )
        self.assertTrue(reminder.is_from_calendar)

    def test_duplicated_slot_is_blocked(self):
        """The same title cannot repeat in the same day and time."""
        DailyReminder.objects.create(
            user=self.user, title='Água', scheduled_time=time(10, 0)
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DailyReminder.objects.create(
                    user=self.user, title='Água', scheduled_time=time(10, 0)
                )

    def test_model_has_no_done_state(self):
        """There is no completion field (RF15: to-do without check)."""
        campos = {field.name for field in DailyReminder._meta.fields}
        for proibido in ('is_done', 'done', 'completed', 'is_completed'):
            self.assertNotIn(proibido, campos)


class ReminderViewsTests(TestCase):
    """Routes of the reminders app."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='lembrete2@tallyora.test',
            password='Zx9#pKq7wLm2',
        )
        self.client.force_login(self.user)

    def test_list_requires_login(self):
        """An anonymous visitor goes to the login page."""
        self.client.logout()
        resposta = self.client.get(reverse('reminders:list'))
        self.assertEqual(resposta.status_code, 302)

    def test_list_shows_only_upcoming_reminders(self):
        """Past reminders leave the list."""
        DailyReminder.objects.create(
            user=self.user,
            title='Ontem',
            scheduled_time=time(8, 0),
            reminder_date=timezone.localdate() - timezone.timedelta(days=1),
        )
        DailyReminder.objects.create(
            user=self.user, title='Hoje', scheduled_time=time(9, 0)
        )
        resposta = self.client.get(reverse('reminders:list'))
        self.assertContains(resposta, 'Hoje')
        self.assertNotContains(resposta, 'Ontem')

    def test_create_assigns_the_logged_user(self):
        """The reminder is always created for the signed user."""
        resposta = self.client.post(
            reverse('reminders:create'),
            {
                'title': 'Consulta',
                'scheduled_time': '14:00',
                'reminder_date': timezone.localdate().isoformat(),
            },
        )
        self.assertEqual(resposta.status_code, 302)
        lembrete = DailyReminder.objects.get(title='Consulta')
        self.assertEqual(lembrete.user, self.user)

    def test_delete_refuses_another_users_reminder(self):
        """A reminder of someone else answers 404."""
        outro = CustomUser.objects.create_user(
            email='lembrete3@tallyora.test',
            password='Zx9#pKq7wLm2',
        )
        alheio = DailyReminder.objects.create(
            user=outro, title='Alheio', scheduled_time=time(11, 0)
        )
        resposta = self.client.get(
            reverse('reminders:delete', args=[alheio.pk])
        )
        self.assertEqual(resposta.status_code, 404)


def _message_texts(response):
    """Return the messages queued for ``response`` as plain strings."""
    return [str(message) for message in get_messages(response.wsgi_request)]


class ReminderSyncViewTests(TestCase):
    """The manual Google Calendar sync only runs on POST."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='sync@tallyora.test',
            password='Zx9#pKq7wLm2',
        )

    def test_sync_refuses_get(self):
        """A GET on the sync route answers 405."""
        self.client.force_login(self.user)
        resposta = self.client.get(reverse('reminders:sync'))
        self.assertEqual(resposta.status_code, 405)

    def test_sync_requires_login(self):
        """An anonymous POST goes to the login page."""
        resposta = self.client.post(reverse('reminders:sync'))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse('users:login'), resposta.url)

    def test_sync_without_credentials_warns(self):
        """No OAuth2 variable means a warning and no new reminder."""
        self.client.force_login(self.user)
        with patch.dict(os.environ, EMPTY_CREDENTIALS):
            resposta = self.client.post(reverse('reminders:sync'))
        mensagens = _message_texts(resposta)
        self.assertEqual(len(mensagens), 1)
        self.assertIn('Google Calendar não está configurado', mensagens[0])
        self.assertEqual(DailyReminder.objects.count(), 0)
        self.assertRedirects(resposta, reverse('reminders:list'))

    def test_sync_calls_the_service_for_the_logged_user(self):
        """The service receives the owner and the counts are reported."""
        self.client.force_login(self.user)
        result = {'created': 2, 'updated': 1, 'deleted': 0, 'errors': []}
        with patch(SERVICE_PATH) as service_class:
            service = service_class.return_value
            service.is_configured = True
            service.sync_today.return_value = result
            resposta = self.client.post(reverse('reminders:sync'))
        service_class.assert_called_once_with(self.user)
        service.sync_today.assert_called_once_with()
        mensagens = _message_texts(resposta)
        self.assertEqual(len(mensagens), 1)
        self.assertIn('2 eventos importados', mensagens[0])
        self.assertIn('1 atualizado', mensagens[0])
        self.assertRedirects(resposta, reverse('reminders:list'))

    def test_sync_failure_keeps_the_manual_reminder(self):
        """An API failure answers an error and deletes nothing."""
        self.client.force_login(self.user)
        DailyReminder.objects.create(
            user=self.user, title='Manual', scheduled_time=time(8, 0)
        )
        result = {
            'created': 0,
            'updated': 0,
            'deleted': 0,
            'errors': ['falha de rede: timed out'],
        }
        with patch(SERVICE_PATH) as service_class:
            service = service_class.return_value
            service.is_configured = True
            service.sync_today.return_value = result
            resposta = self.client.post(reverse('reminders:sync'))
        mensagens = _message_texts(resposta)
        self.assertEqual(len(mensagens), 1)
        self.assertIn('Nenhum lembrete foi apagado', mensagens[0])
        self.assertTrue(DailyReminder.objects.filter(title='Manual').exists())
        self.assertRedirects(resposta, reverse('reminders:list'))


class ReminderPaginationTests(TestCase):
    """The list shows ten reminders per page."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='pagina@tallyora.test',
            password='Zx9#pKq7wLm2',
        )
        self.client.force_login(self.user)
        for indice in range(12):
            DailyReminder.objects.create(
                user=self.user,
                title=f'Lembrete {indice}',
                scheduled_time=time(8, indice),
            )

    def test_first_page_has_ten_reminders(self):
        """Twelve reminders fill two pages of ten and two."""
        resposta = self.client.get(reverse('reminders:list'))
        self.assertEqual(len(resposta.context['reminders']), 10)
        self.assertEqual(resposta.context['paginator'].num_pages, 2)

    def test_second_page_has_the_remaining_two(self):
        """The last page keeps the two leftovers."""
        resposta = self.client.get(reverse('reminders:list'), {'page': 2})
        self.assertEqual(len(resposta.context['reminders']), 2)

    def test_second_page_links_back_to_the_first(self):
        """The pager keeps the querystring when moving pages."""
        resposta = self.client.get(reverse('reminders:list'), {'page': 2})
        self.assertContains(resposta, 'page=1')
        self.assertContains(resposta, 'Página')
