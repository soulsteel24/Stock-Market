import os
from celery import Celery

# Use environment variables for Redis URL or fallback to localhost
REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "stock_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"]
)

# Enable synchronous execution for local testing without Redis
ALWAYS_EAGER = os.getenv("CELERY_ALWAYS_EAGER", "false").lower() == "true"

celery_app.conf.update(
    task_always_eager=ALWAYS_EAGER,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    worker_concurrency=4  # Adjust based on server capacity
)

# Optional: Configuration for scheduled tasks (Overnight Scan)
celery_app.conf.beat_schedule = {
    "run-overnight-scan": {
        "task": "app.tasks.run_overnight_universe_scan",
        "schedule": 24 * 60 * 60,  # Or a crontab for midnight
        # e.g., from celery.schedules import crontab
        # 'schedule': crontab(hour=1, minute=0)
    }
}
