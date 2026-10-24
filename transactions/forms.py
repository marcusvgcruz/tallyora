"""Forms for transactions and recurring fixed expenses."""

from django import forms

from users.forms import INPUT_CLASSES

from .models import RecurringExpense, Transaction

CARD_LABEL = 'Este gasto está na fatura do cartão de crédito?'
CARD_HELP_TEXT = (
    'Marque quando o valor entra na fatura do cartão em vez de sair '
    'direto do saldo da conta.'
)
CARD_CHECKBOX_CLASSES = (
    'w-4 h-4 rounded border-emerald-500/60 bg-slate-900 '
    'text-emerald-500 focus:ring-emerald-500/50'
)
CARD_WRAPPER_CLASSES = (
    'rounded-xl border border-emerald-500/40 bg-emerald-500/5 '
    'px-4 py-3'
)
PERCENTAGE_LIMIT = 'O percentual não pode passar de 100%.'
NEGATIVE_ALLOCATION = 'O valor da alocação não pode ser negativo.'


class UserScopedFormMixin:
    """Restrict category and account choices to the logged user."""

    user_field_names = ('category', 'account')

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self._scope_user_fields()

    def _scope_user_fields(self):
        """Filter each related queryset by the form owner."""
        for field_name in self.user_field_names:
            field = self.fields.get(field_name)
            if field is None:
                continue
            queryset = field.queryset
            if self.user is None:
                field.queryset = queryset.none()
            else:
                field.queryset = queryset.filter(user=self.user)


class CreditCardFieldMixin:
    """Label the card flag with a highlighted wrapper in the template."""

    card_field_name = 'is_on_credit_card'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get(self.card_field_name)
        if field is None:
            return
        field.label = CARD_LABEL
        field.help_text = CARD_HELP_TEXT
        field.widget.attrs['class'] = CARD_CHECKBOX_CLASSES
        field.widget.attrs['data-highlight'] = 'credit-card'
        field.widget.attrs['data-wrapper-class'] = CARD_WRAPPER_CLASSES


class RecurringExpenseForm(
    CreditCardFieldMixin,
    UserScopedFormMixin,
    forms.ModelForm,
):
    """Register a fixed monthly expense of the logged user."""

    class Meta:
        model = RecurringExpense
        fields = (
            'title',
            'amount',
            'due_day',
            'billing_cycle',
            'category',
            'account',
            'is_on_credit_card',
            'is_active',
        )
        labels = {
            'title': 'Título',
            'amount': 'Valor (R$)',
            'due_day': 'Dia de vencimento',
            'billing_cycle': 'Ciclo de cobrança',
            'category': 'Categoria',
            'account': 'Conta',
            'is_active': 'Despesa ativa',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Aluguel, internet, academia...',
            }),
            'amount': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00',
            }),
            'due_day': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'min': '1',
                'max': '31',
                'placeholder': '5',
            }),
            'billing_cycle': forms.Select(attrs={'class': INPUT_CLASSES}),
            'category': forms.Select(attrs={'class': INPUT_CLASSES}),
            'account': forms.Select(attrs={'class': INPUT_CLASSES}),
            'is_active': forms.CheckboxInput(attrs={
                'class': (
                    'w-4 h-4 rounded border-slate-700 bg-slate-900 '
                    'text-emerald-500 focus:ring-emerald-500/50'
                ),
            }),
        }


class TransactionForm(
    CreditCardFieldMixin,
    UserScopedFormMixin,
    forms.ModelForm,
):
    """Register a single money movement of the logged user."""

    class Meta:
        model = Transaction
        fields = (
            'title',
            'amount',
            'transaction_type',
            'reference_date',
            'category',
            'account',
            'is_on_credit_card',
            'is_paid',
        )
        labels = {
            'title': 'Título',
            'amount': 'Valor (R$)',
            'transaction_type': 'Tipo',
            'reference_date': 'Data de referência',
            'category': 'Categoria',
            'account': 'Conta',
            'is_paid': 'Já foi pago',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Mercado, salário, fatura...',
            }),
            'amount': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00',
            }),
            'transaction_type': forms.Select(
                attrs={'class': INPUT_CLASSES}
            ),
            'reference_date': forms.DateInput(
                attrs={'class': INPUT_CLASSES, 'type': 'date'},
                format='%Y-%m-%d',
            ),
            'category': forms.Select(attrs={'class': INPUT_CLASSES}),
            'account': forms.Select(attrs={'class': INPUT_CLASSES}),
            'is_paid': forms.CheckboxInput(attrs={
                'class': (
                    'w-4 h-4 rounded border-slate-700 bg-slate-900 '
                    'text-emerald-500 focus:ring-emerald-500/50'
                ),
            }),
        }
