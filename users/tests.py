"""Automated tests for the e-mail based authentication of Tallyora."""

import re

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

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


class PasswordResetPageTests(TestCase):
    """The four password reset screens are public and render in pt-BR."""

    def setUp(self):
        self.user = User.objects.create_user(
            email=EMAIL,
            password=PASSWORD,
        )

    def reset_link(self):
        """Build a valid reset link for the user, as the e-mail does."""
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        return reverse(
            'users:password_reset_confirm',
            kwargs={'uidb64': uidb64, 'token': token},
        )

    def test_reset_form_page_renders(self):
        response = self.client.get(reverse('users:password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recuperar senha')

    def test_reset_done_page_renders(self):
        response = self.client.get(reverse('users:password_reset_done'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verifique seu e-mail')

    def test_reset_confirm_page_renders_for_a_valid_link(self):
        response = self.client.get(self.reset_link(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Criar nova senha')

    def test_reset_confirm_page_explains_an_invalid_link(self):
        response = self.client.get(
            reverse(
                'users:password_reset_confirm',
                kwargs={'uidb64': 'invalido', 'token': 'expirado'},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Link inválido ou expirado')

    def test_reset_complete_page_renders(self):
        response = self.client.get(reverse('users:password_reset_complete'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Senha redefinida')

    def test_login_page_links_to_the_reset_form(self):
        response = self.client.get(reverse('users:login'))
        self.assertContains(response, 'Esqueci minha senha')
        self.assertContains(response, reverse('users:password_reset'))


class PasswordResetRequestTests(TestCase):
    """Requesting the reset link by e-mail, without leaking accounts."""

    def setUp(self):
        self.user = User.objects.create_user(
            email=EMAIL,
            password=PASSWORD,
        )

    def request_reset(self, email=EMAIL):
        return self.client.post(
            reverse('users:password_reset'),
            {'email': email},
        )

    def test_request_for_a_known_email_sends_one_message(self):
        self.request_reset()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [EMAIL])

    def test_request_uses_the_pt_br_subject(self):
        self.request_reset()
        self.assertEqual(
            mail.outbox[0].subject,
            'Redefinição de senha no Tallyora',
        )

    def test_message_body_carries_the_reset_link(self):
        self.request_reset()
        body = mail.outbox[0].body
        self.assertIn('http://testserver/recuperar-senha/', body)

    def test_request_redirects_to_the_done_page(self):
        response = self.request_reset()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            reverse('users:password_reset_done'),
        )

    def test_request_for_an_unknown_email_sends_no_message(self):
        self.request_reset(email='ninguem@example.com')
        self.assertEqual(len(mail.outbox), 0)

    def test_unknown_email_gets_the_same_response_as_a_known_one(self):
        known = self.request_reset()
        mail.outbox.clear()
        unknown = self.request_reset(email='ninguem@example.com')
        self.assertEqual(unknown.status_code, known.status_code)
        self.assertEqual(unknown['Location'], known['Location'])


class PasswordResetFlowTests(TestCase):
    """The link sent by e-mail really changes the password."""

    LINK_PATTERN = re.compile(
        r'/recuperar-senha/(?P<uidb64>[^/\s]+)/(?P<token>[^/\s]+)/'
    )

    def setUp(self):
        self.user = User.objects.create_user(
            email=EMAIL,
            password=PASSWORD,
        )
        self.new_password = 'NovaSenha#2026'

    def credentials_from_the_email(self):
        """Read the uid and the token out of the message body."""
        match = self.LINK_PATTERN.search(mail.outbox[0].body)
        self.assertIsNotNone(match, mail.outbox[0].body)
        return match.group('uidb64'), match.group('token')

    def reset_password_with_the_email(self):
        """Request the e-mail, follow the link and submit a new password."""
        mail.outbox.clear()
        self.client.post(
            reverse('users:password_reset'),
            {'email': EMAIL},
        )
        uidb64, token = self.credentials_from_the_email()
        link = reverse(
            'users:password_reset_confirm',
            kwargs={'uidb64': uidb64, 'token': token},
        )
        opened = self.client.get(link, follow=True)
        return self.client.post(
            opened.request['PATH_INFO'],
            {
                'new_password1': self.new_password,
                'new_password2': self.new_password,
            },
        )

    def test_the_email_link_redirects_to_the_complete_page(self):
        response = self.reset_password_with_the_email()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            reverse('users:password_reset_complete'),
        )

    def test_the_new_password_replaces_the_old_one(self):
        self.reset_password_with_the_email()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertFalse(self.user.check_password(PASSWORD))

    def test_login_works_with_the_new_password(self):
        self.reset_password_with_the_email()
        self.assertTrue(
            self.client.login(
                username=EMAIL,
                password=self.new_password,
            )
        )

    def test_the_login_page_accepts_the_new_password(self):
        self.reset_password_with_the_email()
        response = self.client.post(
            reverse('users:login'),
            {'username': EMAIL, 'password': self.new_password},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('core:dashboard'))

    def test_the_link_stops_working_after_the_reset(self):
        mail.outbox.clear()
        self.client.post(
            reverse('users:password_reset'),
            {'email': EMAIL},
        )
        uidb64, token = self.credentials_from_the_email()
        used_link = reverse(
            'users:password_reset_confirm',
            kwargs={'uidb64': uidb64, 'token': token},
        )
        self.reset_password_with_the_email()
        response = self.client.get(used_link)
        self.assertContains(response, 'Link inválido ou expirado')
