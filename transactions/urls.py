"""URL routes of the transactions app."""

from django.urls import path

from .views import (
    RecurringExpenseCreateView,
    RecurringExpenseDeleteView,
    RecurringExpenseListView,
    RecurringExpenseUpdateView,
    TransactionCreateView,
    TransactionDeleteView,
    TransactionListView,
    TransactionUpdateView,
)

app_name = 'transactions'

urlpatterns = [
    path('', TransactionListView.as_view(), name='list'),
    path('nova/', TransactionCreateView.as_view(), name='create'),
    path(
        '<int:pk>/editar/',
        TransactionUpdateView.as_view(),
        name='update',
    ),
    path(
        '<int:pk>/excluir/',
        TransactionDeleteView.as_view(),
        name='delete',
    ),
    path(
        'fixas/',
        RecurringExpenseListView.as_view(),
        name='recurring_list',
    ),
    path(
        'fixas/nova/',
        RecurringExpenseCreateView.as_view(),
        name='recurring_create',
    ),
    path(
        'fixas/<int:pk>/editar/',
        RecurringExpenseUpdateView.as_view(),
        name='recurring_update',
    ),
    path(
        'fixas/<int:pk>/excluir/',
        RecurringExpenseDeleteView.as_view(),
        name='recurring_delete',
    ),
]
