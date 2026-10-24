from django.contrib import admin

from .models import DailyReminder


@admin.register(DailyReminder)
class DailyReminderAdmin(admin.ModelAdmin):
    """Admin listing of the daily reminders."""

    list_display = ('title', 'user', 'reminder_date', 'scheduled_time')
    list_filter = ('reminder_date',)
    search_fields = ('title', 'user__email')
