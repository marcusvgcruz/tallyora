"""URL routes of the investments app."""

from django.urls import path

from .views import (
    AllocationTargetUpdateView,
    AssetCreateView,
    AssetDeleteView,
    AssetUpdateView,
    PortfolioDashboardView,
    RefreshQuotesView,
)

app_name = 'investments'

urlpatterns = [
    path('', PortfolioDashboardView.as_view(), name='portfolio'),
    path('novo/', AssetCreateView.as_view(), name='asset_create'),
    path(
        '<int:pk>/editar/',
        AssetUpdateView.as_view(),
        name='asset_update',
    ),
    path(
        '<int:pk>/excluir/',
        AssetDeleteView.as_view(),
        name='asset_delete',
    ),
    path(
        'cotacoes/atualizar/',
        RefreshQuotesView.as_view(),
        name='refresh_quotes',
    ),
    path('metas/', AllocationTargetUpdateView.as_view(), name='targets'),
]
