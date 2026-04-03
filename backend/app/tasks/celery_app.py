"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab
import os

broker_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "apex_screener",
    broker=broker_url,
    result_backend=broker_url,
    include=["app.tasks.scheduled"], "app.tasks.equity_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_max_tasks_per_child=100,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_concurrency=2,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    # Module 1: Macroéconomie — Daily at 18:00 UTC (après fermeture marchés US)
    "sync-macro-data": {
        "task": "app.tasks.scheduled.task_sync_macro",
        "schedule": crontab(hour=18, minute=0),
    },

    # Module 2: Radar Sectoriel — Daily at 22:00 UTC (après fermeture marchés)
    "sync-sector-data": {
        "task": "app.tasks.scheduled.task_sync_sectors",
        "schedule": crontab(hour=22, minute=0),
    },

    # Module 3a: Screener Crypto — Every 6 hours
    "sync-crypto-fundamentals": {
        "task": "app.tasks.scheduled.task_sync_crypto",
        "schedule": crontab(hour="*/6", minute=15),
    },

    # Module 3b: Screener Actions — Every Sunday at 23:00 UTC (données trimestrielles)
    # FIX: cette tâche manquait entièrement, causant STOCKS: 0
    "sync-stock-fundamentals-batch": {
        "task": "app.tasks.scheduled.task_sync_stock_fundamentals_batch",
        "schedule": crontab(hour=23, minute=0, day_of_week="0"),
    },

    # Module 4: Traqueur d'Initiés — Every 30 minutes during market hours
    "scan-insider-filings": {
        "task": "app.tasks.scheduled.task_scan_insiders",
        "schedule": crontab(minute="*/30", hour="13-22"),  # 13-22 UTC = 8-17 EST
    },

    # Alert Engine: Equity workflow — Every 30 minutes (after insider scan)
    "process-equity-alerts": {
        "task": "app.tasks.scheduled.task_process_equity_alerts",
        "schedule": crontab(minute="15,45", hour="13-22"),
    },

    # Alert Engine: Crypto workflow — Every 6 hours (after crypto sync)
    "process-crypto-alerts": {
        "task": "app.tasks.scheduled.task_process_crypto_alerts",
        "schedule": crontab(hour="*/6", minute=30),
    },
}
