from django.urls import path

from .views import (
    AccountCreateView,
    AccountDeleteView,
    AccountListView,
    AccountUpdateView,
)

app_name = 'accounts'

urlpatterns = [
    path('', AccountListView.as_view(), name='list'),
    path('novo/', AccountCreateView.as_view(), name='create'),
    path('<int:pk>/editar/', AccountUpdateView.as_view(), name='update'),
    path('<int:pk>/excluir/', AccountDeleteView.as_view(), name='delete'),
]
