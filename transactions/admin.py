from django.contrib import admin

from .models import RecurringExpense, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin listing of the transactions and card items."""

    list_display = (
        'title',
        'user',
        'transaction_type',
        'amount',
        'reference_date',
        'is_on_credit_card',
        'is_paid',
    )
    list_filter = (
        'transaction_type',
        'is_on_credit_card',
        'is_paid',
        'reference_date',
    )
    search_fields = ('title', 'user__email')
    date_hierarchy = 'reference_date'


@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    """Admin listing of the fixed monthly expenses."""

    list_display = (
        'title',
        'user',
        'amount',
        'due_day',
        'billing_cycle',
        'is_on_credit_card',
        'is_active',
    )
    list_filter = ('billing_cycle', 'is_on_credit_card', 'is_active')
    search_fields = ('title', 'user__email')
