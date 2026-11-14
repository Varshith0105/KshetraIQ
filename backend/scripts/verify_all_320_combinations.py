import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

from app.services.market_price_service import market_price_service, POPULAR_COMMODITIES, POPULAR_MANDIS

market_price_service._ensure_loaded()
errors = []
successes = 0

print(f"Testing all {len(POPULAR_COMMODITIES)} popular commodities against all {len(POPULAR_MANDIS)} popular mandis...")
for c in POPULAR_COMMODITIES:
    crop_name = c["name"]
    for m in POPULAR_MANDIS:
        mandi_name = m["name"]
        st = m["state"]
        dist = m["district"]
        try:
            fc = market_price_service.forecast_price(
                commodity=crop_name,
                mandi=mandi_name,
                days_ahead=7
            )
            price = fc["forecast_modal_price"]
            assert price > 0
            assert fc["confidence_band"]["lower_bound"] > 0
            assert fc["price_unit"] == "Rs./Quintal"
            assert fc["observation_date"] is not None
            assert fc["retrieved_at"] is not None
            assert isinstance(fc["is_stale"], bool)
            successes += 1
        except Exception as e:
            errors.append(f"{crop_name} @ {mandi_name}: {e}")

print(f"\nRESULTS:")
print(f"Total Combinations Tested: {len(POPULAR_COMMODITIES) * len(POPULAR_MANDIS)}")
print(f"Successful Inferences: {successes}")
print(f"Failed Inferences: {len(errors)}")
if errors:
    print("Sample errors:", errors[:5])
else:
    print("ALL 320 COMBINATIONS VERIFIED SUCCESSFULLY WITH 100% PASS RATE!")

