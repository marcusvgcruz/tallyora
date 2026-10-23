from django import forms

from users.forms import INPUT_CLASSES

from .models import BankAccount

DAY_ERROR = 'O dia deve estar entre 1 e 31.'
REQUIRED_DAY_ERROR = 'Informe o dia de fechamento e o vencimento.'


class BankAccountForm(forms.ModelForm):
    """Form to register a bank account and its optional credit card."""

    closing_day = forms.IntegerField(
        label='Dia de fechamento',
        required=False,
        min_value=1,
        max_value=31,
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLASSES,
            'min': '1',
            'max': '31',
            'placeholder': '5',
        }),
        error_messages={
            'min_value': DAY_ERROR,
            'max_value': DAY_ERROR,
            'invalid': 'Informe um dia válido.',
        },
    )
    due_day = forms.IntegerField(
        label='Dia de vencimento',
        required=False,
        min_value=1,
        max_value=31,
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLASSES,
            'min': '1',
            'max': '31',
            'placeholder': '12',
        }),
        error_messages={
            'min_value': DAY_ERROR,
            'max_value': DAY_ERROR,
            'invalid': 'Informe um dia válido.',
        },
    )

    class Meta:
        model = BankAccount
        fields = (
            'name',
            'initial_balance',
            'has_credit_card',
            'closing_day',
            'due_day',
        )
        labels = {
            'name': 'Nome da conta',
            'initial_balance': 'Saldo inicial (R$)',
            'has_credit_card': 'Possui cartão de crédito',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Nubank, Itaú, Carteira...',
            }),
            'initial_balance': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'step': '0.01',
                'placeholder': '0,00',
            }),
            'has_credit_card': forms.CheckboxInput(attrs={
                'class': (
                    'w-4 h-4 rounded border-slate-700 bg-slate-900 '
                    'text-emerald-500 focus:ring-emerald-500/50'
                ),
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        has_credit_card = cleaned_data.get('has_credit_card')
        closing_day = cleaned_data.get('closing_day')
        due_day = cleaned_data.get('due_day')

        if has_credit_card:
            for field_name, value in (
                ('closing_day', closing_day),
                ('due_day', due_day),
            ):
                if value is None:
                    self.add_error(field_name, REQUIRED_DAY_ERROR)
                elif value < 1 or value > 31:
                    self.add_error(field_name, DAY_ERROR)
        else:
            cleaned_data['closing_day'] = None
            cleaned_data['due_day'] = None

        return cleaned_data
