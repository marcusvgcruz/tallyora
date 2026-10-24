from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError

from .models import CustomUser

INPUT_CLASSES = (
    'w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 '
    'text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 '
    'focus:ring-emerald-500/50 focus:border-emerald-500 transition-all '
    'text-sm'
)


class UserRegistrationForm(UserCreationForm):
    """Public registration form for a new Tallyora account."""

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email')
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'E-mail',
        }
        widgets = {
            'first_name': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'autocomplete': 'given-name',
                    'placeholder': 'Seu nome',
                }
            ),
            'last_name': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'autocomplete': 'family-name',
                    'placeholder': 'Seu sobrenome',
                }
            ),
            'email': forms.EmailInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'autocomplete': 'email',
                    'placeholder': 'voce@exemplo.com',
                }
            ),
        }
        error_messages = {
            'email': {
                'unique': 'Já existe uma conta com este e-mail.',
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Senha'
        self.fields['password2'].label = 'Confirmar senha'
        for field_name in ('password1', 'password2'):
            self.fields[field_name].widget.attrs['class'] = INPUT_CLASSES

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError('Já existe uma conta com este e-mail.')
        return email


class EmailAuthenticationForm(AuthenticationForm):
    """Login form that uses the e-mail address as identifier."""

    username = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(
            attrs={
                'class': INPUT_CLASSES,
                'autocomplete': 'email',
                'placeholder': 'voce@exemplo.com',
            }
        ),
    )

    error_messages = {
        'invalid_login': 'E-mail ou senha inválidos.',
        'inactive': 'Esta conta está inativa.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].label = 'Senha'
        self.fields['password'].widget.attrs['class'] = INPUT_CLASSES


class UserAdminCreationForm(UserCreationForm):
    """User creation form used inside the Django admin."""

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name')


class UserAdminChangeForm(UserChangeForm):
    """User edition form used inside the Django admin."""

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name')
