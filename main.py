"""
Silver Tracker — main entry point.

Architecture:
  Ingestion  →  Storage (SQLite)  →  Processing  →  Notifications (WhatsApp)

Scheduler runs two jobs:
  1. price_job   — every PRICE_FETCH_INTERVAL seconds, fetches latest 1-min candle
  2. notify_job  — every 15–20 minutes (randomized), sends WhatsApp summary
"""

import logging
import os
import sys

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from logzero import logger, loglevel

from config.settings import settings
from src.ingestion.angel_one_client import AngelOneClient
from src.ingestion.historical_fetcher import HistoricalFetcher
from src.notifications.whatsapp_notifier import WhatsAppNotifier
from src.processing.price_processor import PriceProcessor
from src.storage.database import Database

IST = pytz.timezone("Asia/Kolkata")


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    loglevel(level)
    os.makedirs("logs", exist_ok=True)

    file_handler = logging.FileHandler("logs/silver_tracker.log", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logging.getLogger().addHandler(file_handler)


def price_job(
    client: AngelOneClient,
    fetcher: HistoricalFetcher,
    db: Database,
) -> None:
    """Fetch the latest 1-minute candle and persist it."""
    try:
        candle = fetcher.fetch_latest_candle()
        if candle:
            db.upsert_minute_price(candle)
            logger.debug("Stored candle: ts=%s close=%.2f", candle["timestamp"], candle["close"])
    except Exception as exc:
        logger.error("price_job error: %s", exc)


def notify_job(
    processor: PriceProcessor,
    notifier: WhatsAppNotifier,
    scheduler: BlockingScheduler,
) -> None:
    """Build a price summary and send a WhatsApp notification."""
    try:
        summary = processor.compute_summary(reference_minutes_back=15)
        if summary is None:
            logger.warning("notify_job: no summary available yet")
            return

        message = summary.format_message()
        notifier.send(
            message=message,
            price=summary.current_price,
            change=summary.change,
            change_pct=summary.change_pct,
        )

        # Re-schedule notify_job with a fresh random interval (15–20 min)
        next_interval = settings.notification_interval_seconds()
        logger.info("Next notification in %d seconds", next_interval)
        job = scheduler.get_job("notify_job")
        if job:
            job.reschedule(trigger=IntervalTrigger(seconds=next_interval))

    except Exception as exc:
        logger.error("notify_job error: %s", exc)


def bootstrap_historical(fetcher: HistoricalFetcher, db: Database) -> None:
    logger.info("Bootstrapping: fetching last 7 days of silver history …")
    candles = fetcher.fetch_last_n_days(days=7)
    if candles:
        inserted = db.bulk_upsert(candles)
        logger.info("Historical bootstrap complete: %d new candles inserted", inserted)
    else:
        logger.warning("No historical candles returned during bootstrap")


def main() -> None:
    setup_logging()
    logger.info("=== Silver Tracker starting ===")

    try:
        settings.validate()
    except EnvironmentError as exc:
        logger.error(str(exc))
        sys.exit(1)

    # Initialise layers
    db = Database(settings.DB_PATH)
    client = AngelOneClient()
    client.login()

    fetcher = HistoricalFetcher(client)
    processor = PriceProcessor(db)
    notifier = WhatsAppNotifier(db)

    # One-time historical backfill
    bootstrap_historical(fetcher, db)

    # Scheduler
    scheduler = BlockingScheduler(timezone=IST)

    scheduler.add_job(
        price_job,
        trigger=IntervalTrigger(seconds=settings.PRICE_FETCH_INTERVAL),
        id="price_job",
        kwargs={"client": client, "fetcher": fetcher, "db": db},
        max_instances=1,
        coalesce=True,
    )

    initial_notify_interval = settings.notification_interval_seconds()
    scheduler.add_job(
        notify_job,
        trigger=IntervalTrigger(seconds=initial_notify_interval),
        id="notify_job",
        kwargs={"processor": processor, "notifier": notifier, "scheduler": scheduler},
        max_instances=1,
        coalesce=True,
    )

    logger.info(
        "Scheduler started — price every %ds, first notification in %ds",
        settings.PRICE_FETCH_INTERVAL,
        initial_notify_interval,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Silver Tracker stopped by user")


if __name__ == "__main__":
    main()
