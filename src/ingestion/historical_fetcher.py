from datetime import datetime, timedelta, timezone
from typing import Any

import pytz
from logzero import logger

from config.settings import settings
from src.ingestion.angel_one_client import AngelOneClient

IST = pytz.timezone("Asia/Kolkata")
DATE_FMT = "%Y-%m-%d %H:%M"


def _parse_candle(candle: list[Any]) -> dict:
    """Convert raw API candle [ts, o, h, l, c, vol] to a storage-ready dict."""
    raw_ts = candle[0]
    if isinstance(raw_ts, str):
        # Angel One returns ISO-like strings: "2024-01-15T09:15:00+05:30"
        dt = datetime.fromisoformat(raw_ts)
        if dt.tzinfo is None:
            dt = IST.localize(dt)
    else:
        dt = datetime.fromtimestamp(raw_ts / 1000, tz=timezone.utc)

    return {
        "timestamp": dt.astimezone(timezone.utc),
        "open": float(candle[1]),
        "high": float(candle[2]),
        "low": float(candle[3]),
        "close": float(candle[4]),
        "volume": float(candle[5]),
        "symbol": settings.SILVER_SYMBOL,
    }


class HistoricalFetcher:
    """Fetches historical minute-level silver candle data from Angel One."""

    # MCX sessions: 09:00 – 23:30 IST on weekdays
    MAX_DAYS_PER_REQUEST = 30  # Angel One cap for ONE_MINUTE interval

    def __init__(self, client: AngelOneClient) -> None:
        self._client = client

    def fetch_last_n_days(self, days: int = 7) -> list[dict]:
        """Return parsed candle dicts for the past `days` calendar days."""
        now_ist = datetime.now(IST)
        to_dt = now_ist
        from_dt = now_ist - timedelta(days=days)

        all_candles: list[dict] = []
        chunk_start = from_dt

        while chunk_start < to_dt:
            chunk_end = min(chunk_start + timedelta(days=self.MAX_DAYS_PER_REQUEST), to_dt)
            logger.info(
                "Fetching historical data %s → %s",
                chunk_start.strftime(DATE_FMT),
                chunk_end.strftime(DATE_FMT),
            )
            try:
                raw = self._client.get_candle_data(
                    exchange=settings.SILVER_EXCHANGE,
                    symbol_token=settings.SILVER_TOKEN,
                    interval="ONE_MINUTE",
                    from_date=chunk_start.strftime(DATE_FMT),
                    to_date=chunk_end.strftime(DATE_FMT),
                )
                all_candles.extend(_parse_candle(c) for c in raw)
                logger.info("Retrieved %d candles in this chunk", len(raw))
            except Exception as exc:
                logger.error("Failed to fetch chunk %s → %s: %s", chunk_start, chunk_end, exc)

            chunk_start = chunk_end

        logger.info("Total historical candles fetched: %d", len(all_candles))
        return all_candles

    def fetch_latest_candle(self) -> dict | None:
        """Fetch the most recent completed 1-minute candle."""
        now_ist = datetime.now(IST)
        from_dt = now_ist - timedelta(minutes=5)
        try:
            raw = self._client.get_candle_data(
                exchange=settings.SILVER_EXCHANGE,
                symbol_token=settings.SILVER_TOKEN,
                interval="ONE_MINUTE",
                from_date=from_dt.strftime(DATE_FMT),
                to_date=now_ist.strftime(DATE_FMT),
            )
            if raw:
                return _parse_candle(raw[-1])
        except Exception as exc:
            logger.error("Failed to fetch latest candle: %s", exc)
        return None
