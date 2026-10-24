from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
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
