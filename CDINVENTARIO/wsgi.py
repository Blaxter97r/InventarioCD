"""
WSGI config for CDINVENTARIO project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from .django_compat import ensure_django_cache_module

ensure_django_cache_module()
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CDINVENTARIO.settings')

application = get_wsgi_application()
