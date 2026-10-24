from django.contrib import admin

from .models import AssetAllocationTarget, InvestmentAsset


@admin.register(AssetAllocationTarget)
class AssetAllocationTargetAdmin(admin.ModelAdmin):
    """Admin listing of the target percentage per asset class."""

    list_display = ('asset_class', 'user', 'target_percentage')
    list_filter = ('asset_class',)
    search_fields = ('user__email',)


@admin.register(InvestmentAsset)
class InvestmentAssetAdmin(admin.ModelAdmin):
    """Admin listing of the portfolio assets."""

    list_display = (
        'ticker',
        'user',
        'asset_class',
        'quantity',
        'average_price',
        'current_price',
        'last_quote_update',
    )
    list_filter = ('asset_class',)
    search_fields = ('ticker', 'name', 'user__email')
