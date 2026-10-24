"""URL routes of the reminders app."""

from django.urls import path

from .views import (
    ReminderCreateView,
    ReminderDeleteView,
    ReminderListView,
    ReminderSyncView,
)

app_name = 'reminders'

urlpatterns = [
    path('', ReminderListView.as_view(), name='list'),
    path('novo/', ReminderCreateView.as_view(), name='create'),
    path('sincronizar/', ReminderSyncView.as_view(), name='sync'),
    path('<int:pk>/excluir/', ReminderDeleteView.as_view(), name='delete'),
]
