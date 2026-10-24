"""Django settings for the Tallyora project."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    """Return an environment variable parsed as a boolean."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=None):
    """Return a comma-separated environment variable as a list."""
    value = os.environ.get(name)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]


SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured(
        'SECRET_KEY is not set. Define it in the .env file.'
    )

# Ambiente de execução: ``dev`` usa SQLite; ``prd`` usa PostgreSQL.
APP_ENV = (os.environ.get('APP_ENV') or 'dev').strip().lower()
if APP_ENV not in ('dev', 'prd'):
    raise ImproperlyConfigured(
        "APP_ENV must be 'dev' or 'prd'. Received: " f'{APP_ENV!r}'
    )

DEBUG = env_bool('DEBUG', default=APP_ENV == 'dev')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tailwind',
    'theme',
    'accounts',
    'categories',
    'goals_events',
    'investments',
    'reminders',
    'profiles',
    'transactions',
    'users',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.root_urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database

if APP_ENV == 'prd':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'tallyora'),
            'USER': os.environ.get('DB_USER', 'tallyora'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        },
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        },
    }


# Authentication

AUTH_USER_MODEL = 'users.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'UserAttributeSimilarityValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.' 'MinimumLengthValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'CommonPasswordValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'NumericPasswordValidator'
        ),
    },
]

LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'core:landing'


# Internationalization

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = 'static/'

STATICFILES_DIRS = []
if (BASE_DIR / 'static').is_dir():
    STATICFILES_DIRS.append(BASE_DIR / 'static')

# Destination of ``collectstatic`` (used by the container/production).
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise serves the collected files under gunicorn (no nginx needed).
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': ('whitenoise.storage.CompressedManifestStaticFilesStorage'),
    },
}

# Project translations on top of the Django catalogue.
LOCALE_PATHS = [BASE_DIR / 'locale']


# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Email — Django 6.1 configura pelo dicionário ``MAILERS``.
# Sem SMTP no .env, a mensagem (ex.: redefinição de senha) sai no terminal.

DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL', 'Tallyora <nao-responda@tallyora.local>'
)

if os.environ.get('EMAIL_HOST'):
    MAILERS = {
        'default': {
            'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
            'OPTIONS': {
                'host': os.environ['EMAIL_HOST'],
                'port': int(os.environ.get('EMAIL_PORT') or 587),
                'username': os.environ.get('EMAIL_HOST_USER', ''),
                'password': os.environ.get('EMAIL_HOST_PASSWORD', ''),
                'use_tls': env_bool('EMAIL_USE_TLS', True),
            },
        },
    }
else:
    MAILERS = {
        'default': {
            'BACKEND': 'django.core.mail.backends.console.EmailBackend',
        },
    }


# Tailwind CSS

TAILWIND_APP_NAME = 'theme'

INTERNAL_IPS = ['127.0.0.1']

NPM_BIN_PATH = os.environ.get('NPM_BIN_PATH', 'npm')
