"""
WSGI config for ecom_prj project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

# Применяем патч для совместимости Django 4.2 с Python 3.14
from ecom_prj import django_python314_patch

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom_prj.settings')

application = get_wsgi_application()
