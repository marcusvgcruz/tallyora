from django.contrib import admin

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin listing of the user categories."""

    list_display = ('name', 'user', 'category_type', 'color_hex')
    list_filter = ('category_type',)
    search_fields = ('name', 'user__email')
