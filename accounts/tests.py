from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from users.models import CustomUser

from .models import BankAccount


class BankAccountModelTests(TestCase):
    """Accounts and cards of one user."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='conta@tallyora.test',
            password='Zx9#pKq7wLm2',
        )

    def test_account_belongs_to_user(self):
        """A created account keeps its owner."""
        account = BankAccount.objects.create(
            user=self.user,
            name='Conta corrente',
            initial_balance=Decimal('1500.00'),
        )
        self.assertEqual(account.user, self.user)
        self.assertEqual(account.initial_balance, Decimal('1500.00'))

    def test_card_fields_are_optional(self):
        """An account without a card has no closing or due day."""
        account = BankAccount.objects.create(
            user=self.user, name='Conta simples'
        )
        self.assertFalse(account.has_credit_card)
        self.assertIsNone(account.closing_day)
        self.assertIsNone(account.due_day)

    def test_card_keeps_billing_days(self):
        """A card account stores the closing and due days."""
        account = BankAccount.objects.create(
            user=self.user,
            name='Cartão',
            has_credit_card=True,
            closing_day=25,
            due_day=5,
        )
        self.assertTrue(account.has_credit_card)
        self.assertEqual(account.closing_day, 25)
        self.assertEqual(account.due_day, 5)

    def test_accounts_are_isolated_per_user(self):
        """One user never sees the accounts of another."""
        other = CustomUser.objects.create_user(
            email='outro@tallyora.test',
            password='Zx9#pKq7wLm2',
        )
        BankAccount.objects.create(user=self.user, name='Minha conta')
        BankAccount.objects.create(user=other, name='Conta alheia')
        self.assertEqual(BankAccount.objects.filter(user=self.user).count(), 1)
        self.assertEqual(BankAccount.objects.filter(user=other).count(), 1)

    def test_account_str_shows_the_name(self):
        """The text form of the account is its name."""
        account = BankAccount.objects.create(user=self.user, name='Nubank')
        self.assertEqual(str(account), 'Nubank')


class AccountListPaginationTests(TestCase):
    """Pagination of the bank account list."""

    def setUp(self):
        """Create twelve accounts for one user."""
        self.user = CustomUser.objects.create_user(
            email='contas@tallyora.test',
            password='Zx9#pKq7wLm2',
        )
        self.client.force_login(self.user)
        self.url = reverse('accounts:list')
        for index in range(1, 13):
            self.add_account(index)

    def add_account(self, index, user=None, name=None):
        """Create one bank account with a fixed name."""
        return BankAccount.objects.create(
            user=user or self.user,
            name=name or f'Conta {index:02d}',
        )

    def test_first_page_holds_ten_of_two_pages(self):
        """Ten rows on page 1 and two pages in total."""
        response = self.client.get(self.url)

        self.assertEqual(len(response.context['accounts']), 10)
        self.assertEqual(response.context['paginator'].num_pages, 2)
        self.assertContains(response, 'Página 1 de 2')

    def test_second_page_holds_the_remaining_two(self):
        """Page 2 brings the two rows left by page 1."""
        response = self.client.get(self.url, {'page': 2})

        self.assertEqual(len(response.context['accounts']), 2)
        self.assertContains(response, 'Página 2 de 2')

    def test_single_page_hides_the_pagination_bar(self):
        """A short list does not render the pagination bar."""
        BankAccount.objects.filter(user=self.user).delete()
        self.add_account(1)

        response = self.client.get(self.url)

        self.assertNotContains(response, 'Página 1 de 1')

    def test_pagination_never_shows_another_user_item(self):
        """The pages only bring accounts of the logged user."""
        other = CustomUser.objects.create_user(
            email='contas2@tallyora.test',
            password='Zx9#pKq7wLm2',
        )
        for index in range(1, 13):
            self.add_account(
                index,
                user=other,
                name=f'Alheia {index:02d}',
            )

        response = self.client.get(self.url)

        self.assertEqual(len(response.context['accounts']), 10)
        self.assertEqual(response.context['paginator'].num_pages, 2)
        self.assertContains(response, 'Conta')
        self.assertNotContains(response, 'Alheia')
