from celery import Celery

from app.infrastructure.config import get_settings

settings = get_settings()
celery_app = Celery("maintenance_worker", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_routes = {"app.infrastructure.worker.*": {"queue": "maintenance"}}


@celery_app.task(name="app.infrastructure.worker.reindex_documents")
def reindex_documents() -> str:
    return "Document reindex task placeholder executed."
