from django.contrib import admin

from .models import EventExpenseItem, EventPlan, GoalBox


@admin.register(GoalBox)
class GoalBoxAdmin(admin.ModelAdmin):
    """Admin listing of the savings boxes."""

    list_display = (
        'name',
        'user',
        'allocation_type',
        'allocation_value',
        'current_balance',
        'target_amount',
    )
    list_filter = ('allocation_type',)
    search_fields = ('name', 'user__email')


class EventExpenseItemInline(admin.TabularInline):
    """Supplier costs edited inside the event page."""

    model = EventExpenseItem
    extra = 0
    fields = (
        'supplier_name',
        'category_name',
        'total_cost',
        'amount_paid',
        'payment_status',
    )
    readonly_fields = ('payment_status',)


@admin.register(EventPlan)
class EventPlanAdmin(admin.ModelAdmin):
    """Admin listing of the events with their supplier costs."""

    list_display = (
        'title',
        'user',
        'event_date',
        'monthly_contribution_type',
        'monthly_contribution_value',
        'is_active',
    )
    list_filter = ('is_active', 'monthly_contribution_type')
    search_fields = ('title', 'user__email')
    date_hierarchy = 'event_date'
    inlines = (EventExpenseItemInline,)


@admin.register(EventExpenseItem)
class EventExpenseItemAdmin(admin.ModelAdmin):
    """Admin listing of the supplier costs."""

    list_display = (
        'supplier_name',
        'event',
        'total_cost',
        'amount_paid',
        'payment_status',
    )
    list_filter = ('payment_status',)
    search_fields = ('supplier_name', 'event__title')
