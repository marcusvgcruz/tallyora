"""Forms for savings boxes and event plans."""

from django import forms

from core.models import ZERO
from users.forms import INPUT_CLASSES

from .models import GoalBox

PERCENTAGE_LIMIT = 'O percentual não pode passar de 100%.'
NEGATIVE_ALLOCATION = 'O valor da alocação não pode ser negativo.'


class GoalBoxForm(forms.ModelForm):
    """Register a savings box of the logged user."""

    class Meta:
        model = GoalBox
        fields = (
            'name',
            'storage_location',
            'allocation_type',
            'allocation_value',
            'current_balance',
            'target_amount',
        )
        labels = {
            'name': 'Nome da caixinha',
            'storage_location': 'Onde o dinheiro está',
            'allocation_type': 'Tipo de alocação',
            'allocation_value': 'Valor da alocação',
            'current_balance': 'Saldo acumulado (R$)',
            'target_amount': 'Meta (R$)',
        }
        help_texts = {
            'storage_location': (
                'Ex.: cofrinho do banco, CDB de liquidez diária.'
            ),
            'allocation_value': (
                'Percentual da renda livre ou valor fixo por período.'
            ),
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Reserva de emergência, viagem...',
            }),
            'storage_location': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Cofrinho Nubank',
            }),
            'allocation_type': forms.Select(attrs={'class': INPUT_CLASSES}),
            'allocation_value': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00',
            }),
            'current_balance': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00',
            }),
            'target_amount': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00',
            }),
        }

    def clean_allocation_value(self):
        """Reject a negative allocation."""
        value = self.cleaned_data.get('allocation_value')
        if value is not None and value < ZERO:
            raise forms.ValidationError(NEGATIVE_ALLOCATION)
        return value

    def clean(self):
        cleaned_data = super().clean()
        allocation_type = cleaned_data.get('allocation_type')
        allocation_value = cleaned_data.get('allocation_value')
        if (
            allocation_type == GoalBox.AllocationType.PERCENTAGE
            and allocation_value is not None
            and allocation_value > 100
        ):
            self.add_error('allocation_value', PERCENTAGE_LIMIT)
        return cleaned_data
