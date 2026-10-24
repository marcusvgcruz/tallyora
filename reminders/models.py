from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class DailyReminder(BaseModel):
    """Daily to-do item shown on the dashboard.

    The reminder has no "done" state on purpose: it is a note for the
    day, not a task list. It leaves the screen when its ``reminder_date``
    passes or when the user deletes it.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_reminders',
        verbose_name='usuário',
    )
    title = models.CharField('lembrete', max_length=160)
    scheduled_time = models.TimeField('horário')
    reminder_date = models.DateField(
        'data do lembrete',
        default=timezone.localdate,
    )
    external_google_event_id = models.CharField(
        'id do evento no Google Calendar',
        max_length=255,
        blank=True,
        default='',
    )

    class Meta:
        verbose_name = 'lembrete diário'
        verbose_name_plural = 'lembretes diários'
        ordering = ('scheduled_time', 'title')
        constraints = [
            models.UniqueConstraint(
                fields=(
                    'user',
                    'reminder_date',
                    'scheduled_time',
                    'title',
                ),
                name='unique_reminder_per_user_day_slot',
            ),
        ]

    def __str__(self):
        return f'{self.scheduled_time:%H:%M} {self.title}'

    @property
    def is_from_calendar(self):
        """Whether the reminder was mirrored from Google Calendar."""
        return bool(self.external_google_event_id)

    @property
    def scheduled_label(self):
        """Time formatted the Brazilian way, e.g. ``08:30``."""
        return self.scheduled_time.strftime('%H:%M')
