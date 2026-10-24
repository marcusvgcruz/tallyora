from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

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


class CategoryListPaginationTests(TestCase):
    """Pagination of the category list."""

    def setUp(self):
        """Replace the seeded categories with twelve of our own."""
        self.user = CustomUser.objects.create_user(
            email='listacategorias@tallyora.test',
            password='Zx9#pKq7wLm2',
        )
        self.client.force_login(self.user)
        self.url = reverse('categories:list')
        Category.objects.filter(user=self.user).delete()
        for index in range(1, 13):
            self.add_category(index)

    def add_category(self, index, user=None, name=None):
        """Create one expense category with a fixed name."""
        return Category.objects.create(
            user=user or self.user,
            name=name or f'Categoria {index:02d}',
            category_type='EXPENSE',
        )

    def test_first_page_holds_ten_of_two_pages(self):
        """Ten rows on page 1 and two pages in total."""
        response = self.client.get(self.url)

        self.assertEqual(len(response.context['categories']), 10)
        self.assertEqual(response.context['paginator'].num_pages, 2)
        self.assertContains(response, 'Página 1 de 2')
        self.assertNotContains(response, 'Categoria 12')

    def test_second_page_holds_the_remaining_two(self):
        """Page 2 brings the two rows left by page 1."""
        response = self.client.get(self.url, {'page': 2})

        self.assertEqual(len(response.context['categories']), 2)
        self.assertContains(response, 'Página 2 de 2')
        self.assertContains(response, 'Categoria 12')

    def test_pagination_never_shows_another_user_item(self):
        """The pages only bring categories of the logged user."""
        other = CustomUser.objects.create_user(
            email='listacategorias2@tallyora.test',
            password='Zx9#pKq7wLm2',
        )
        Category.objects.filter(user=other).delete()
        for index in range(1, 13):
            self.add_category(
                index,
                user=other,
                name=f'Alheia {index:02d}',
            )

        response = self.client.get(self.url)

        self.assertEqual(len(response.context['categories']), 10)
        self.assertEqual(response.context['paginator'].num_pages, 2)
        self.assertContains(response, 'Categoria')
        self.assertNotContains(response, 'Alheia')
