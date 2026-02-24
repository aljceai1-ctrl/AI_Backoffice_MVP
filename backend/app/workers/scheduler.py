"""Background scheduler for email polling."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.workers.email_poller import poll_and_ingest

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def start_scheduler():
    """Start the email polling scheduler."""
    scheduler.add_job(
        poll_and_ingest,
        "interval",
        seconds=settings.EMAIL_POLL_INTERVAL_SECONDS,
        id="email_poller",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Email poller scheduled every %d seconds", settings.EMAIL_POLL_INTERVAL_SECONDS)


def stop_scheduler():
    """Shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
