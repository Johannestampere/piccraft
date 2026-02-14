from celery import Celery
from app.config import settings

celery = Celery(
    "piccraft",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=3600,
    task_track_started=True,
)

celery.autodiscover_tasks(["app.tasks"])