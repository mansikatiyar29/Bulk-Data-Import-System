"""WSGI config for bulk_import_system project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bulk_import_system.settings')
application = get_wsgi_application()