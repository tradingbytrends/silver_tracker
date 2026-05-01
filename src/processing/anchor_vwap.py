"""
Anchor VWAP (MIDAS) indicator — pure calculation, no plotting, no third-party deps.

Input : dict with keys  high, low, close, volume  (each a plain Python list of floats)
Output: dict with keys  ma{n}_highbars, ma{n}_lowbars, ma{n}_top_high, etc.
"""

import math


def highestbars(high: list, length: int) -> list:
    """Pine: highestbars(length) * -1  →  bars-back offset to highest high."""
    n = len(high)
    result = [math.nan] * n
    for i in range(length - 1, n):
        window = high[i - length + 1 : i + 1]
        max_val = max(window)
        max_idx = window.index(max_val)        # first (oldest) occurrence
        result[i] = (length - 1) - max_idx
    return result


def lowestbars(low: list, length: int) -> list:
    """Pine: lowestbars(length) * -1  →  bars-back offset to lowest low."""
    n = len(low)
    result = [math.nan] * n
    for i in range(length - 1, n):
        window = low[i - length + 1 : i + 1]
        min_val = min(window)
        min_idx = window.index(min_val)
        result[i] = (length - 1) - min_idx
    return result


def _get_vwap_series(src: list, vol: list, offsets: list) -> list:
    """
    Anchored VWAP.  offsets[i] = how many bars back the anchor is for bar i.
    Pine: sum(vol[k]*src[k], k=0..length-1) / sum(vol[k], k=0..length-1)
    """
    n = len(src)
    result = [math.nan] * n
    for i in range(n):
        length = offsets[i]
        if math.isnan(length) or length < 1:
            continue
        length = int(length)
        start = i - length + 1
        if start < 0:
            continue
        v = vol[start : i + 1]
        s = src[start : i + 1]
        uvol = sum(v)
        if uvol == 0:
            continue
        result[i] = sum(vi * si for vi, si in zip(v, s)) / uvol
    return result


def get_midas(offsets: list, hlc3: list, high: list, low: list,
              volume: list, is_highest: bool) -> tuple:
    """Pine: getMidas(len, isHighest) → (mid, value)"""
    mid = _get_vwap_series(hlc3, volume, offsets)
    src = high if is_highest else low
    value = _get_vwap_series(src, volume, offsets)
    return mid, value


def get_midas_trend(vtop: list, vbot: list, close: list) -> list:
    """
    Pine: getMidasTrend(vtop, vbot)
     1  = bullish,  -1  = bearish,  0 = neutral
    """
    result = [0] * len(close)
    for i in range(len(close)):
        top, bot, c = vtop[i], vbot[i], close[i]
        top_na = math.isnan(top)
        bot_na = math.isnan(bot)
        bull = (top_na or c > top) and (not bot_na and c > bot)
        bear = (bot_na or c < bot) and (not top_na and c < top)
        if bull:
            result[i] = 1
        elif bear:
            result[i] = -1
    return result


def compute_anchor_vwap(data: dict, lengths: list = None) -> dict:
    """
    Main entry point.

    Parameters
    ----------
    data    : dict with lists  high, low, close, volume
    lengths : lookback bar counts  (default: [17, 72, 305, 1292])

    Returns
    -------
    dict of lists:
        ma{n}_highbars   bars-back to highest high
        ma{n}_lowbars    bars-back to lowest low
        ma{n}_top_mid    hlc3 anchored-VWAP from highest-high bar
        ma{n}_top_high   high anchored-VWAP from highest-high bar
        ma{n}_bot_mid    hlc3 anchored-VWAP from lowest-low bar
        ma{n}_bot_low    low  anchored-VWAP from lowest-low bar
        ma{n}_trend      1 bull / -1 bear / 0 neutral
    """
    if lengths is None:
        lengths = [17, 72, 305, 1292]

    high   = data["high"]
    low    = data["low"]
    close  = data["close"]
    volume = data["volume"]
    hlc3   = [(h + l + c) / 3 for h, l, c in zip(high, low, close)]

    out = {}
    for n, length in enumerate(lengths, start=1):
        prefix = f"ma{n}"

        hbars = highestbars(high, length)
        lbars = lowestbars(low, length)

        out[f"{prefix}_highbars"] = hbars
        out[f"{prefix}_lowbars"]  = lbars

        top_mid, top_high = get_midas(hbars, hlc3, high, low, volume, is_highest=True)
        bot_mid, bot_low  = get_midas(lbars, hlc3, high, low, volume, is_highest=False)

        out[f"{prefix}_top_mid"]  = top_mid
        out[f"{prefix}_top_high"] = top_high
        out[f"{prefix}_bot_mid"]  = bot_mid
        out[f"{prefix}_bot_low"]  = bot_low
        out[f"{prefix}_trend"]    = get_midas_trend(top_high, bot_low, close)

    return out
