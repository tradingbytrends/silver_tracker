from dataclasses import dataclass
from datetime import timezone
from typing import Optional

from logzero import logger

from src.storage.database import Database, MinutePrice


@dataclass
class PriceSummary:
    current_price: float
    prev_close: Optional[float]
    change: Optional[float]
    change_pct: Optional[float]
    high_1h: Optional[float]
    low_1h: Optional[float]
    high_1d: Optional[float]
    low_1d: Optional[float]
    timestamp: str

    def format_message(self) -> str:
        lines = [
            f"*Silver Price Update*",
            f"Price: ₹{self.current_price:,.2f}",
            f"Time : {self.timestamp} IST",
        ]
        if self.change is not None:
            direction = "▲" if self.change >= 0 else "▼"
            lines.append(
                f"Change: {direction} ₹{abs(self.change):,.2f} ({self.change_pct:+.2f}%)"
            )
        if self.high_1h and self.low_1h:
            lines.append(f"1H Range: ₹{self.low_1h:,.2f} – ₹{self.high_1h:,.2f}")
        if self.high_1d and self.low_1d:
            lines.append(f"Day Range: ₹{self.low_1d:,.2f} – ₹{self.high_1d:,.2f}")
        return "\n".join(lines)


class PriceProcessor:
    """Derives analytics from stored minute-level data."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def compute_summary(self, reference_minutes_back: int = 15) -> Optional[PriceSummary]:
        latest: Optional[MinutePrice] = self._db.latest_price()
        if latest is None:
            logger.warning("No price data available in database")
            return None

        recent: list[MinutePrice] = self._db.recent_prices(limit=60 * 24)  # up to 24h
        if not recent:
            return None

        closes = [r.close for r in recent]
        highs = [r.high for r in recent]
        lows = [r.low for r in recent]

        # 1-hour window (last 60 candles)
        high_1h = max(highs[:60]) if len(highs) >= 1 else None
        low_1h = min(lows[:60]) if len(lows) >= 1 else None

        # Full day window
        high_1d = max(highs) if highs else None
        low_1d = min(lows) if lows else None

        # Price change relative to N minutes ago
        ref = self._db.price_n_minutes_ago(reference_minutes_back)
        change: Optional[float] = None
        change_pct: Optional[float] = None
        if ref and ref.close:
            change = latest.close - ref.close
            change_pct = (change / ref.close) * 100

        import pytz
        IST = pytz.timezone("Asia/Kolkata")
        ts_ist = latest.timestamp.replace(tzinfo=timezone.utc).astimezone(IST)

        return PriceSummary(
            current_price=latest.close,
            prev_close=closes[1] if len(closes) > 1 else None,
            change=change,
            change_pct=change_pct,
            high_1h=high_1h,
            low_1h=low_1h,
            high_1d=high_1d,
            low_1d=low_1d,
            timestamp=ts_ist.strftime("%Y-%m-%d %H:%M"),
        )
