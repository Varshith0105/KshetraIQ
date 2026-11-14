"""KshetraIQ Farmer Profile Service.

Provides persistent, per-account farm profiles linked to user IDs in SQLite.
Ensures:
- Account isolation: users can only read and update their own profile.
- Strict state and district validation against official 28 states and 8 UTs.
- Automatic fallback defaults for new accounts.
- Preserves all database data across restarts.
"""

from __future__ import annotations

import datetime
import logging
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from app.data.india_locations import validate_state_and_district

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)


class FarmerProfileUpdateRequest(BaseModel):
    farm_name: str = Field(..., min_length=2, max_length=150)
    land_area_acres: float = Field(..., gt=0, le=50000, description="Holding area in acres")
    state: str = Field(..., description="Indian state or Union Territory")
    district: str = Field(..., description="Official district matching state")
    season: str = Field(default="Kharif", description="Kharif | Rabi | Zaid | Perennial")
    irrigation_method: str = Field(default="Drip", description="Drip | Sprinkler | Canal | Borewell | Flood | Rainfed")
    water_availability: str = Field(default="Borewell", description="Borewell | Canal | Rainfed | River | Pond | Tank")

    @field_validator("land_area_acres")
    @classmethod
    def validate_area(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Land area must be greater than 0 acres.")
        return round(v, 2)


class FarmerProfileResponse(BaseModel):
    user_id: str
    full_name: str
    email: str | None = None
    phone_number: str | None = None
    farm_name: str
    land_area_acres: float
    state: str
    district: str
    season: str
    irrigation_method: str
    water_availability: str
    updated_at: str


class ProfileService:
    """Manages per-user farm profile persistence."""

    def __init__(self, db_path: Path | None = None, settings: Settings | None = None) -> None:
        if settings is None:
            from app.core.config import get_settings
            self.settings = get_settings()
        else:
            self.settings = settings

        if db_path is None:
            self.db_path = self.settings.resolved_sqlite_db_path
        else:
            self.db_path = self.settings.resolve_db_path(db_path)

        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            logger.warning(
                "ProfileService could not create directory %s: %s. Falling back to writable temp directory.",
                self.db_path.parent,
                e,
            )
            fallback = self.settings.get_safe_fallback_dir()
            self.db_path = fallback / self.db_path.name
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS farmer_profiles (
                    user_id TEXT PRIMARY KEY,
                    farm_name TEXT NOT NULL,
                    land_area_acres REAL NOT NULL,
                    state TEXT NOT NULL,
                    district TEXT NOT NULL,
                    season TEXT NOT NULL,
                    irrigation_method TEXT NOT NULL,
                    water_availability TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
                """
            )
            conn.commit()

    def get_profile(self, user_id: str) -> FarmerProfileResponse:
        """Retrieve profile for a specific user. If no profile exists, return defaults based on user info."""
        with self._get_connection() as conn:
            # Get user info
            u_cur = conn.execute("SELECT id, full_name, email, phone_number FROM users WHERE id = ?", (user_id,))
            u_row = u_cur.fetchone()
            if not u_row:
                raise ValueError("User not found.")

            p_cur = conn.execute("SELECT * FROM farmer_profiles WHERE user_id = ?", (user_id,))
            p_row = p_cur.fetchone()

            full_name = u_row["full_name"]
            email = u_row["email"]
            display_email = None if email and email.endswith("@kshetraiq.local") else email
            phone_number = u_row["phone_number"]

            if p_row:
                return FarmerProfileResponse(
                    user_id=user_id,
                    full_name=full_name,
                    email=display_email,
                    phone_number=phone_number,
                    farm_name=p_row["farm_name"],
                    land_area_acres=float(p_row["land_area_acres"]),
                    state=p_row["state"],
                    district=p_row["district"],
                    season=p_row["season"],
                    irrigation_method=p_row["irrigation_method"],
                    water_availability=p_row["water_availability"],
                    updated_at=p_row["updated_at"],
                )

            # Default profile for initial setup
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            default_farm_name = f"{full_name}'s Farm"
            return FarmerProfileResponse(
                user_id=user_id,
                full_name=full_name,
                email=display_email,
                phone_number=phone_number,
                farm_name=default_farm_name,
                land_area_acres=2.5,
                state="Andhra Pradesh",
                district="Guntur",
                season="Kharif",
                irrigation_method="Drip",
                water_availability="Borewell",
                updated_at=now_iso,
            )

    def save_profile(self, user_id: str, req: FarmerProfileUpdateRequest) -> FarmerProfileResponse:
        """Validate and persist farmer profile."""
        valid, err = validate_state_and_district(req.state, req.district)
        if not valid:
            raise ValueError(err)

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO farmer_profiles (
                    user_id, farm_name, land_area_acres, state, district, season, irrigation_method, water_availability, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    farm_name = excluded.farm_name,
                    land_area_acres = excluded.land_area_acres,
                    state = excluded.state,
                    district = excluded.district,
                    season = excluded.season,
                    irrigation_method = excluded.irrigation_method,
                    water_availability = excluded.water_availability,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    req.farm_name.strip(),
                    req.land_area_acres,
                    req.state.strip(),
                    req.district.strip(),
                    req.season.strip(),
                    req.irrigation_method.strip(),
                    req.water_availability.strip(),
                    now_iso,
                ),
            )
            conn.commit()

        return self.get_profile(user_id)


profile_service = ProfileService()

