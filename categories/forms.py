from django import forms

from users.forms import INPUT_CLASSES

from .models import Category


class CategoryForm(forms.ModelForm):
    """Form to register a transaction category of the logged user."""

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    class Meta:
        model = Category
        fields = ('name', 'category_type', 'color_hex')
        labels = {
            'name': 'Nome da categoria',
            'category_type': 'Tipo',
            'color_hex': 'Cor (hexadecimal)',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Moradia, Alimentação...',
            }),
            'category_type': forms.Select(attrs={'class': INPUT_CLASSES}),
            'color_hex': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': '#10b981',
                'maxlength': '7',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        category_type = cleaned_data.get('category_type')
        if self.user and name and category_type:
            duplicated = Category.objects.filter(
                user=self.user,
                name__iexact=name,
                category_type=category_type,
            )
            if self.instance.pk:
                duplicated = duplicated.exclude(pk=self.instance.pk)
            if duplicated.exists():
                self.add_error(
                    'name',
                    'Já existe uma categoria com este nome e tipo.',
                )
        return cleaned_data

    def clean_color_hex(self):
        color_hex = self.cleaned_data['color_hex'].strip()
        if not color_hex.startswith('#'):
            color_hex = f'#{color_hex}'
        return color_hex.lower()
