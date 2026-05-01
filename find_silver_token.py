"""
Find current MCX Silver contract tokens from Angel One scrip master.

Run from project root:
    python find_silver_token.py
"""

import json
import urllib.request

URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

print(f"Downloading scrip master from Angel One …")
with urllib.request.urlopen(URL, timeout=30) as resp:
    scrips = json.loads(resp.read().decode())

print(f"Total scrips: {len(scrips)}\n")

# Filter MCX Silver contracts
silver = [
    s for s in scrips
    if s.get("exch_seg") == "MCX"
    and "SILVER" in s.get("name", "").upper()
]

silver.sort(key=lambda s: s.get("expiry", ""))

print(f"{'Token':<12} {'Symbol':<30} {'Name':<20} {'Expiry':<12} {'LotSize'}")
print("-" * 90)
for s in silver:
    print(
        f"{s.get('token', ''):<12} "
        f"{s.get('symbol', ''):<30} "
        f"{s.get('name', ''):<20} "
        f"{s.get('expiry', ''):<12} "
        f"{s.get('lotsize', '')}"
    )
