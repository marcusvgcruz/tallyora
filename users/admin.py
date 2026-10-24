from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import UserAdminChangeForm, UserAdminCreationForm
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for the e-mail based user model."""

    model = CustomUser
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    fieldsets = (
        (
            None,
            {
                'fields': ('email', 'password'),
            },
        ),
        (
            'Informações pessoais',
            {
                'fields': ('first_name', 'last_name'),
            },
        ),
        (
            'Permissões',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        (
            'Datas importantes',
            {
                'fields': ('last_login', 'date_joined'),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'first_name',
                    'last_name',
                    'password1',
                    'password2',
                ),
            },
        ),
    )
