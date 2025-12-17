"""Celery background task configuration"""
from celery import Celery
from app.config import settings

# Initialize Celery
celery_app = Celery(
    "clinicbot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Kolkata',
    enable_utc=True,
    task_routes={
        'app.tasks.reminders.*': {'queue': 'reminders'},
        'app.tasks.events.*': {'queue': 'events'},
        'app.tasks.summary.*': {'queue': 'summary'},
    }
)
