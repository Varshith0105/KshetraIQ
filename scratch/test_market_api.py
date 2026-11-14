import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.market_price_service import market_price_service

cat = market_price_service.get_market_catalog()
print("Popular commodities count:", len(cat["popular_commodities"]))
print("Verified pairs count:", len(cat["verified_pairs"]))
for p in cat["verified_pairs"][:5]:
    print("  Pair:", p)
