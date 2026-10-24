"""URL routes of the goals_events app."""

from django.urls import path

from .views import (
    EventExpenseItemCreateView,
    EventExpenseItemDeleteView,
    EventExpenseItemUpdateView,
    EventPlanCreateView,
    EventPlanDeleteView,
    EventPlanDetailView,
    EventPlanListView,
    EventPlanUpdateView,
    GoalBoxCreateView,
    GoalBoxDeleteView,
    GoalBoxListView,
    GoalBoxUpdateView,
)

app_name = 'goals'

urlpatterns = [
    path('', GoalBoxListView.as_view(), name='list'),
    path('nova/', GoalBoxCreateView.as_view(), name='create'),
    path('<int:pk>/editar/', GoalBoxUpdateView.as_view(), name='update'),
    path('<int:pk>/excluir/', GoalBoxDeleteView.as_view(), name='delete'),
    path('eventos/', EventPlanListView.as_view(), name='event_list'),
    path(
        'eventos/novo/',
        EventPlanCreateView.as_view(),
        name='event_create',
    ),
    path(
        'eventos/<int:pk>/',
        EventPlanDetailView.as_view(),
        name='event_detail',
    ),
    path(
        'eventos/<int:pk>/editar/',
        EventPlanUpdateView.as_view(),
        name='event_update',
    ),
    path(
        'eventos/<int:pk>/excluir/',
        EventPlanDeleteView.as_view(),
        name='event_delete',
    ),
    path(
        'eventos/<int:event_pk>/itens/novo/',
        EventExpenseItemCreateView.as_view(),
        name='item_create',
    ),
    path(
        'itens/<int:pk>/editar/',
        EventExpenseItemUpdateView.as_view(),
        name='item_update',
    ),
    path(
        'itens/<int:pk>/excluir/',
        EventExpenseItemDeleteView.as_view(),
        name='item_delete',
    ),
]
