from django.contrib import admin

from .models import PayrollDeduction, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin listing of the salary profiles."""

    list_display = (
        'user',
        'work_regime',
        'payment_frequency',
        'base_gross_income',
        'advance_percentage',
        'has_investments',
    )
    list_filter = ('work_regime', 'payment_frequency', 'has_investments')
    search_fields = ('user__email', 'user__first_name')


@admin.register(PayrollDeduction)
class PayrollDeductionAdmin(admin.ModelAdmin):
    """Admin listing of the payroll deductions."""

    list_display = ('name', 'user', 'amount', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'user__email')
