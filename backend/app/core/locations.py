"""Canonical farm locations supported across all 28 Indian States and 8 Union Territories."""

from __future__ import annotations

from app.data.india_locations import INDIA_STATES_AND_UT, validate_state_and_district

# Complete 28 States and 8 Union Territories with official districts
FARM_LOCATIONS: dict[str, frozenset[str]] = {
    state: frozenset(districts) for state, districts in INDIA_STATES_AND_UT.items()
}


def validate_farm_location(state: str, district: str) -> tuple[str, str]:
    """Validate that state exists and district belongs to the state, returning canonical names."""
    ok, err = validate_state_and_district(state, district)
    if not ok:
        raise ValueError(err)

    # Return canonical casing from authoritative dataset
    state_clean = state.strip().lower()
    district_clean = district.strip().lower()

    for s_name, d_list in INDIA_STATES_AND_UT.items():
        if s_name.lower() == state_clean:
            for d_name in d_list:
                if d_name.lower() == district_clean:
                    return s_name, d_name
            return s_name, district.strip()

    return state.strip(), district.strip()
