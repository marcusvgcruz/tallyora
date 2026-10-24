"""Tests for the financial profile, signals and CLT deductions."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from users.models import CustomUser

from .forms import PayrollDeductionForm, UserProfileForm
from .models import PayrollDeduction, UserProfile

PASSWORD = 'SenhaForte#2026'
ZERO = Decimal('0.00')


class ProfileFactoryMixin:
    """Factory helpers shared by the profile test cases."""

    def create_user(self, email='ana@example.com'):
        return CustomUser.objects.create_user(
            email=email,
            password=PASSWORD,
            first_name='Ana',
            last_name='Lima',
        )

    def create_profile(self, gross, user=None, **fields):
        user = user or self.create_user()
        profile = user.profile
        profile.base_gross_income = Decimal(gross)
        for name, value in fields.items():
            setattr(profile, name, value)
        profile.save()
        return profile

    def add_deduction(self, user, amount, name='INSS', is_active=True):
        return PayrollDeduction.objects.create(
            user=user,
            name=name,
            amount=Decimal(amount),
            is_active=is_active,
        )


class UserProfileSignalTests(ProfileFactoryMixin, TestCase):
    """A financial profile is created automatically for every user."""

    def test_profile_is_created_for_a_new_user(self):
        user = self.create_user()
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertIsInstance(user.profile, UserProfile)

    def test_profile_is_linked_one_to_one(self):
        user = self.create_user()
        self.assertEqual(user.profile.user.pk, user.pk)
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)

    def test_saving_the_user_again_does_not_duplicate_the_profile(self):
        user = self.create_user()
        profile_id = user.profile.pk
        user.first_name = 'Ana Maria'
        user.save()
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
        self.assertEqual(user.profile.pk, profile_id)

    def test_profile_uses_the_documented_defaults(self):
        profile = self.create_user().profile
        self.assertEqual(profile.work_regime, UserProfile.WorkRegime.CLT)
        self.assertEqual(
            profile.payment_frequency,
            UserProfile.PaymentFrequency.MONTHLY,
        )
        self.assertEqual(profile.base_gross_income, ZERO)
        self.assertEqual(profile.advance_percentage, Decimal('40.00'))
        self.assertFalse(profile.has_investments)

    def test_superuser_also_receives_a_profile(self):
        admin = CustomUser.objects.create_superuser(
            email='admin@example.com',
            password=PASSWORD,
        )
        self.assertTrue(UserProfile.objects.filter(user=admin).exists())

    def test_deleting_the_user_deletes_the_profile(self):
        user = self.create_user()
        user_id = user.pk
        user.delete()
        self.assertEqual(
            UserProfile.objects.filter(user_id=user_id).count(),
            0,
        )


class PayrollDeductionTests(ProfileFactoryMixin, TestCase):
    """Active CLT deductions are subtracted from the gross income."""

    def test_single_deduction_is_subtracted_from_the_gross_income(self):
        profile = self.create_profile('5000.00')
        self.add_deduction(profile.user, '500.00')
        self.assertEqual(profile.deductions_total, Decimal('500.00'))
        self.assertEqual(profile.net_income, Decimal('4500.00'))

    def test_several_deductions_are_summed(self):
        profile = self.create_profile('5000.00')
        self.add_deduction(profile.user, '500.00', name='INSS')
        self.add_deduction(profile.user, '300.00', name='IRRF')
        self.add_deduction(profile.user, '120.50', name='Sindicato')
        self.assertEqual(profile.deductions_total, Decimal('920.50'))
        self.assertEqual(profile.net_income, Decimal('4079.50'))

    def test_without_deductions_the_net_income_equals_the_gross_income(self):
        profile = self.create_profile('5000.00')
        self.assertEqual(profile.deductions_total, ZERO)
        self.assertEqual(profile.net_income, Decimal('5000.00'))

    def test_inactive_deductions_are_ignored(self):
        profile = self.create_profile('5000.00')
        self.add_deduction(profile.user, '500.00')
        self.add_deduction(
            profile.user,
            '900.00',
            name='Consignado antigo',
            is_active=False,
        )
        self.assertEqual(profile.deductions_total, Decimal('500.00'))
        self.assertEqual(profile.net_income, Decimal('4500.00'))

    def test_deductions_of_another_user_are_not_counted(self):
        profile = self.create_profile('5000.00')
        other = self.create_user(email='outro@example.com')
        self.add_deduction(other, '700.00')
        self.assertEqual(profile.deductions_total, ZERO)
        self.assertEqual(profile.net_income, Decimal('5000.00'))

    def test_pj_regime_ignores_payroll_deductions(self):
        profile = self.create_profile(
            '5000.00',
            work_regime=UserProfile.WorkRegime.PJ,
        )
        self.add_deduction(profile.user, '500.00')
        self.assertEqual(profile.deductions_total, ZERO)
        self.assertEqual(profile.net_income, Decimal('5000.00'))


class AdvancePercentageTests(ProfileFactoryMixin, TestCase):
    """The CLT fortnightly advance splits the salary in two payments."""

    def test_monthly_clt_has_no_first_half_payment(self):
        profile = self.create_profile('5000.00')
        self.add_deduction(profile.user, '500.00')
        self.assertFalse(profile.is_biweekly)
        self.assertEqual(profile.first_half_income, ZERO)
        self.assertEqual(profile.second_half_income, Decimal('4500.00'))

    def test_biweekly_advance_uses_the_configured_percentage(self):
        profile = self.create_profile(
            '5000.00',
            payment_frequency=UserProfile.PaymentFrequency.BIWEEKLY,
            advance_percentage=Decimal('40.00'),
        )
        self.assertTrue(profile.is_biweekly)
        self.assertEqual(profile.first_half_income, Decimal('2000.00'))

    def test_advance_is_rounded_to_two_decimal_places(self):
        profile = self.create_profile(
            '999.99',
            payment_frequency=UserProfile.PaymentFrequency.BIWEEKLY,
            advance_percentage=Decimal('33.33'),
        )
        self.assertEqual(profile.first_half_income, Decimal('333.30'))

    def test_biweekly_second_half_discounts_the_deductions(self):
        profile = self.create_profile(
            '5000.00',
            payment_frequency=UserProfile.PaymentFrequency.BIWEEKLY,
            advance_percentage=Decimal('40.00'),
        )
        self.add_deduction(profile.user, '800.00')
        self.assertEqual(profile.net_income, Decimal('4200.00'))
        self.assertEqual(profile.first_half_income, Decimal('2000.00'))
        self.assertEqual(profile.second_half_income, Decimal('2200.00'))

    def test_biweekly_halves_add_up_to_the_net_income(self):
        profile = self.create_profile(
            '7300.00',
            payment_frequency=UserProfile.PaymentFrequency.BIWEEKLY,
            advance_percentage=Decimal('33.33'),
        )
        self.add_deduction(profile.user, '1111.11')
        total = profile.first_half_income + profile.second_half_income
        self.assertEqual(total, profile.net_income)

    def test_custom_advance_percentage_changes_the_first_half(self):
        profile = self.create_profile(
            '5000.00',
            payment_frequency=UserProfile.PaymentFrequency.BIWEEKLY,
            advance_percentage=Decimal('30.00'),
        )
        self.assertEqual(profile.first_half_income, Decimal('1500.00'))
        self.assertEqual(profile.second_half_income, Decimal('3500.00'))

    def test_zero_advance_pays_everything_on_the_second_half(self):
        profile = self.create_profile(
            '5000.00',
            payment_frequency=UserProfile.PaymentFrequency.BIWEEKLY,
            advance_percentage=ZERO,
        )
        self.assertEqual(profile.first_half_income, ZERO)
        self.assertEqual(profile.second_half_income, Decimal('5000.00'))

    def test_weekly_clt_has_no_first_half_payment(self):
        profile = self.create_profile(
            '5000.00',
            payment_frequency=UserProfile.PaymentFrequency.WEEKLY,
        )
        self.assertFalse(profile.is_biweekly)
        self.assertEqual(profile.first_half_income, ZERO)
        self.assertEqual(profile.second_half_income, Decimal('5000.00'))

    def test_pj_biweekly_has_no_first_half_payment(self):
        profile = self.create_profile(
            '5000.00',
            work_regime=UserProfile.WorkRegime.PJ,
            payment_frequency=UserProfile.PaymentFrequency.BIWEEKLY,
        )
        self.assertFalse(profile.is_biweekly)
        self.assertEqual(profile.first_half_income, ZERO)
        self.assertEqual(profile.second_half_income, Decimal('5000.00'))

    def test_full_advance_with_deductions_produces_a_negative_second_half(
        self,
    ):
        """Documented outcome of the current rule: the advance is gross."""
        profile = self.create_profile(
            '5000.00',
            payment_frequency=UserProfile.PaymentFrequency.BIWEEKLY,
            advance_percentage=Decimal('100.00'),
        )
        self.add_deduction(profile.user, '800.00')
        self.assertEqual(profile.first_half_income, Decimal('5000.00'))
        self.assertEqual(profile.second_half_income, Decimal('-800.00'))


class ProfileValidationTests(ProfileFactoryMixin, TestCase):
    """Limits enforced by the model validators and by the forms."""

    def test_advance_above_one_hundred_is_rejected(self):
        profile = self.create_profile('5000.00')
        profile.advance_percentage = Decimal('120.00')
        with self.assertRaises(ValidationError) as context:
            profile.full_clean()
        self.assertIn('advance_percentage', context.exception.message_dict)

    def test_negative_advance_is_rejected(self):
        profile = self.create_profile('5000.00')
        profile.advance_percentage = Decimal('-1.00')
        with self.assertRaises(ValidationError) as context:
            profile.full_clean()
        self.assertIn('advance_percentage', context.exception.message_dict)

    def test_advance_of_one_hundred_is_accepted(self):
        profile = self.create_profile(
            '5000.00',
            advance_percentage=Decimal('100.00'),
        )
        profile.full_clean()

    def test_advance_form_rejects_values_above_one_hundred(self):
        profile = self.create_profile('5000.00')
        form = UserProfileForm(
            data={
                'work_regime': UserProfile.WorkRegime.CLT,
                'payment_frequency': UserProfile.PaymentFrequency.MONTHLY,
                'base_gross_income': '5000.00',
                'advance_percentage': '150.00',
                'investment_allocation_type': (
                    UserProfile.InvestmentAllocationType.FIXED
                ),
                'investment_allocation_value': '0.00',
            },
            instance=profile,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('advance_percentage', form.errors)

    def test_deduction_form_rejects_a_negative_amount(self):
        profile = self.create_profile('5000.00')
        form = PayrollDeductionForm(
            data={
                'name': 'Empréstimo',
                'amount': '-100.00',
                'is_active': True,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        self.assertFalse(profile.user.payroll_deductions.exists())

    def test_deduction_model_accepts_a_negative_amount(self):
        """The model has no validator: only the form blocks negatives."""
        profile = self.create_profile('5000.00')
        deduction = self.add_deduction(profile.user, '-100.00')
        deduction.full_clean()
        self.assertEqual(profile.net_income, Decimal('5100.00'))


class InvestmentAllocationTests(ProfileFactoryMixin, TestCase):
    """Investment allocation is stored but does not change the net income."""

    def test_percentage_allocation_does_not_change_the_net_income(self):
        profile = self.create_profile(
            '5000.00',
            has_investments=True,
            investment_allocation_type=(
                UserProfile.InvestmentAllocationType.PERCENTAGE
            ),
            investment_allocation_value=Decimal('10.00'),
        )
        self.add_deduction(profile.user, '500.00')
        self.assertEqual(profile.net_income, Decimal('4500.00'))

    def test_fixed_allocation_does_not_change_the_halves(self):
        profile = self.create_profile(
            '5000.00',
            payment_frequency=UserProfile.PaymentFrequency.BIWEEKLY,
            advance_percentage=Decimal('40.00'),
            has_investments=True,
            investment_allocation_type=(
                UserProfile.InvestmentAllocationType.FIXED
            ),
            investment_allocation_value=Decimal('500.00'),
        )
        self.assertEqual(profile.first_half_income, Decimal('2000.00'))
        self.assertEqual(profile.second_half_income, Decimal('3000.00'))
