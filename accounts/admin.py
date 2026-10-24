from django.contrib import admin

from .models import BankAccount


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    """Admin listing of the bank accounts and cards."""

    list_display = (
        'name',
        'user',
        'initial_balance',
        'has_credit_card',
        'closing_day',
        'due_day',
    )
    list_filter = ('has_credit_card',)
    search_fields = ('name', 'user__email')
