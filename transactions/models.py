from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import BaseModel, to_money

ZERO = Decimal('0.00')


class RecurringExpense(BaseModel):
    """Fixed monthly expense that repeats every billing cycle."""

    class BillingCycle(models.TextChoices):
        FIRST_HALF = 'FIRST_HALF', '1ª quinzena'
        SECOND_HALF = 'SECOND_HALF', '2ª quinzena'
        MONTHLY = 'MONTHLY', 'Mensal'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recurring_expenses',
        verbose_name='usuário',
    )
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recurring_expenses',
        verbose_name='categoria',
    )
    account = models.ForeignKey(
        'accounts.BankAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recurring_expenses',
        verbose_name='conta',
    )
    title = models.CharField('título', max_length=120)
    amount = models.DecimalField(
        'valor',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )
    due_day = models.PositiveSmallIntegerField(
        'dia de vencimento',
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )
    billing_cycle = models.CharField(
        'ciclo de cobrança',
        max_length=12,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
    )
    is_on_credit_card = models.BooleanField(
        'está na fatura do cartão de crédito?',
        default=False,
    )
    is_active = models.BooleanField('ativo', default=True)

    class Meta:
        verbose_name = 'despesa fixa'
        verbose_name_plural = 'despesas fixas'
        ordering = ('due_day', 'title')

    def __str__(self):
        return f'{self.title} - R$ {self.amount}'

    @property
    def applies_every_cycle(self):
        """Whether the expense is charged in every billing cycle."""
        return self.billing_cycle == self.BillingCycle.MONTHLY


class Transaction(BaseModel):
    """Single money movement: income, expense or credit card bill."""

    class TransactionType(models.TextChoices):
        INCOME = 'INCOME', 'Receita'
        EXPENSE = 'EXPENSE', 'Despesa'
        CREDIT_CARD_BILL = 'CREDIT_CARD_BILL', 'Fatura do cartão'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='usuário',
    )
    account = models.ForeignKey(
        'accounts.BankAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='conta',
    )
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='categoria',
    )
    title = models.CharField('título', max_length=120)
    amount = models.DecimalField(
        'valor',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )
    transaction_type = models.CharField(
        'tipo',
        max_length=16,
        choices=TransactionType.choices,
        default=TransactionType.EXPENSE,
    )
    reference_date = models.DateField(
        'data de referência',
        default=timezone.localdate,
    )
    is_on_credit_card = models.BooleanField(
        'está na fatura do cartão de crédito?',
        default=False,
    )
    is_paid = models.BooleanField('pago', default=False)

    class Meta:
        verbose_name = 'transação'
        verbose_name_plural = 'transações'
        ordering = ('-reference_date', '-created_at')

    def __str__(self):
        return f'{self.title} - R$ {self.amount}'

    @property
    def is_card_bill(self):
        """Whether this row is the consolidated credit card bill."""
        return self.transaction_type == self.TransactionType.CREDIT_CARD_BILL

    @property
    def is_income(self):
        """Whether this row adds money to the period."""
        return self.transaction_type == self.TransactionType.INCOME

    @property
    def signed_amount(self):
        """Amount with the sign applied for balance sums."""
        if self.is_income:
            return to_money(self.amount)
        return to_money(-self.amount)
