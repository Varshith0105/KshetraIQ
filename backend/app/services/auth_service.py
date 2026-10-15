"""KshetraIQ Authentication & Session Management Service.

Provides secure user registration, PBKDF2-HMAC-SHA256 password hashing with unique salts,
session token issuance, and cross-user authorization enforcement.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import os
import re
import secrets
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    full_name: str | None = Field(default=None, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    confirm_password: str | None = Field(default=None, min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format.")
        return clean


class UserLoginRequest(BaseModel):
    email: str = Field(...)
    password: str = Field(...)


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    created_at: str


class AuthTokenResponse(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_at: str
    user: UserProfileResponse
    user_id: str | None = None
    email: str | None = None
    display_name: str | None = None


class AuthService:
    """Manages user persistence, credential verification, and session tokens."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            backend_tmp = Path(__file__).resolve().parents[2] / ".tmp" / "kshetraiq.db"
            root_tmp = Path(__file__).resolve().parents[3] / ".tmp" / "kshetraiq.db"
            self.db_path = backend_tmp if backend_tmp.exists() else root_tmp
        else:
            self.db_path = db_path

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
                """
            )
            # Ensure assessments table has user_id column
            try:
                conn.execute("ALTER TABLE assessments ADD COLUMN user_id TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

            conn.commit()

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return dk.hex()

    def register(self, req: UserRegisterRequest) -> AuthTokenResponse:
        """Register a new farmer account with secure password hashing."""
        effective_name = (req.full_name or req.display_name or req.email.split("@")[0]).strip()
        effective_confirm = req.confirm_password or req.password
        if req.password != effective_confirm:
            raise ValueError("Password confirmation does not match.")

        email_clean = req.email.lower().strip()
        user_id = f"user_{secrets.token_hex(8)}"
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(req.password, salt)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with self._get_connection() as conn:
            # Check existing email
            cursor = conn.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
            if cursor.fetchone():
                raise ValueError("An account with this email address already exists.")

            conn.execute(
                """
                INSERT INTO users (id, email, full_name, password_hash, salt, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, email_clean, effective_name, password_hash, salt.hex(), now),
            )
            conn.commit()

        return self._create_session(user_id, email_clean, effective_name, now)

    def login(self, req: UserLoginRequest) -> AuthTokenResponse:
        """Authenticate user credentials and issue a session bearer token."""
        email_clean = req.email.lower().strip()

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, email, full_name, password_hash, salt, created_at FROM users WHERE email = ?",
                (email_clean,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("Invalid email or password.")

            salt = bytes.fromhex(row["salt"])
            computed_hash = self._hash_password(req.password, salt)
            if not secrets.compare_digest(computed_hash, row["password_hash"]):
                raise ValueError("Invalid email or password.")

            user_id = row["id"]
            full_name = row["full_name"]
            created_at = row["created_at"]

        return self._create_session(user_id, email_clean, full_name, created_at)

    def _create_session(self, user_id: str, email: str, full_name: str, created_at: str) -> AuthTokenResponse:
        token = secrets.token_urlsafe(32)
        now = datetime.datetime.now(datetime.timezone.utc)
        expires = now + datetime.timedelta(days=7)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (token, user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (token, user_id, now.isoformat(), expires.isoformat()),
            )
            conn.commit()

        user_profile = UserProfileResponse(
            user_id=user_id,
            email=email,
            full_name=full_name,
            created_at=created_at,
        )
        return AuthTokenResponse(
            token=token,
            expires_at=expires.isoformat(),
            user=user_profile,
            user_id=user_id,
            email=email,
            display_name=full_name,
        )

    def get_user_by_token(self, token: str) -> UserProfileResponse | None:
        """Validate bearer token and retrieve active user session."""
        if not token:
            return None

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT u.id, u.email, u.full_name, u.created_at, s.expires_at
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ?
                """,
                (token,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            if row["expires_at"] < now:
                # Expired session
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                return None

            return UserProfileResponse(
                user_id=row["id"],
                email=row["email"],
                full_name=row["full_name"],
                created_at=row["created_at"],
            )

    def logout(self, token: str) -> bool:
        """Invalidate active session token."""
        if not token:
            return False
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return cursor.rowcount > 0


auth_service = AuthService()
