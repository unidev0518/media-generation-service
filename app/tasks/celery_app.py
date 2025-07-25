"""Celery application configuration."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

# Create Celery instance
celery_app = Celery("media_generation")

# Configure Celery
celery_app.config_from_object(settings.celery_config, namespace="")

# Auto-discover tasks
celery_app.autodiscover_tasks([
    "app.tasks.generation_tasks",
])

# Task routing
celery_app.conf.task_routes = {
    "app.tasks.generation_tasks.*": {"queue": "generation"},
}

# Additional configuration
celery_app.conf.update(
    # Task execution
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Retry settings
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
) 