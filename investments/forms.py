"""Forms for the investment portfolio."""

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseModelFormSet, modelformset_factory
from django.forms.models import construct_instance

from users.forms import INPUT_CLASSES

from .models import AssetAllocationTarget, InvestmentAsset

DUPLICATED_TICKER = 'Você já cadastrou o ticker {ticker} na sua carteira.'


class InvestmentAssetForm(forms.ModelForm):
    """Create or edit an asset of the logged user portfolio."""

    class Meta:
        model = InvestmentAsset
        fields = (
            'asset_class',
            'ticker',
            'name',
            'quantity',
            'average_price',
            'current_price',
            'target_percentage_in_class',
        )
        labels = {
            'asset_class': 'Classe de ativo',
            'ticker': 'Ticker',
            'name': 'Nome do ativo',
            'quantity': 'Quantidade',
            'average_price': 'Preço médio (R$)',
            'current_price': 'Preço atual (R$)',
            'target_percentage_in_class': 'Peso ideal na classe (%)',
        }
        help_texts = {
            'ticker': (
                'Código negociado na B3, como HGLG11 ou PETR4. '
                'Cripto e renda fixa usam um código livre.'
            ),
            'current_price': (
                'Atualizado automaticamente para FII e ações. '
                'Para renda fixa e cripto, informe o valor à mão.'
            ),
        }
        widgets = {
            'asset_class': forms.Select(attrs={'class': INPUT_CLASSES}),
            'ticker': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'placeholder': 'HGLG11',
                    'autocomplete': 'off',
                    'style': 'text-transform: uppercase',
                }
            ),
            'name': forms.TextInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'placeholder': 'Fundo imobiliário, ação, CDB...',
                }
            ),
            'quantity': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.00000001',
                    'min': '0',
                    'placeholder': '0',
                }
            ),
            'average_price': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.0001',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
            'current_price': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.0001',
                    'min': '0',
                    'placeholder': '0,00',
                }
            ),
            'target_percentage_in_class': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'max': '100',
                    'placeholder': '0,00',
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        # The ideal weight is optional: zero means "sem meta definida".
        self.fields['target_percentage_in_class'].required = False

    def clean_ticker(self):
        """Store the ticker in upper case and free of spaces."""
        ticker = (self.cleaned_data.get('ticker') or '').strip().upper()
        if not ticker:
            raise forms.ValidationError('Informe o ticker do ativo.')
        return ticker

    def clean(self):
        """Reject a ticker already used by the same user.

        The ``UniqueConstraint(user, ticker)`` of the model is not checked
        by the ModelForm, so the duplication is validated here.
        """
        cleaned = super().clean()
        ticker = cleaned.get('ticker')
        if not ticker or self.user is None:
            return cleaned
        duplicates = InvestmentAsset.objects.filter(
            user=self.user,
            ticker=ticker,
        )
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            self.add_error(
                'ticker',
                DUPLICATED_TICKER.format(ticker=ticker),
            )
        return cleaned


class AllocationTargetForm(forms.ModelForm):
    """One row of the allocation targets formset."""

    class Meta:
        model = AssetAllocationTarget
        fields = ('asset_class', 'target_percentage')
        widgets = {
            'asset_class': forms.Select(attrs={'class': INPUT_CLASSES}),
            'target_percentage': forms.NumberInput(
                attrs={
                    'class': INPUT_CLASSES,
                    'step': '0.01',
                    'min': '0',
                    'max': '100',
                    'placeholder': '0,00',
                }
            ),
        }

    def _post_clean(self):
        """Validate the fields, leaving the total rule to the view.

        ``AssetAllocationTarget.clean()`` compares a single row with the
        rows already stored. That is wrong for a batch edit: while the
        formset saves, the stored rows are still the old ones, so a valid
        rebalance would be refused. The aggregate of the whole formset is
        checked by ``AllocationTargetUpdateView`` instead.
        """
        options = self._meta
        exclude = self._get_validation_exclusions()
        try:
            self.instance = construct_instance(
                self,
                self.instance,
                options.fields,
                options.exclude,
            )
            self.instance.clean_fields(exclude=exclude)
        except ValidationError as error:
            self._update_errors(error)


class BaseAllocationTargetFormSet(BaseModelFormSet):
    """Formset that links the logged user to every new target row.

    The user is set while the form is built (not only on save) because
    ``AssetAllocationTarget.clean()`` reads ``self.user`` and the model
    validation runs over the instance before ``formset.save()``.
    """

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def _construct_form(self, index, **kwargs):
        form = super()._construct_form(index, **kwargs)
        if form.instance.pk is not None:
            return form
        # The model default of ``target_percentage`` (0.00) would make an
        # untouched extra row look filled, so it would fail the required
        # validation. Clearing the initial keeps empty rows empty.
        form.fields['target_percentage'].initial = None
        if self.user is not None:
            form.instance.user = self.user
        return form


AllocationTargetFormSet = modelformset_factory(
    AssetAllocationTarget,
    form=AllocationTargetForm,
    fields=('asset_class', 'target_percentage'),
    extra=4,
    can_delete=True,
    formset=BaseAllocationTargetFormSet,
)
