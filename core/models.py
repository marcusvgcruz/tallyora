from decimal import ROUND_HALF_UP, Decimal

from django.db import models

MONEY_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')


def to_money(value):
    """Round a numeric value to two decimal places using half-up rounding."""
    return Decimal(value).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


class BaseModel(models.Model):
    """Abstract base model with creation and update timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
