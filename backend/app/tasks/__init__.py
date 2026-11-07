from celery import Celery

from app.config import get_settings

celery = Celery(
    "livesrl", broker=get_settings().redis_url, include=["app.tasks.mail", "app.tasks.ingest"]
)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    broker_connection_retry_on_startup=True,
    task_ignore_result=True,
    task_send_sent_event=True,
    beat_schedule={},
)
