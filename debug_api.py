"""
Clean shareable report: Angel One API request + response summary + AVWAP indicators.

Run from project root:
    python debug_api.py
"""

import json
import math
import textwrap
from datetime import datetime, timedelta
from unittest.mock import patch

import pyotp
import pytz
import requests

from config.settings import settings
from src.processing.anchor_vwap import compute_anchor_vwap
from src.storage.database import Database

IST = pytz.timezone("Asia/Kolkata")
DATE_FMT = "%Y-%m-%d %H:%M"
SEP  = "=" * 70
SEP2 = "-" * 70

# Only intercept the getCandleData call, skip login noise
_capture = {"candle_req": None, "candle_res": None, "call_count": 0}
_original_send = requests.Session.send


def _logging_send(self, prepared_request, **kwargs):
    response = _original_send(self, prepared_request, **kwargs)
    _capture["call_count"] += 1
    # getCandleData is always the last POST — capture it
    if "getCandleData" in prepared_request.url:
        _capture["candle_req"] = prepared_request
        _capture["candle_res"] = response
    return response


def _print_candle_request(req, params):
    print(f"\n{SEP}")
    print("  ANGEL ONE — getCandleData  REQUEST")
    print(SEP)
    print(f"  Method  : {req.method}")
    print(f"  URL     : {req.url}")
    print(f"  Headers :")
    for k, v in req.headers.items():
        if k.lower() in ("authorization",):
            v = "Bearer <JWT_TOKEN_REDACTED>"
        print(f"    {k}: {v}")
    print(f"  Body (JSON):")
    print(textwrap.indent(json.dumps(params, indent=4), "    "))


def _print_candle_response(res, candles):
    print(f"\n{SEP}")
    print("  ANGEL ONE — getCandleData  RESPONSE")
    print(SEP)
    print(f"  HTTP Status : {res.status_code} {res.reason}")
    print(f"  Content-Type: {res.headers.get('Content-Type', '')}")
    print(f"  x-request-id: {res.headers.get('x-request-id', '')}")
    print()
    print('  Body (JSON) — structure:')
    print('  {')
    print('    "status"   : true,')
    print('    "message"  : "SUCCESS",')
    print('    "errorcode": "",')
    print(f'    "data"     : [ ... {len(candles)} candles ... ]')
    print('  }')
    print()
    print(f"  Each candle: [timestamp, open, high, low, close, volume]")
    print(SEP2)
    print(f"  Total candles returned : {len(candles)}")
    if candles:
        print(f"  First candle           : {candles[0]}")
        print(f"  Last  candle           : {candles[-1]}")


def _print_indicators():
    db = Database(settings.DB_PATH)
    rows = db.recent_prices(limit=1500)
    if not rows:
        print("\n  No DB data — run main.py first to backfill.")
        return
    rows = list(reversed(rows))   # oldest → newest
    data = {
        "high":   [r.high   for r in rows],
        "low":    [r.low    for r in rows],
        "close":  [r.close  for r in rows],
        "volume": [r.volume for r in rows],
    }
    result = compute_anchor_vwap(data)
    print(f"  (computed from {len(rows)} candles in local DB)")

    print(f"\n{SEP}")
    print("  ANCHOR VWAP INDICATORS  (last bar)")
    print(SEP)
    print(f"  {'Indicator':<22}  {'Value':>16}")
    print(f"  {SEP2}")
    for key, series in result.items():
        val = series[-1]
        if math.isnan(float(val)):
            display = "N/A"
        elif key.endswith("_trend"):
            display = {1: "1  (bullish)", -1: "-1 (bearish)", 0: "0  (neutral)"}.get(int(val), str(val))
        elif key.endswith(("_highbars", "_lowbars")):
            display = str(int(val))
        else:
            display = f"{val:,.2f}"
        print(f"  {key:<22}  {display:>16}")
    print(SEP)


def main() -> None:
    settings.validate()

    from SmartApi import SmartConnect

    today = datetime.now(IST).date()
    from_dt = IST.localize(datetime(today.year, today.month, today.day, 4, 0))
    to_dt   = IST.localize(datetime(today.year, today.month, today.day, 4, 30))

    params = {
        "exchange":    settings.SILVER_EXCHANGE,
        "symboltoken": settings.SILVER_TOKEN,
        "interval":    "THIRTY_MINUTE",
        "fromdate":    from_dt.strftime(DATE_FMT),
        "todate":      to_dt.strftime(DATE_FMT),
    }

    print(f"\nConnecting to Angel One …  (client: {settings.ANGEL_CLIENT_CODE})")

    with patch.object(requests.Session, "send", _logging_send):
        api = SmartConnect(api_key=settings.ANGEL_API_KEY)
        totp = pyotp.TOTP(settings.ANGEL_TOTP_SECRET).now()
        session_data = api.generateSession(
            settings.ANGEL_CLIENT_CODE, settings.ANGEL_PASSWORD, totp
        )
        if session_data.get("status") is False:
            print(f"Login failed: {session_data.get('message')}")
            return
        print("Login successful. Fetching candles …")
        response = api.getCandleData(params)

    candles = response.get("data") or []
    if not candles:
        print("\nNo candles returned — check SILVER_TOKEN in .env or market hours.")
        return

    req = _capture["candle_req"]
    res = _capture["candle_res"]

    _print_candle_request(req, params)
    _print_candle_response(res, candles)
    _print_indicators()


if __name__ == "__main__":
    main()
