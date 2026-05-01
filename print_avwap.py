"""
Run from project root:
    python print_avwap.py
"""

import math

from config.settings import settings
from src.storage.database import Database
from src.processing.anchor_vwap import compute_anchor_vwap

CANDLE_LIMIT = 1500   # must be >= largest length (1292) + buffer


def main() -> None:
    db = Database(settings.DB_PATH)
    rows = db.recent_prices(limit=CANDLE_LIMIT)
    if not rows:
        print("No data in DB. Run main.py first.")
        return

    rows = list(reversed(rows))   # oldest → newest
    print(f"Loaded {len(rows)} candles  ({rows[0].timestamp}  →  {rows[-1].timestamp})\n")

    data = {
        "high":   [r.high   for r in rows],
        "low":    [r.low    for r in rows],
        "close":  [r.close  for r in rows],
        "volume": [r.volume for r in rows],
    }

    result = compute_anchor_vwap(data)

    print(f"{'Indicator':<22}  {'Value':>14}")
    print("-" * 40)
    for key, series in result.items():
        val = series[-1]
        if math.isnan(float(val)):
            display = "           N/A"
        elif key.endswith("_trend"):
            label = {1: "1  (bullish)", -1: "-1 (bearish)", 0: "0  (neutral)"}.get(int(val), str(val))
            display = f"{label:>14}"
        elif key.endswith(("_highbars", "_lowbars")):
            display = f"{int(val):>14d}"
        else:
            display = f"{val:>14.2f}"
        print(f"{key:<22}  {display}")


if __name__ == "__main__":
    main()
