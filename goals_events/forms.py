"""Forms for savings boxes and event plans."""

from django import forms

from core.models import ZERO
from users.forms import INPUT_CLASSES

from .models import EventExpenseItem, EventPlan, GoalBox

PERCENTAGE_LIMIT = 'O percentual não pode passar de 100%.'
NEGATIVE_ALLOCATION = 'O valor da alocação não pode ser negativo.'
NEGATIVE_AMOUNT = 'O valor não pode ser negativo.'
PAID_ABOVE_COST = 'O valor pago não pode ser maior que o custo total.'

CHECKBOX_CLASSES = (
    'h-4 w-4 rounded border border-slate-700 bg-slate-900 '
    'text-emerald-500 focus:ring-emerald-500/50 transition-all'
)


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
            'name': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'placeholder': 'Reserva de emergência, viagem...',
                }
            ),
            'storage_location': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'placeholder': 'Cofrinho Nubank',
                }
            ),
            'allocation_type': forms.Select(attrs={'class': INPUT_CLASSES}),
            'allocation_value': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
            'current_balance': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
            'target_amount': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
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


class EventPlanForm(forms.ModelForm):
    """Register an event plan of the logged user."""

    class Meta:
        model = EventPlan
        fields = (
            'title',
            'event_date',
            'already_saved_amount',
            'monthly_contribution_type',
            'monthly_contribution_value',
            'linked_goal_box',
            'is_active',
        )
        labels = {
            'title': 'Nome do evento',
            'event_date': 'Data do evento',
            'already_saved_amount': 'Já guardado (R$)',
            'monthly_contribution_type': 'Tipo de aporte mensal',
            'monthly_contribution_value': 'Valor do aporte mensal',
            'linked_goal_box': 'Caixinha vinculada',
            'is_active': 'Evento ativo',
        }
        help_texts = {
            'already_saved_amount': (
                'Quanto você já tem guardado para este evento.'
            ),
            'monthly_contribution_value': (
                'Percentual da renda livre ou valor fixo por mês.'
            ),
            'linked_goal_box': (
                'Caixinha usada para guardar o dinheiro deste evento.'
            ),
        }
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'placeholder': 'Casamento, viagem, reforma...',
                }
            ),
            'event_date': forms.DateInput(
                attrs={'class': INPUT_CLASSES, 'type': 'date'},
                format='%Y-%m-%d',
            ),
            'already_saved_amount': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
            'monthly_contribution_type': forms.Select(
                attrs={'class': INPUT_CLASSES}
            ),
            'monthly_contribution_value': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
            'linked_goal_box': forms.Select(attrs={'class': INPUT_CLASSES}),
            'is_active': forms.CheckboxInput(
                attrs={'class': CHECKBOX_CLASSES}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event_date'].input_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d/%m/%y',
        ]
        goal_boxes = GoalBox.objects.none()
        if user is not None:
            goal_boxes = GoalBox.objects.filter(user=user)
        self.fields['linked_goal_box'].queryset = goal_boxes
        self.fields['linked_goal_box'].required = False

    def clean(self):
        """Keep the amounts non-negative and the share up to 100%."""
        cleaned_data = super().clean()
        contribution_type = cleaned_data.get('monthly_contribution_type')
        contribution_value = cleaned_data.get('monthly_contribution_value')
        saved_amount = cleaned_data.get('already_saved_amount')
        if saved_amount is not None and saved_amount < ZERO:
            self.add_error('already_saved_amount', NEGATIVE_AMOUNT)
        if contribution_value is not None and contribution_value < ZERO:
            self.add_error('monthly_contribution_value', NEGATIVE_AMOUNT)
        if (
            contribution_type == EventPlan.ContributionType.PERCENTAGE
            and contribution_value is not None
            and contribution_value > 100
        ):
            self.add_error('monthly_contribution_value', PERCENTAGE_LIMIT)
        return cleaned_data


class EventExpenseItemForm(forms.ModelForm):
    """Register a supplier cost inside an event plan."""

    class Meta:
        model = EventExpenseItem
        fields = (
            'supplier_name',
            'category_name',
            'total_cost',
            'amount_paid',
            'notes',
        )
        labels = {
            'supplier_name': 'Fornecedor',
            'category_name': 'Categoria',
            'total_cost': 'Custo total (R$)',
            'amount_paid': 'Valor pago (R$)',
            'notes': 'Observações',
        }
        help_texts = {
            'category_name': 'Ex.: buffet, fotografia, decoração.',
        }
        widgets = {
            'supplier_name': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'placeholder': 'Buffet Alegria',
                }
            ),
            'category_name': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'placeholder': 'Buffet',
                }
            ),
            'total_cost': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
            'amount_paid': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': INPUT_CLASSES,
                    'rows': 3,
                    'placeholder': 'Forma de pagamento, parcelas...',
                }
            ),
        }

    def clean_amount_paid(self):
        """Reject a payment bigger than the supplier cost."""
        amount_paid = self.cleaned_data.get('amount_paid')
        total_cost = self.cleaned_data.get('total_cost')
        if (
            amount_paid is not None
            and total_cost is not None
            and amount_paid > total_cost
        ):
            raise forms.ValidationError(PAID_ABOVE_COST)
        return amount_paid
