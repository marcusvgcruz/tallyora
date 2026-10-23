from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from core.models import BaseModel

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r'^#[0-9a-fA-F]{6}$',
    message='Informe uma cor no formato hexadecimal (#RRGGBB).',
)


class Category(BaseModel):
    """Transaction category of a user, income or expense."""

    class CategoryType(models.TextChoices):
        INCOME = 'INCOME', 'Receita'
        EXPENSE = 'EXPENSE', 'Despesa'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name='usuário',
    )
    name = models.CharField('nome', max_length=100)
    category_type = models.CharField(
        'tipo',
        max_length=10,
        choices=CategoryType.choices,
        default=CategoryType.EXPENSE,
    )
    color_hex = models.CharField(
        'cor',
        max_length=7,
        default='#10b981',
        validators=[HEX_COLOR_VALIDATOR],
    )

    class Meta:
        verbose_name = 'categoria'
        verbose_name_plural = 'categorias'
        ordering = ('category_type', 'name')
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'name', 'category_type'),
                name='unique_category_per_user_type',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_category_type_display()})'
