"""
KshetraIQ User Activity Service.

Maintains a lightweight, meaningful, and sanitized activity history for authenticated users.
Strictly prevents logging sensitive data (passwords, tokens, credentials).
Safely closes all SQLite connection handles to prevent database lock contention.
"""

from __future__ import annotations

import datetime
import json
import logging
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from app.core.config import Settings, get_settings
from app.schemas.chat import UserActivityResponse

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "password", "confirm_password", "token", "access_token", "refresh_token",
    "secret", "api_key", "authorization", "cookie", "otp", "dev_otp"
}


def sanitize_metadata(data: dict[str, Any] | None) -> dict[str, Any]:
    """Recursively redact sensitive keys from activity metadata."""
    if not data or not isinstance(data, dict):
        return {}
    clean: dict[str, Any] = {}
    for k, v in data.items():
        if k.lower() in SENSITIVE_KEYS or any(s in k.lower() for s in ["password", "token", "secret"]):
            continue
        if isinstance(v, dict):
            clean[k] = sanitize_metadata(v)
        elif isinstance(v, (str, int, float, bool)) or v is None:
            clean[k] = v
        elif isinstance(v, list):
            clean[k] = [
                sanitize_metadata(item) if isinstance(item, dict) else item
                for item in v[:20]
            ]
    return clean


class ActivityService:
    """Stores and retrieves user activity trails per authenticated farmer."""

    def __init__(self, settings: Settings | None = None, db_path: Path | None = None) -> None:
        self.settings = settings or get_settings()
        if db_path is not None:
            self.db_path = db_path
        else:
            self.db_path = self.settings.resolved_sqlite_db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_activities (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activities_user_time ON user_activities(user_id, created_at DESC)"
            )
            conn.commit()

    def log_activity(
        self,
        user_id: str,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UserActivityResponse:
        """Log a sanitized activity event for an authenticated user."""
        if not user_id:
            raise ValueError("user_id is required to record activity.")

        clean_meta = sanitize_metadata(metadata)
        act_id = f"act_{secrets.token_hex(8)}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO user_activities (id, user_id, action, entity_type, entity_id, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    act_id,
                    user_id,
                    action.strip(),
                    entity_type.strip() if entity_type else None,
                    entity_id.strip() if entity_id else None,
                    json.dumps(clean_meta),
                    now,
                ),
            )
            conn.commit()

        return UserActivityResponse(
            id=act_id,
            user_id=user_id,
            action=action.strip(),
            entity_type=entity_type.strip() if entity_type else None,
            entity_id=entity_id.strip() if entity_id else None,
            metadata=clean_meta,
            created_at=now,
        )

    def get_recent_activities(
        self,
        user_id: str,
        limit: int = 15,
    ) -> list[UserActivityResponse]:
        """Retrieve the most recent activities for an authenticated user."""
        if not user_id:
            return []

        with self._connection() as conn:
            cur = conn.execute(
                """
                SELECT id, user_id, action, entity_type, entity_id, metadata_json, created_at
                FROM user_activities
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, max(1, min(limit, 50))),
            )
            rows = cur.fetchall()

        results = []
        for r in rows:
            meta = {}
            if r["metadata_json"]:
                try:
                    meta = json.loads(r["metadata_json"])
                except Exception:
                    pass
            results.append(
                UserActivityResponse(
                    id=r["id"],
                    user_id=r["user_id"],
                    action=r["action"],
                    entity_type=r["entity_type"],
                    entity_id=r["entity_id"],
                    metadata=meta,
                    created_at=r["created_at"],
                )
            )
        return results


# Default global instance
activity_service = ActivityService()
