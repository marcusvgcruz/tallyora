from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from core.models import ZERO, BaseModel, to_money

ONE_HUNDRED = Decimal('100.00')


class GoalBox(BaseModel):
    """Savings box (cofrinho) with a percentage or fixed allocation."""

    class AllocationType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentual'
        FIXED = 'FIXED', 'Valor fixo'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='goal_boxes',
        verbose_name='usuário',
    )
    name = models.CharField('nome', max_length=120)
    storage_location = models.CharField(
        'onde o dinheiro está',
        max_length=120,
        blank=True,
        help_text='Ex.: cofrinho do banco, CDB de liquidez diária.',
    )
    allocation_type = models.CharField(
        'tipo de alocação',
        max_length=10,
        choices=AllocationType.choices,
        default=AllocationType.PERCENTAGE,
    )
    allocation_value = models.DecimalField(
        'valor da alocação',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
        validators=[MinValueValidator(ZERO)],
    )
    current_balance = models.DecimalField(
        'saldo acumulado',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )
    target_amount = models.DecimalField(
        'meta',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )

    class Meta:
        verbose_name = 'caixinha'
        verbose_name_plural = 'caixinhas'
        ordering = ('name',)

    def __str__(self):
        return self.name

    def clean(self):
        """Validate percentage allocations and the sum of active boxes."""
        super().clean()
        if (
            self.allocation_type == self.AllocationType.PERCENTAGE
            and self.allocation_value > ONE_HUNDRED
        ):
            raise ValidationError(
                {'allocation_value': 'O percentual não pode passar de 100%.'}
            )

    @property
    def progress_percentage(self):
        """How much of the target is already saved (0 to 100)."""
        if self.target_amount <= ZERO:
            return ZERO
        progress = self.current_balance / self.target_amount * ONE_HUNDRED
        return to_money(min(progress, ONE_HUNDRED))

    @property
    def remaining_amount(self):
        """How much is still missing to reach the target."""
        missing = self.target_amount - self.current_balance
        return to_money(missing) if missing > ZERO else ZERO

    def calculate_period_contribution(self, available_balance):
        """Return the amount in BRL to set aside this period.

        Percentage boxes take that share of ``available_balance``;
        fixed boxes take their value as is. A non-positive balance
        yields zero, so the free balance is never reduced by a box
        that has nothing to allocate from.
        """
        available = to_money(available_balance or ZERO)
        if available <= ZERO:
            return ZERO
        if self.allocation_type == self.AllocationType.PERCENTAGE:
            return to_money(available * self.allocation_value / ONE_HUNDRED)
        return to_money(self.allocation_value)


class EventPlan(BaseModel):
    """Big project (wedding, trip, renovation) with a monthly target."""

    class ContributionType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentual da renda'
        FIXED = 'FIXED', 'Valor fixo'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_plans',
        verbose_name='usuário',
    )
    linked_goal_box = models.ForeignKey(
        GoalBox,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='event_plans',
        verbose_name='caixinha vinculada',
    )
    title = models.CharField('nome do evento', max_length=120)
    event_date = models.DateField('data do evento')
    already_saved_amount = models.DecimalField(
        'valor já guardado',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )
    monthly_contribution_type = models.CharField(
        'tipo de aporte mensal',
        max_length=10,
        choices=ContributionType.choices,
        default=ContributionType.FIXED,
    )
    monthly_contribution_value = models.DecimalField(
        'valor do aporte mensal',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
        validators=[MinValueValidator(ZERO)],
    )
    is_active = models.BooleanField('ativo', default=True)

    class Meta:
        verbose_name = 'evento'
        verbose_name_plural = 'eventos'
        ordering = ('event_date', 'title')

    def __str__(self):
        return self.title

    def clean(self):
        """Keep the monthly percentage inside 0..100."""
        super().clean()
        if (
            self.monthly_contribution_type == self.ContributionType.PERCENTAGE
            and self.monthly_contribution_value > ONE_HUNDRED
        ):
            raise ValidationError(
                {
                    'monthly_contribution_value': (
                        'O percentual não pode passar de 100%.'
                    ),
                }
            )

    def monthly_contribution(self, base_amount=ZERO):
        """Amount to set aside every month for this event."""
        value = self.monthly_contribution_value
        if value <= ZERO:
            return ZERO
        if self.monthly_contribution_type == self.ContributionType.PERCENTAGE:
            base = to_money(base_amount or ZERO)
            if base <= ZERO:
                return ZERO
            return to_money(base * value / ONE_HUNDRED)
        return to_money(value)

    @property
    def total_cost(self):
        """Sum of every supplier cost of the event."""
        total = sum(
            (item.total_cost for item in self.expense_items.all()),
            ZERO,
        )
        return to_money(total)

    @property
    def total_paid(self):
        """Sum of the amounts already paid to suppliers."""
        total = sum(
            (item.amount_paid for item in self.expense_items.all()),
            ZERO,
        )
        return to_money(total)

    @property
    def remaining_to_pay(self):
        """How much is still owed to suppliers."""
        missing = self.total_cost - self.total_paid
        return to_money(missing) if missing > ZERO else ZERO

    @property
    def amount_still_needed(self):
        """How much the user still has to save for this event."""
        missing = self.remaining_to_pay - self.already_saved_amount
        return to_money(missing) if missing > ZERO else ZERO

    @property
    def saved_percentage(self):
        """Share of the remaining cost already saved (0 to 100)."""
        needed = self.remaining_to_pay
        if needed <= ZERO:
            return to_money(ONE_HUNDRED)
        progress = self.already_saved_amount / needed * ONE_HUNDRED
        return to_money(min(progress, ONE_HUNDRED))


class EventExpenseItem(BaseModel):
    """Supplier cost inside an event plan."""

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendente'
        PARTIAL = 'PARTIAL', 'Parcial'
        PAID = 'PAID', 'Pago'

    event = models.ForeignKey(
        EventPlan,
        on_delete=models.CASCADE,
        related_name='expense_items',
        verbose_name='evento',
    )
    supplier_name = models.CharField('fornecedor', max_length=120)
    category_name = models.CharField('categoria', max_length=80, blank=True)
    total_cost = models.DecimalField(
        'custo total',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )
    amount_paid = models.DecimalField(
        'valor pago',
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )
    payment_status = models.CharField(
        'status do pagamento',
        max_length=8,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    notes = models.TextField('observações', blank=True)

    class Meta:
        verbose_name = 'item de despesa do evento'
        verbose_name_plural = 'itens de despesa do evento'
        ordering = ('supplier_name',)

    def __str__(self):
        return f'{self.supplier_name} - {self.event.title}'

    def clean(self):
        """Reject payments bigger than the supplier cost."""
        super().clean()
        if self.amount_paid > self.total_cost:
            raise ValidationError(
                {
                    'amount_paid': (
                        'O valor pago não pode ser maior que o custo total.'
                    ),
                }
            )

    def save(self, *args, **kwargs):
        """Keep ``payment_status`` coherent with the amounts."""
        if self.amount_paid <= ZERO:
            self.payment_status = self.PaymentStatus.PENDING
        elif self.amount_paid >= self.total_cost:
            self.payment_status = self.PaymentStatus.PAID
        else:
            self.payment_status = self.PaymentStatus.PARTIAL
        super().save(*args, **kwargs)

    @property
    def remaining_amount(self):
        """How much is still owed to this supplier."""
        missing = self.total_cost - self.amount_paid
        return to_money(missing) if missing > ZERO else ZERO
