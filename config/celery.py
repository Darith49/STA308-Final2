import os

# Set default Django settings module for 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

try:
    from celery import Celery
    app = Celery('portal')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()
except ImportError:
    app = None
