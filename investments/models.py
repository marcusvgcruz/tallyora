from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import ZERO, BaseModel, to_money

ONE_HUNDRED = Decimal('100.00')


class AssetClass(models.TextChoices):
    """Asset classes tracked by the P3X inspired portfolio."""

    FII = 'FII', 'FII'
    STOCK = 'STOCK', 'Ações'
    FIXED_INCOME = 'FIXED_INCOME', 'Renda Fixa'
    CRYPTO = 'CRYPTO', 'Cripto'


class AssetAllocationTarget(BaseModel):
    """Ideal percentage of the portfolio for one asset class."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='allocation_targets',
        verbose_name='usuário',
    )
    asset_class = models.CharField(
        'classe de ativo',
        max_length=12,
        choices=AssetClass.choices,
    )
    target_percentage = models.DecimalField(
        'percentual alvo',
        max_digits=5,
        decimal_places=2,
        default=ZERO,
        validators=[MinValueValidator(ZERO), MaxValueValidator(ONE_HUNDRED)],
    )

    class Meta:
        verbose_name = 'meta por classe de ativo'
        verbose_name_plural = 'metas por classe de ativo'
        ordering = ('asset_class',)
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'asset_class'),
                name='unique_target_per_user_class',
            ),
        ]

    def __str__(self):
        return f'{self.get_asset_class_display()} - {self.target_percentage}%'

    def clean(self):
        """Never let the sum of the targets pass 100%."""

        super().clean()
        others = AssetAllocationTarget.objects.filter(user=self.user)
        if self.pk:
            others = others.exclude(pk=self.pk)
        current = others.aggregate(total=models.Sum('target_percentage'))[
            'total'
        ]
        total = to_money((current or ZERO) + self.target_percentage)
        if total > ONE_HUNDRED:
            raise ValidationError({
                'target_percentage': (
                    'A soma das metas por classe não pode passar de 100% '
                    f'(com esta ficaria {total}%).'
                ),
            })

    @classmethod
    def total_percentage(cls, user):
        """Sum of the targets already configured by the user."""
        total = cls.objects.filter(user=user).aggregate(
            total=models.Sum('target_percentage')
        )['total']
        return to_money(total or ZERO)

    @classmethod
    def targets_by_class(cls, user):
        """Map of ``asset_class`` to target percentage."""
        return {
            target.asset_class: target.target_percentage
            for target in cls.objects.filter(user=user)
        }


class InvestmentAsset(BaseModel):
    """Asset held by the user, with manual or automatic quotes."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investment_assets',
        verbose_name='usuário',
    )
    asset_class = models.CharField(
        'classe de ativo',
        max_length=12,
        choices=AssetClass.choices,
    )
    ticker = models.CharField('ticker', max_length=20)
    name = models.CharField('nome', max_length=120, blank=True)
    quantity = models.DecimalField(
        'quantidade',
        max_digits=18,
        decimal_places=8,
        default=ZERO,
    )
    average_price = models.DecimalField(
        'preço médio',
        max_digits=14,
        decimal_places=4,
        default=ZERO,
    )
    current_price = models.DecimalField(
        'preço atual',
        max_digits=14,
        decimal_places=4,
        default=ZERO,
    )
    target_percentage_in_class = models.DecimalField(
        'peso ideal na classe (%)',
        max_digits=5,
        decimal_places=2,
        default=ZERO,
        validators=[MinValueValidator(ZERO), MaxValueValidator(ONE_HUNDRED)],
    )
    last_quote_update = models.DateTimeField(
        'última atualização da cotação',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'ativo da carteira'
        verbose_name_plural = 'ativos da carteira'
        ordering = ('asset_class', 'ticker')
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'ticker'),
                name='unique_ticker_per_user',
            ),
        ]

    def __str__(self):
        return self.ticker

    def save(self, *args, **kwargs):
        """Store the ticker in upper case and trim spaces."""
        self.ticker = (self.ticker or '').strip().upper()
        super().save(*args, **kwargs)

    @property
    def total_invested(self):
        """Money the user put in this asset."""
        return to_money(self.quantity * self.average_price)

    @property
    def current_total_value(self):
        """Market value of the asset at the last known quote."""
        return to_money(self.quantity * self.current_price)

    @property
    def profit_loss_amount(self):
        """Profit (positive) or loss (negative) in BRL."""
        return to_money(self.current_total_value - self.total_invested)

    @property
    def profit_loss_percentage(self):
        """Profit or loss in percentage of the invested amount."""
        invested = self.total_invested
        if invested <= ZERO:
            return ZERO
        return to_money(self.profit_loss_amount / invested * ONE_HUNDRED)

    @property
    def is_quoted(self):
        """Whether the asset has an automatic quote (B3 traded)."""
        return self.asset_class in (AssetClass.FII, AssetClass.STOCK)
