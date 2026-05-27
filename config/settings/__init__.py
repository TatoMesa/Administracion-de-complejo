import os

environment = os.environ.get('DJANGO_SETTINGS_MODULE', 'development')

if environment == 'production':
    from .production import *
else:
    from .development import *