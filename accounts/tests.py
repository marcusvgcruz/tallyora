from decimal import Decimal

from django.test import TestCase

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
