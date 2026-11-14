"""
KshetraIQ Conversation Memory & Multi-Turn History Service.

Persists conversational sessions per authenticated user in SQLite.
Enforces strict user isolation so farmers can never see or cross-contaminate
each other's dialogue history or follow-up entities.
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
from app.schemas.chat import ChatMessageItem, ConversationSummary

logger = logging.getLogger(__name__)


class ConversationService:
    """Safely stores and retrieves multi-turn dialogue memory for users."""

    def __init__(self, settings: Settings | None = None, db_path: Path | None = None) -> None:
        self.settings = settings or get_settings()
        if db_path is not None:
            self.db_path = self.settings.resolve_db_path(db_path)
        else:
            self.db_path = self.settings.resolved_sqlite_db_path
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            logger.warning(
                "ConversationService could not create directory %s: %s. Falling back to writable temp directory.",
                self.db_path.parent,
                e,
            )
            fallback = self.settings.get_safe_fallback_dir()
            self.db_path = fallback / self.db_path.name
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
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    screen_id TEXT,
                    language TEXT DEFAULT 'en',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_user_updated ON conversations(user_id, updated_at DESC)"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    message_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    message TEXT NOT NULL,
                    screen_id TEXT,
                    observed TEXT,
                    analysis TEXT,
                    recommendation TEXT,
                    next_actions_json TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conv_messages_lookup ON conversation_messages(conversation_id, created_at ASC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conv_messages_user ON conversation_messages(user_id)"
            )
            conn.commit()

    def get_or_create_conversation(
        self,
        conversation_id: str | None,
        user_id: str,
        initial_title: str = "Farm Advisory Session",
        screen_id: str | None = None,
        language: str = "en",
    ) -> str:
        """Get an existing conversation if owned by the user, or create a fresh one."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with self._connection() as conn:
            if conversation_id:
                cur = conn.execute(
                    "SELECT conversation_id, user_id FROM conversations WHERE conversation_id = ?",
                    (conversation_id,),
                )
                row = cur.fetchone()
                if row:
                    if row["user_id"] == user_id:
                        conn.execute(
                            "UPDATE conversations SET updated_at = ?, screen_id = COALESCE(?, screen_id) WHERE conversation_id = ?",
                            (now, screen_id, conversation_id),
                        )
                        conn.commit()
                        return conversation_id
                    else:
                        logger.warning(
                            "User %s attempted to access conversation %s owned by %s. Isolating.",
                            user_id, conversation_id, row["user_id"]
                        )

            new_id = f"conv_{secrets.token_hex(10)}"
            clean_title = (initial_title[:50] + "...") if len(initial_title) > 50 else initial_title
            conn.execute(
                """
                INSERT INTO conversations (conversation_id, user_id, title, screen_id, language, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id, user_id, clean_title, screen_id, language, now, now),
            )
            conn.commit()
            return new_id

    def add_message(
        self,
        conversation_id: str,
        user_id: str,
        sender: str,
        message: str,
        screen_id: str | None = None,
        observed: str | None = None,
        analysis: str | None = None,
        recommendation: str | None = None,
        next_actions: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessageItem:
        """Append a message to the verified user's conversation."""
        msg_id = f"msg_{secrets.token_hex(8)}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        actions_json = json.dumps(next_actions or [])
        meta_json = json.dumps(metadata or {})

        with self._connection() as conn:
            cur = conn.execute(
                "SELECT user_id FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            row = cur.fetchone()
            if not row or row["user_id"] != user_id:
                raise PermissionError("Access denied: conversation does not belong to this user.")

            conn.execute(
                """
                INSERT INTO conversation_messages (
                    message_id, conversation_id, user_id, sender, message, screen_id,
                    observed, analysis, recommendation, next_actions_json, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg_id, conversation_id, user_id, sender, message, screen_id,
                    observed, analysis, recommendation, actions_json, meta_json, now,
                ),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
                (now, conversation_id),
            )
            conn.commit()

        return ChatMessageItem(
            message_id=msg_id,
            conversation_id=conversation_id,
            sender=sender,
            message=message,
            screen_id=screen_id,
            observed=observed,
            analysis=analysis,
            recommendation=recommendation,
            next_actions=next_actions or [],
            created_at=now,
        )

    def get_messages(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 20,
    ) -> list[ChatMessageItem]:
        """Fetch chronological messages for a conversation, enforcing ownership."""
        with self._connection() as conn:
            cur = conn.execute(
                "SELECT user_id FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            row = cur.fetchone()
            if not row or row["user_id"] != user_id:
                return []

            cur = conn.execute(
                """
                SELECT message_id, conversation_id, sender, message, screen_id,
                       observed, analysis, recommendation, next_actions_json, created_at
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (conversation_id, max(1, min(limit, 100))),
            )
            rows = cur.fetchall()

        messages = []
        for r in rows:
            actions = []
            if r["next_actions_json"]:
                try:
                    actions = json.loads(r["next_actions_json"])
                except Exception:
                    pass
            messages.append(
                ChatMessageItem(
                    message_id=r["message_id"],
                    conversation_id=r["conversation_id"],
                    sender=r["sender"],
                    message=r["message"],
                    screen_id=r["screen_id"],
                    observed=r["observed"],
                    analysis=r["analysis"],
                    recommendation=r["recommendation"],
                    next_actions=actions,
                    created_at=r["created_at"],
                )
            )
        return messages

    def list_conversations(
        self,
        user_id: str,
        limit: int = 15,
    ) -> list[ConversationSummary]:
        """List past conversations for an authenticated user."""
        if not user_id:
            return []

        with self._connection() as conn:
            cur = conn.execute(
                """
                SELECT c.conversation_id, c.title, c.screen_id, c.language, c.created_at, c.updated_at,
                       COUNT(m.message_id) AS message_count
                FROM conversations c
                LEFT JOIN conversation_messages m ON c.conversation_id = m.conversation_id
                WHERE c.user_id = ?
                GROUP BY c.conversation_id
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (user_id, max(1, min(limit, 50))),
            )
            rows = cur.fetchall()

        return [
            ConversationSummary(
                conversation_id=r["conversation_id"],
                title=r["title"],
                screen_id=r["screen_id"],
                language=r["language"] or "en",
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                message_count=r["message_count"],
            )
            for r in rows
        ]

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Safely delete a conversation owned by the authenticated user."""
        with self._connection() as conn:
            cur = conn.execute(
                "SELECT user_id FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            row = cur.fetchone()
            if not row or row["user_id"] != user_id:
                return False

            conn.execute("DELETE FROM conversation_messages WHERE conversation_id = ?", (conversation_id,))
            conn.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
            conn.commit()
            return True


# Default global instance
conversation_service = ConversationService()
