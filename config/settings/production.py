from .base import *
import os
import dj_database_url

DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Base de datos desde variable de entorno
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600
    )
}

# Seguridad
SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)

# Whitenoise para archivos estáticos
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = BASE_DIR / 'staticfiles'

CSRF_TRUSTED_ORIGINS = [
    'https://web-production-490a4.up.railway.app',
]