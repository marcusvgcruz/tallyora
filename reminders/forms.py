"""Forms for the daily reminders."""

from django import forms

from users.forms import INPUT_CLASSES

from .models import DailyReminder

DUPLICATED_REMINDER = (
    'Você já tem um lembrete com este título neste dia e horário.'
)


class DailyReminderForm(forms.ModelForm):
    """Register a daily reminder of the logged user."""

    class Meta:
        model = DailyReminder
        fields = ('title', 'scheduled_time', 'reminder_date')
        labels = {
            'title': 'Lembrete',
            'scheduled_time': 'Horário',
            'reminder_date': 'Data',
        }
        help_texts = {
            'title': 'Ex.: tomar remédio, pagar a conta de luz.',
        }
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'placeholder': 'Tomar remédio, pagar a conta...',
                    'maxlength': '160',
                }
            ),
            'scheduled_time': forms.TimeInput(
                attrs={'class': INPUT_CLASSES, 'type': 'time'},
                format='%H:%M',
            ),
            'reminder_date': forms.DateInput(
                attrs={'class': INPUT_CLASSES, 'type': 'date'},
                format='%Y-%m-%d',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['scheduled_time'].input_formats = [
            '%H:%M',
            '%H:%M:%S',
        ]
        self.fields['reminder_date'].input_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d/%m/%y',
        ]

    def clean_title(self):
        """Store the reminder text without surrounding spaces."""
        title = self.cleaned_data['title'].strip()
        if not title:
            raise forms.ValidationError('Escreva o lembrete.')
        return title

    def clean(self):
        """Reject the same reminder twice on the same day and time."""
        cleaned_data = super().clean()
        title = cleaned_data.get('title')
        scheduled_time = cleaned_data.get('scheduled_time')
        reminder_date = cleaned_data.get('reminder_date')
        user = getattr(self.instance, 'user', None)
        if not (user and title and scheduled_time and reminder_date):
            return cleaned_data
        duplicated = DailyReminder.objects.filter(
            user=user,
            title=title,
            scheduled_time=scheduled_time,
            reminder_date=reminder_date,
        )
        if self.instance.pk:
            duplicated = duplicated.exclude(pk=self.instance.pk)
        if duplicated.exists():
            raise forms.ValidationError(DUPLICATED_REMINDER)
        return cleaned_data
