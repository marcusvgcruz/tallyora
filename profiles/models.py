from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import ZERO, BaseModel, to_money

ONE_HUNDRED = Decimal('100.00')


class UserProfile(BaseModel):
    """Financial profile of a user: work regime, salary and investments."""

    class WorkRegime(models.TextChoices):
        CLT = 'CLT', 'CLT'
        PJ = 'PJ', 'PJ / Autônomo'

    class PaymentFrequency(models.TextChoices):
        WEEKLY = 'WEEKLY', 'Semanal'
        BIWEEKLY = 'BIWEEKLY', 'Quinzenal'
        MONTHLY = 'MONTHLY', 'Mensal'

    class InvestmentAllocationType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentual'
        FIXED = 'FIXED', 'Valor fixo'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='usuário',
    )
    work_regime = models.CharField(
        'regime de trabalho',
        max_length=10,
        choices=WorkRegime.choices,
        default=WorkRegime.CLT,
    )
    payment_frequency = models.CharField(
        'periodicidade de recebimento',
        max_length=10,
        choices=PaymentFrequency.choices,
        default=PaymentFrequency.MONTHLY,
    )
    base_gross_income = models.DecimalField(
        'renda bruta base',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )
    advance_percentage = models.DecimalField(
        'percentual de adiantamento',
        max_digits=5,
        decimal_places=2,
        default=Decimal('40.00'),
        validators=[
            MinValueValidator(ZERO),
            MaxValueValidator(ONE_HUNDRED),
        ],
        help_text='Percentual da renda pago na primeira quinzena.',
    )
    has_investments = models.BooleanField(
        'investe mensalmente',
        default=False,
    )
    investment_allocation_type = models.CharField(
        'tipo de alocação para investimentos',
        max_length=10,
        choices=InvestmentAllocationType.choices,
        default=InvestmentAllocationType.PERCENTAGE,
    )
    investment_allocation_value = models.DecimalField(
        'valor de alocação para investimentos',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )

    class Meta:
        verbose_name = 'perfil financeiro'
        verbose_name_plural = 'perfis financeiros'

    def __str__(self):
        return f'Perfil de {self.user.email}'

    @property
    def is_biweekly(self):
        """Whether the salary is split between two monthly payments."""
        return (
            self.work_regime == self.WorkRegime.CLT
            and self.payment_frequency == self.PaymentFrequency.BIWEEKLY
        )

    @property
    def deductions_total(self):
        """Sum of the active payroll deductions (CLT only)."""
        if self.work_regime == self.WorkRegime.PJ:
            return ZERO
        total = self.user.payroll_deductions.filter(
            is_active=True,
        ).aggregate(total=models.Sum('amount'))['total']
        return total or ZERO

    @property
    def net_income(self):
        """Gross income minus the active payroll deductions."""
        return to_money(self.base_gross_income - self.deductions_total)

    @property
    def first_half_income(self):
        """Amount received on the first half of the month (day 15).

        Only a CLT salary paid every fortnight is split; the advance is
        paid without any payroll deduction.
        """
        if not self.is_biweekly:
            return ZERO
        return to_money(
            self.base_gross_income * self.advance_percentage / ONE_HUNDRED
        )

    @property
    def second_half_income(self):
        """Amount received on the second half of the month (day 30).

        Single payment regimes (CLT monthly, PJ) receive the whole net
        income at the end of the period.
        """
        if not self.is_biweekly:
            return self.net_income
        return to_money(self.net_income - self.first_half_income)


class PayrollDeduction(BaseModel):
    """Fixed payroll deduction on a CLT salary (INSS, IRRF, ...)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payroll_deductions',
        verbose_name='usuário',
    )
    name = models.CharField('nome', max_length=100)
    amount = models.DecimalField(
        'valor',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )
    is_active = models.BooleanField('ativo', default=True)

    class Meta:
        verbose_name = 'desconto de folha'
        verbose_name_plural = 'descontos de folha'
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} - R$ {self.amount}'
