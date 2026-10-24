from datetime import time

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from users.models import CustomUser

from .models import DailyReminder


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
