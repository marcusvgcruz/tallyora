from django.urls import path

from .views import (
    PayrollDeductionCreateView,
    PayrollDeductionDeleteView,
    ProfileConfigView,
)

app_name = 'profiles'

urlpatterns = [
    path('', ProfileConfigView.as_view(), name='profile'),
    path(
        'descontos/novo/',
        PayrollDeductionCreateView.as_view(),
        name='deduction_create',
    ),
    path(
        'descontos/<int:pk>/excluir/',
        PayrollDeductionDeleteView.as_view(),
        name='deduction_delete',
    ),
]
