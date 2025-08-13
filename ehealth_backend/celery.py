from celery import Celery
from celery.schedules import crontab

# app = Celery('your_app')
# app.conf.beat_schedule = {
#     'check-expired-payments': {
#         'task': 'your_app.tasks.check_expired_payments',
#         'schedule': crontab(minute='*/5'),  # Every 5 minutes
#     },
# }

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ehealth_backend.settings')
app = Celery('ehealth_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()