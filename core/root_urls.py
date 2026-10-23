"""Project root URL configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('', include('users.urls')),
    path('perfil/', include('profiles.urls')),
    path('contas/', include('accounts.urls')),
    path('categorias/', include('categories.urls')),
]
