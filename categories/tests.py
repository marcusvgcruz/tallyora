from django.db import IntegrityError, transaction
from django.test import TestCase

from users.models import CustomUser

from .models import Category


class CategoryModelTests(TestCase):
    """Categories created for each user."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='categoria@tallyora.test',
            password='Zx9#pKq7wLm2',
        )

    def test_seeded_categories_come_with_the_user(self):
        """The profile signal seeds the eight default categories."""
        self.assertEqual(Category.objects.filter(user=self.user).count(), 8)

    def test_category_keeps_type_and_color(self):
        """A category stores its type and colour."""
        category = Category.objects.create(
            user=self.user,
            name='Academia',
            category_type='EXPENSE',
            color_hex='#22d3ee',
        )
        self.assertEqual(category.category_type, 'EXPENSE')
        self.assertEqual(category.color_hex, '#22d3ee')

    def test_same_name_in_other_type_is_allowed(self):
        """Income and expense may share a name."""
        Category.objects.create(
            user=self.user, name='Ajuste teste', category_type='EXPENSE'
        )
        category = Category.objects.create(
            user=self.user, name='Ajuste teste', category_type='INCOME'
        )
        self.assertIsNotNone(category.pk)

    def test_duplicated_name_and_type_is_blocked(self):
        """The same name twice in the same type is refused."""
        Category.objects.create(
            user=self.user, name='Duplicada', category_type='EXPENSE'
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(
                    user=self.user, name='Duplicada', category_type='EXPENSE'
                )

    def test_two_users_can_share_a_category_name(self):
        """The uniqueness is per user, not global."""
        other = CustomUser.objects.create_user(
            email='categoria2@tallyora.test',
            password='Zx9#pKq7wLm2',
        )
        Category.objects.create(
            user=self.user, name='Minha', category_type='EXPENSE'
        )
        category = Category.objects.create(
            user=other, name='Minha', category_type='EXPENSE'
        )
        self.assertIsNotNone(category.pk)
