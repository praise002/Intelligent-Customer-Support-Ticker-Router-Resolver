from celery import Celery
from celery.schedules import crontab
from kombu import Queue

REDIS_URL = "redis://localhost:6378/0"

celery_app = Celery("ticket_router", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_queue_max_priority=10,
    task_default_priority=5,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,  # Take 1 task at a time (respects priority)
    worker_max_tasks_per_child=100,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "tasks.classify_ticket": {"queue": "classification"},
        "tasks.process_llm": {"queue": "processing"},
    },
)

celery_app.conf.task_queues = (
    # Classification queue (no priority needed)
    Queue("classification", routing_key="classification"),
    # Processing queue (priority enabled)
    Queue(
        "processing", routing_key="processing", queue_arguments={"x-max-priority": 10}
    ),
)


beat_schedule = {
    "compute-metrics-hourly": {
        "task": "src.tasks.compute_daily_metrics",
        "schedule": crontab(minute=0),  # Every hour at :00
    }
}
