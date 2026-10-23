from decimal import Decimal

from django.conf import settings
from django.db import models

from core.models import BaseModel

ZERO = Decimal('0.00')


class BankAccount(BaseModel):
    """Bank account owned by a user, optionally with a credit card."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bank_accounts',
        verbose_name='usuário',
    )
    name = models.CharField('nome da conta', max_length=100)
    initial_balance = models.DecimalField(
        'saldo inicial',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )
    has_credit_card = models.BooleanField(
        'possui cartão de crédito',
        default=False,
    )
    closing_day = models.PositiveSmallIntegerField(
        'dia de fechamento',
        null=True,
        blank=True,
    )
    due_day = models.PositiveSmallIntegerField(
        'dia de vencimento',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'conta bancária'
        verbose_name_plural = 'contas bancárias'
        ordering = ('name',)

    def __str__(self):
        return self.name
