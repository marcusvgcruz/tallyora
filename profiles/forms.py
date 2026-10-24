from django import forms

from users.forms import INPUT_CLASSES

from .models import PayrollDeduction, UserProfile

PERCENTAGE_ERROR = 'O percentual deve estar entre 0 e 100.'


class UserProfileForm(forms.ModelForm):
    """Form to edit the financial profile of the logged user."""

    class Meta:
        model = UserProfile
        fields = (
            'work_regime',
            'payment_frequency',
            'base_gross_income',
            'advance_percentage',
            'has_investments',
            'investment_allocation_type',
            'investment_allocation_value',
        )
        labels = {
            'work_regime': 'Regime de trabalho',
            'payment_frequency': 'Periodicidade de recebimento',
            'base_gross_income': 'Renda bruta base (R$)',
            'advance_percentage': 'Percentual de adiantamento (%)',
            'has_investments': 'Investe mensalmente',
            'investment_allocation_type': 'Tipo de alocação',
            'investment_allocation_value': 'Valor da alocação',
        }
        widgets = {
            'work_regime': forms.Select(attrs={'class': INPUT_CLASSES}),
            'payment_frequency': forms.Select(attrs={'class': INPUT_CLASSES}),
            'base_gross_income': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
            'advance_percentage': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'max': '100',
                    'placeholder': '40.00',
                }
            ),
            'has_investments': forms.CheckboxInput(
                attrs={
                    'class': (
                        'w-4 h-4 rounded border-slate-700 bg-slate-900 '
                        'text-emerald-500 focus:ring-emerald-500/50'
                    ),
                }
            ),
            'investment_allocation_type': forms.Select(
                attrs={'class': INPUT_CLASSES}
            ),
            'investment_allocation_value': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
        }

    def clean_advance_percentage(self):
        value = self.cleaned_data['advance_percentage']
        if value is None or value < 0 or value > 100:
            raise forms.ValidationError(PERCENTAGE_ERROR)
        return value

    def clean(self):
        cleaned_data = super().clean()
        allocation_type = cleaned_data.get('investment_allocation_type')
        allocation_value = cleaned_data.get('investment_allocation_value')
        if allocation_type == UserProfile.InvestmentAllocationType.PERCENTAGE:
            if allocation_value is None:
                self.add_error(
                    'investment_allocation_value',
                    'Informe o percentual da renda líquida.',
                )
            elif allocation_value < 0 or allocation_value > 100:
                self.add_error(
                    'investment_allocation_value',
                    PERCENTAGE_ERROR,
                )
        return cleaned_data


class PayrollDeductionForm(forms.ModelForm):
    """Form to register a payroll deduction of the logged user."""

    class Meta:
        model = PayrollDeduction
        fields = ('name', 'amount', 'is_active')
        labels = {
            'name': 'Nome do desconto',
            'amount': 'Valor (R$)',
            'is_active': 'Desconto ativo',
        }
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'placeholder': 'INSS, IRRF, consignado...',
                }
            ),
            'amount': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
            'is_active': forms.CheckboxInput(
                attrs={
                    'class': (
                        'w-4 h-4 rounded border-slate-700 bg-slate-900 '
                        'text-emerald-500 focus:ring-emerald-500/50'
                    ),
                }
            ),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount is not None and amount < 0:
            raise forms.ValidationError(
                'O valor do desconto não pode ser negativo.'
            )
        return amount
