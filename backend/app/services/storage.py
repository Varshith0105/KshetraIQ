"""KshetraIQ Storage Service — Pluggable persistence layer supporting SQLite and in-memory fallbacks."""

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.assessment import AssessmentResponse

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract storage interface for KshetraIQ assessment records."""

    @abstractmethod
    def save(self, record: AssessmentResponse, user_id: str | None = None) -> None:
        """Persist an assessment record optionally associated with a user."""
        ...

    @abstractmethod
    def get(self, assessment_id: str, user_id: str | None = None) -> AssessmentResponse | None:
        """Retrieve an assessment by ID with optional user authorization."""
        ...

    @abstractmethod
    def list_all(self, user_id: str | None = None) -> list[AssessmentResponse]:
        """List all assessments, optionally filtered by user ID, newest first."""
        ...

    @abstractmethod
    def get_latest(self, user_id: str | None = None) -> AssessmentResponse | None:
        """Get the most recent assessment."""
        ...

    @property
    @abstractmethod
    def mode_name(self) -> str:
        """Human-readable storage mode descriptor."""
        ...


class InMemoryStorage(StorageBackend):
    """In-memory session storage (fallback when persistence is disabled)."""

    def __init__(self) -> None:
        self._records: dict[str, AssessmentResponse] = {}
        self._user_map: dict[str, str | None] = {}

    def save(self, record: AssessmentResponse, user_id: str | None = None) -> None:
        self._records[record.assessment_id] = record
        self._user_map[record.assessment_id] = user_id

    def get(self, assessment_id: str, user_id: str | None = None) -> AssessmentResponse | None:
        # Strict ownership: anonymous/unowned records are never readable back.
        rec = self._records.get(assessment_id)
        if rec is None or user_id is None or self._user_map.get(assessment_id) != user_id:
            return None
        return rec

    def list_all(self, user_id: str | None = None) -> list[AssessmentResponse]:
        if user_id is None:
            return []
        records = sorted(self._records.values(), key=lambda a: a.created_at, reverse=True)
        return [r for r in records if self._user_map.get(r.assessment_id) == user_id]

    def get_latest(self, user_id: str | None = None) -> AssessmentResponse | None:
        records = self.list_all(user_id)
        return records[0] if records else None

    @property
    def mode_name(self) -> str:
        return "in_memory"


class SQLiteStorage(StorageBackend):
    """Local SQLite database persistence ensuring records survive server restarts."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS assessments (
                    assessment_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    weather_source TEXT NOT NULL,
                    storage TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    user_id TEXT
                )
                """
            )
            # Add user_id column if table existed previously without it
            try:
                conn.execute("ALTER TABLE assessments ADD COLUMN user_id TEXT")
            except sqlite3.OperationalError:
                pass

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_assessments_created_at ON assessments(created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_assessments_user_id ON assessments(user_id)"
            )
            conn.commit()
        logger.info("Initialized SQLite storage at %s", self.db_path)

    def save(self, record: AssessmentResponse, user_id: str | None = None) -> None:
        payload_json = record.model_dump_json()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assessments (
                    assessment_id, created_at, weather_source, storage, payload_json, user_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.assessment_id,
                    record.created_at.isoformat(),
                    record.weather_source,
                    self.mode_name,
                    payload_json,
                    user_id,
                ),
            )
            conn.commit()

    def get(self, assessment_id: str, user_id: str | None = None) -> AssessmentResponse | None:
        # Strict ownership: only the owning user can read a record; unowned records are never returned.
        if user_id is None:
            return None
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM assessments WHERE assessment_id = ? AND user_id = ?",
                (assessment_id, user_id),
            ).fetchone()
        if not row:
            return None
        return AssessmentResponse.model_validate(json.loads(row["payload_json"]))

    def list_all(self, user_id: str | None = None) -> list[AssessmentResponse]:
        if user_id is None:
            return []
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM assessments WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        results = []
        for r in rows:
            try:
                results.append(AssessmentResponse.model_validate(json.loads(r["payload_json"])))
            except Exception as e:
                logger.warning("Failed to deserialize assessment row: %s", e)
        return results

    def get_latest(self, user_id: str | None = None) -> AssessmentResponse | None:
        records = self.list_all(user_id)
        return records[0] if records else None

    @property
    def mode_name(self) -> str:
        return "sqlite_local"

