"""URL routes of the goals_events app."""

from django.urls import path

from .views import (
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
]
