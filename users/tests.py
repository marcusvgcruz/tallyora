"""Automated tests for the e-mail based authentication of Tallyora."""

from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .forms import UserRegistrationForm

User = get_user_model()

PASSWORD = 'Tallyora#2026'
EMAIL = 'maria@example.com'


def registration_data(**overrides):
    """Build a valid payload for the public registration form."""
    data = {
        'first_name': 'Maria',
        'last_name': 'Souza',
        'email': EMAIL,
        'password1': PASSWORD,
        'password2': PASSWORD,
    }
    data.update(overrides)
    return data


class UserManagerTests(TestCase):
    """Rules enforced by the custom e-mail based user manager."""

    def test_email_is_normalized_to_lowercase(self):
        user = User.objects.create_user(
            email='Maria@Example.COM',
            password=PASSWORD,
        )
        self.assertEqual(user.email, EMAIL)

    def test_create_user_requires_an_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password=PASSWORD)

    def test_create_user_with_none_email_raises_value_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email=None, password=PASSWORD)

    def test_duplicate_email_raises_integrity_error(self):
        User.objects.create_user(email=EMAIL, password=PASSWORD)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    email='MARIA@example.com',
                    password=PASSWORD,
                )

    def test_new_user_is_active(self):
        user = User.objects.create_user(email=EMAIL, password=PASSWORD)
        self.assertTrue(user.is_active)

    def test_password_is_stored_as_a_hash(self):
        user = User.objects.create_user(email=EMAIL, password=PASSWORD)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith('pbkdf2_'))
        self.assertTrue(user.check_password(PASSWORD))

    def test_password_check_rejects_a_different_password(self):
        user = User.objects.create_user(email=EMAIL, password=PASSWORD)
        self.assertFalse(user.check_password('outra-senha'))

    def test_username_field_is_the_email(self):
        self.assertEqual(User.USERNAME_FIELD, 'email')
        self.assertIsNone(User.username)

    def test_create_superuser_sets_the_admin_flags(self):
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password=PASSWORD,
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)


class EmailAuthenticationTests(TestCase):
    """Login using the e-mail address as the identifier."""

    def setUp(self):
        self.user = User.objects.create_user(
            email=EMAIL,
            password=PASSWORD,
            first_name='Maria',
            last_name='Souza',
        )

    def test_authenticate_with_email_returns_the_user(self):
        user = authenticate(username=EMAIL, password=PASSWORD)
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.user.pk)

    def test_authenticate_with_unknown_email_fails(self):
        user = authenticate(
            username='ninguem@example.com',
            password=PASSWORD,
        )
        self.assertIsNone(user)

    def test_authenticate_with_wrong_password_fails(self):
        self.assertIsNone(authenticate(username=EMAIL, password='errada'))

    def test_client_login_accepts_email_and_password(self):
        self.assertTrue(self.client.login(username=EMAIL, password=PASSWORD))

    def test_login_page_renders(self):
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Entrar')

    def test_login_view_redirects_to_dashboard_on_success(self):
        response = self.client.post(
            reverse('users:login'),
            {'username': EMAIL, 'password': PASSWORD},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('core:dashboard'))

    def test_login_view_keeps_the_user_in_the_session(self):
        self.client.post(
            reverse('users:login'),
            {'username': EMAIL, 'password': PASSWORD},
        )
        self.assertEqual(
            self.client.session['_auth_user_id'],
            str(self.user.pk),
        )

    def test_login_view_rejects_a_wrong_password(self):
        response = self.client.post(
            reverse('users:login'),
            {'username': EMAIL, 'password': 'senha-errada'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'E-mail ou senha inválidos.')

    def test_login_view_rejects_an_unknown_email(self):
        response = self.client.post(
            reverse('users:login'),
            {'username': 'ninguem@example.com', 'password': PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'E-mail ou senha inválidos.')


class LogoutTests(TestCase):
    """Logout ends the authenticated session."""

    def setUp(self):
        self.user = User.objects.create_user(
            email=EMAIL,
            password=PASSWORD,
        )
        self.client.force_login(self.user)

    def test_logout_clears_the_authenticated_session(self):
        self.assertIn('_auth_user_id', self.client.session)
        response = self.client.post(reverse('users:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_redirects_to_the_landing_page(self):
        response = self.client.post(reverse('users:logout'))
        self.assertEqual(response['Location'], reverse('core:landing'))


class UserRegistrationFormTests(TestCase):
    """Validation of the public registration form."""

    def test_form_accepts_a_valid_payload(self):
        form = UserRegistrationForm(data=registration_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_email_is_required(self):
        form = UserRegistrationForm(data=registration_data(email=''))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(email=EMAIL, password=PASSWORD)
        form = UserRegistrationForm(
            data=registration_data(email='MARIA@EXAMPLE.COM')
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['email'],
            ['Já existe uma conta com este e-mail.'],
        )
