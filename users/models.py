from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from core.models import BaseModel


class CustomUserManager(BaseUserManager):
    """Manager for users authenticated by e-mail."""

    def normalize_email_address(self, email):
        """Normalize the e-mail address used as login identifier."""
        if not email:
            raise ValueError('The e-mail address is required.')
        return self.normalize_email(email).lower()

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        user = self.model(
            email=self.normalize_email_address(email),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser, BaseModel):
    """Application user authenticated by e-mail instead of username."""

    username = None
    email = models.EmailField('E-mail', unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'

    def __str__(self):
        return self.email
