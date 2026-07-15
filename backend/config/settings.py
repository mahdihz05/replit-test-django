import os
from datetime import timedelta
from pathlib import Path
import dj_database_url
from decouple import Config, RepositoryEnv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local development secrets from the repository's ignored .env file.
# Explicit process environment variables always take precedence.
_env_file = BASE_DIR.parent / '.env'
if _env_file.is_file() and os.access(_env_file, os.R_OK):
    _local_env = Config(RepositoryEnv(str(_env_file)))
    for _name in (
        'SECRET_KEY',
        'DEBUG',
        'DATABASE_URL',
        'MEDIA_ROOT',
        'OPENAI_API_KEY',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_POLLING_ENABLED',
        'TELEGRAM_PROXY_URL',
        'TELEGRAM_TRUST_ENV_PROXY',
        'SERVE_MEDIA_FILES',
        'LINKEDIN_CLIENT_ID',
        'LINKEDIN_CLIENT_SECRET',
        'LINKEDIN_REDIRECT_URI',
        'LINKEDIN_TOKEN_ENCRYPTION_KEY',
        'SHARED_TOKEN_ENCRYPTION_KEY',
        'LINKEDIN_API_VERSION',
        'LINKEDIN_ORG_ENABLED',
        'ALLOWED_HOSTS',
        'CORS_ALLOWED_ORIGINS',
        'CSRF_TRUSTED_ORIGINS',
        'SECURE_SSL_REDIRECT',
    ):
        if _name not in os.environ:
            _value = _local_env(_name, default='')
            if _value:
                os.environ[_name] = _value

_secret = os.environ.get('SECRET_KEY') or os.environ.get('SESSION_SECRET')
if not _secret:
    raise RuntimeError("SECRET_KEY or SESSION_SECRET environment variable must be set")
SECRET_KEY = _secret

DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

_allowed = os.environ.get('ALLOWED_HOSTS', '')
if _allowed:
    ALLOWED_HOSTS = [h for h in _allowed.split(',') if h]
else:
    # Dev: allow all hosts (Replit proxies requests through its own domain).
    # Production: set ALLOWED_HOSTS env var to your actual domain.
    ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'config',
    'users',
    'workspaces',
    'content',
    'ai_engine',
    'channels_app',
    'publishing',
    'wallet',
    'reports',
    'bots',
    'communication',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', str(BASE_DIR / 'media'))
SERVE_MEDIA_FILES = os.environ.get('SERVE_MEDIA_FILES', 'false').lower() in ('true', '1', 'yes')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

_cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '')
if _cors_origins:
    CORS_ALLOWED_ORIGINS = [o for o in _cors_origins.split(',') if o]
    CORS_ALLOW_CREDENTIALS = True
else:
    # Dev fallback: allow all origins but disable credentials to avoid CSRF risk
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = False

# CSRF configuration for Django admin panel and any session-based views.
# In production set CSRF_TRUSTED_ORIGINS to your actual HTTPS origin(s).
_replit_domain = os.environ.get('REPLIT_DEV_DOMAIN', '')
_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]
elif _replit_domain:
    CSRF_TRUSTED_ORIGINS = [f'https://{_replit_domain}']
else:
    CSRF_TRUSTED_ORIGINS = []

CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False

# OAuth starts through an authenticated API request and returns through a
# top-level cross-site navigation. Lax preserves that callback session while
# Secure/HttpOnly keep the session identifier out of scripts and cleartext HTTP.
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.environ.get(
    'SECURE_SSL_REDIRECT', 'true' if not DEBUG else 'false'
).lower() in ('true', '1', 'yes')
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_POLLING_ENABLED = os.environ.get('TELEGRAM_POLLING_ENABLED', 'true').lower() in ('true', '1', 'yes')
TELEGRAM_PROXY_URL = os.environ.get('TELEGRAM_PROXY_URL', '').strip()
TELEGRAM_TRUST_ENV_PROXY = os.environ.get('TELEGRAM_TRUST_ENV_PROXY', 'false').lower() in ('true', '1', 'yes')
LINKEDIN_CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID', '')
LINKEDIN_CLIENT_SECRET = os.environ.get('LINKEDIN_CLIENT_SECRET', '')
LINKEDIN_TOKEN_ENCRYPTION_KEY = os.environ.get('LINKEDIN_TOKEN_ENCRYPTION_KEY', '')
SHARED_TOKEN_ENCRYPTION_KEY = os.environ.get('SHARED_TOKEN_ENCRYPTION_KEY', '')
LINKEDIN_REDIRECT_URI = os.environ.get('LINKEDIN_REDIRECT_URI', '')
LINKEDIN_API_VERSION = os.environ.get('LINKEDIN_API_VERSION', '202606')
LINKEDIN_ORG_ENABLED = os.environ.get('LINKEDIN_ORG_ENABLED', 'false').lower() in ('true', '1', 'yes')
BALE_BOT_TOKEN = os.environ.get('BALE_BOT_TOKEN', '')
SMS_API_KEY = os.environ.get('SMS_API_KEY', '')
SMS_SENDER = os.environ.get('SMS_SENDER', '')

# Static compatibility export. Runtime code uses config.ai.get_wallet_cost so
# admin changes take effect without modifying application logic.
from .ai import WALLET_COSTS
