from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Category

User = get_user_model()

DEFAULT_CATEGORIES = (
    ('Salário', Category.CategoryType.INCOME, '#10b981'),
    ('Adiantamento', Category.CategoryType.INCOME, '#34d399'),
    ('Moradia', Category.CategoryType.EXPENSE, '#6366f1'),
    ('Alimentação', Category.CategoryType.EXPENSE, '#f59e0b'),
    ('Transporte', Category.CategoryType.EXPENSE, '#3b82f6'),
    ('Lazer', Category.CategoryType.EXPENSE, '#ec4899'),
    ('Saúde', Category.CategoryType.EXPENSE, '#ef4444'),
    ('Assinaturas', Category.CategoryType.EXPENSE, '#8b5cf6'),
)


@receiver(post_save, sender=User)
def create_default_categories(sender, instance, created, **kwargs):
    """Populate the default categories for every new user."""
    if not created:
        return
    Category.objects.bulk_create(
        [
            Category(
                user=instance,
                name=name,
                category_type=category_type,
                color_hex=color_hex,
            )
            for name, category_type, color_hex in DEFAULT_CATEGORIES
        ],
        ignore_conflicts=True,
    )
