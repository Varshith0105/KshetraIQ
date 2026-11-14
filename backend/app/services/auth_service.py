"""KshetraIQ Authentication & Session Management Service.

Provides secure multi-method authentication:
1. Email/Password with PBKDF2-HMAC-SHA256 password hashing (100,000 iterations) and unique salts.
2. Phone OTP with India (+91) normalization, 60s cooldown rate-limiting, PBKDF2 hashed OTPs, and 3-attempt lockouts.
3. Google OAuth 2.0 authorization URL generation, single-use state verification, and token exchange callback.
4. Session token issuance, dual cookie/bearer resolution, Remember Me persistent session controls, and cross-user data isolation.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import os
import re
import secrets
import sqlite3
import smtplib
import urllib.parse
from email.message import EmailMessage
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.locations import validate_farm_location

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    full_name: str | None = Field(default=None, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, description="Optional phone number")
    password: str = Field(..., min_length=6, max_length=128)
    confirm_password: str | None = Field(default=None, min_length=6, max_length=128)
    remember_me: bool = Field(default=False, description="Whether to issue a persistent session")

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
    remember_me: bool = Field(default=False, description="Whether to issue a persistent session (e.g. 30 days)")


class PhoneOtpSendRequest(BaseModel):
    phone_number: str = Field(..., description="10-digit Indian phone number or formatted E.164 (+91...)")


class PhoneOtpSendResponse(BaseModel):
    status: str = "success"
    phone_number: str
    message: str
    dev_otp: str | None = None
    expires_in_seconds: int = 600
    provider_configured: bool = True


class PhoneOtpVerifyRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number matching previous send request")
    otp: str = Field(..., min_length=4, max_length=10, description="One-Time Password")
    full_name: str | None = Field(default=None, max_length=100)
    remember_me: bool = Field(default=False, description="Whether to issue a persistent session")


class GoogleAuthUrlResponse(BaseModel):
    configured: bool
    url: str
    state: str | None = None
    message: str | None = None


class GoogleAuthCallbackRequest(BaseModel):
    code: str
    redirect_uri: str | None = None
    state: str | None = None
    remember_me: bool = False


class PasswordResetRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format.")
        return clean


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequestResponse(BaseModel):
    message: str


class FarmProfilePayload(BaseModel):
    farm_name: str = Field(..., min_length=1, max_length=120)
    district: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    acreage: float = Field(..., gt=0, le=100000)
    season: str = Field(..., min_length=1, max_length=50)
    irrigation_method: str = Field(..., min_length=1, max_length=80)
    water_availability: str = Field(..., min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_location(self) -> "FarmProfilePayload":
        self.state, self.district = validate_farm_location(self.state, self.district)
        return self


class FarmProfileResponse(FarmProfilePayload):
    user_id: str
    updated_at: str


class UserProfileResponse(BaseModel):
    user_id: str
    email: str | None = None
    phone_number: str | None = None
    full_name: str
    auth_provider: str = "email"
    avatar_url: str | None = None
    created_at: str


class AuthTokenResponse(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_at: str
    user: UserProfileResponse
    user_id: str | None = None
    email: str | None = None
    display_name: str | None = None
    remember_me: bool = False


class AuthService:
    """Manages user persistence, credential verification, and session tokens."""

    def __init__(self, db_path: Path | None = None, settings: Settings | None = None) -> None:
        if settings is None:
            from app.core.config import get_settings
            self.settings = get_settings()
        else:
            self.settings = settings

        if db_path is None:
            self.db_path = self.settings.resolved_sqlite_db_path
        else:
            self.db_path = db_path

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        """Safe, idempotent migration for SQLite database preserving all existing data."""
        with self._get_connection() as conn:
            # 1. Users table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE,
                    phone_number TEXT,
                    full_name TEXT NOT NULL,
                    password_hash TEXT,
                    salt TEXT,
                    auth_provider TEXT NOT NULL DEFAULT 'email',
                    provider_id TEXT,
                    avatar_url TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            # Inspect existing columns in users table
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(users)")
            existing_cols = {row[1] for row in cur.fetchall()}

            # Add missing columns safely without invalid ALTER TABLE constraints
            if "phone_number" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")
            if "auth_provider" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'email'")
            if "provider_id" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN provider_id TEXT")
            if "avatar_url" not in existing_cols:
                conn.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")

            # Unique index on normalized phone_number (ignoring NULLs)
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_number ON users(phone_number) WHERE phone_number IS NOT NULL"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_provider_id ON users(provider_id) WHERE provider_id IS NOT NULL"
            )

            # 2. Sessions table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    remember_me INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
                """
            )
            cur.execute("PRAGMA table_info(sessions)")
            session_cols = {row[1] for row in cur.fetchall()}
            if "remember_me" not in session_cols:
                conn.execute("ALTER TABLE sessions ADD COLUMN remember_me INTEGER DEFAULT 0")

            # 3. Phone OTPs table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS phone_otps (
                    phone_number TEXT PRIMARY KEY,
                    otp_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )

            # 4. OAuth CSRF single-use state table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state TEXT PRIMARY KEY,
                    redirect_uri TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )

            # 5. Password reset tokens are stored only as hashes.  A successful
            # reset consumes the token and revokes every active user session.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id)"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS farm_profiles (
                    user_id TEXT PRIMARY KEY,
                    farm_name TEXT NOT NULL,
                    district TEXT NOT NULL,
                    state TEXT NOT NULL,
                    acreage REAL NOT NULL,
                    season TEXT NOT NULL,
                    irrigation_method TEXT NOT NULL,
                    water_availability TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )

            # 6. Assessments table user_id column
            try:
                cur.execute("PRAGMA table_info(assessments)")
                assessment_cols = {row[1] for row in cur.fetchall()}
                if assessment_cols and "user_id" not in assessment_cols:
                    conn.execute("ALTER TABLE assessments ADD COLUMN user_id TEXT")
            except Exception:
                pass

            conn.commit()

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        """Hash password or OTP using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return dk.hex()

    @staticmethod
    def normalize_phone(phone_raw: str) -> str:
        """Normalize Indian phone numbers to canonical E.164 (+91XXXXXXXXXX)."""
        if not phone_raw or not isinstance(phone_raw, str):
            raise ValueError("Phone number is required.")
        clean = re.sub(r"[\s\-\(\)]", "", phone_raw.strip())
        if clean.startswith("+91"):
            digits = clean[3:]
        elif clean.startswith("91") and len(clean) == 12:
            digits = clean[2:]
        elif clean.startswith("0") and len(clean) == 11:
            digits = clean[1:]
        else:
            digits = clean

        if not (len(digits) == 10 and digits.isdigit()):
            raise ValueError(f"Invalid phone number '{phone_raw}'. Must be a 10-digit Indian mobile number.")
        return f"+91{digits}"

    def register(self, req: UserRegisterRequest) -> AuthTokenResponse:
        """Register a new farmer account with secure password hashing."""
        effective_name = (req.full_name or req.display_name or req.email.split("@")[0]).strip()
        effective_confirm = req.confirm_password or req.password
        if req.password != effective_confirm:
            raise ValueError("Password confirmation does not match.")

        email_clean = req.email.lower().strip()
        normalized_phone: str | None = None
        if req.phone_number:
            normalized_phone = self.normalize_phone(req.phone_number)

        user_id = f"user_{secrets.token_hex(8)}"
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(req.password, salt)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with self._get_connection() as conn:
            # Check existing email
            cursor = conn.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
            if cursor.fetchone():
                raise ValueError("An account with this email address already exists.")

            if normalized_phone:
                p_cursor = conn.execute("SELECT id FROM users WHERE phone_number = ?", (normalized_phone,))
                if p_cursor.fetchone():
                    raise ValueError("An account with this phone number already exists.")

            conn.execute(
                """
                INSERT INTO users (id, email, phone_number, full_name, password_hash, salt, auth_provider, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'email', ?)
                """,
                (user_id, email_clean, normalized_phone, effective_name, password_hash, salt.hex(), now),
            )
            conn.commit()

        return self._create_session(
            user_id=user_id,
            email=email_clean,
            full_name=effective_name,
            created_at=now,
            phone_number=normalized_phone,
            auth_provider="email",
            remember_me=req.remember_me,
        )

    def login(self, req: UserLoginRequest) -> AuthTokenResponse:
        """Authenticate user credentials and issue a session bearer token."""
        email_clean = req.email.lower().strip()

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, email, phone_number, full_name, password_hash, salt, auth_provider, avatar_url, created_at 
                FROM users WHERE email = ?
                """,
                (email_clean,),
            )
            row = cursor.fetchone()
            if (
                not row
                or not row["password_hash"]
                or not row["salt"]
                or row["password_hash"].startswith("!")
            ):
                raise ValueError("Invalid email or password.")

            try:
                salt = bytes.fromhex(row["salt"])
                computed_hash = self._hash_password(req.password, salt)
            except Exception:
                raise ValueError("Invalid email or password.")

            if not secrets.compare_digest(computed_hash, row["password_hash"]):
                raise ValueError("Invalid email or password.")

            user_id = row["id"]
            full_name = row["full_name"]
            phone_number = row["phone_number"]
            auth_provider = row["auth_provider"] or "email"
            avatar_url = row["avatar_url"]
            created_at = row["created_at"]

        return self._create_session(
            user_id=user_id,
            email=email_clean,
            full_name=full_name,
            created_at=created_at,
            phone_number=phone_number,
            auth_provider=auth_provider,
            avatar_url=avatar_url,
            remember_me=req.remember_me,
        )

    def send_phone_otp(self, req: PhoneOtpSendRequest) -> PhoneOtpSendResponse:
        """Generate cryptographically secure 6-digit OTP with 60-second cooldown."""
        normalized_phone = self.normalize_phone(req.phone_number)
        now = datetime.datetime.now(datetime.timezone.utc)
        now_iso = now.isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT created_at, expires_at FROM phone_otps WHERE phone_number = ?",
                (normalized_phone,),
            )
            existing = cursor.fetchone()
            if existing:
                try:
                    last_created = datetime.datetime.fromisoformat(existing["created_at"])
                    elapsed_seconds = (now - last_created).total_seconds()
                    if elapsed_seconds < 60:
                        wait_seconds = int(60 - elapsed_seconds)
                        raise ValueError(f"Please wait {wait_seconds} seconds before requesting a new OTP.")
                except (ValueError, TypeError) as err:
                    if "Please wait" in str(err):
                        raise

            # Cryptographically secure 6-digit OTP: 100000 - 999999
            otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
            salt = secrets.token_bytes(16)
            otp_hash = self._hash_password(otp_code, salt)
            # 10 minutes expiry
            expires_at = (now + datetime.timedelta(minutes=10)).isoformat()

            conn.execute(
                """
                INSERT INTO phone_otps (phone_number, otp_hash, salt, attempts, created_at, expires_at)
                VALUES (?, ?, ?, 0, ?, ?)
                ON CONFLICT(phone_number) DO UPDATE SET
                    otp_hash = excluded.otp_hash,
                    salt = excluded.salt,
                    attempts = 0,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                """,
                (normalized_phone, otp_hash, salt.hex(), now_iso, expires_at),
            )
            conn.commit()

        # In dev or test environment with console provider, surface dev_otp for developer testing
        is_dev = (
            self.settings.environment in ("development", "test")
            and getattr(self.settings, "sms_provider", "console") == "console"
        )
        if is_dev:
            logger.info("DEVELOPMENT OTP for %s: %s", normalized_phone, otp_code)

        return PhoneOtpSendResponse(
            status="success",
            phone_number=normalized_phone,
            message="OTP dispatched successfully to your registered mobile number.",
            dev_otp=otp_code if is_dev else None,
            expires_in_seconds=600,
            provider_configured=True,
        )

    def verify_phone_otp(self, req: PhoneOtpVerifyRequest) -> AuthTokenResponse:
        """Validate phone OTP and establish farmer session."""
        normalized_phone = self.normalize_phone(req.phone_number)
        clean_otp = req.otp.strip()
        now = datetime.datetime.now(datetime.timezone.utc)
        now_iso = now.isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT otp_hash, salt, attempts, expires_at FROM phone_otps WHERE phone_number = ?",
                (normalized_phone,),
            )
            record = cursor.fetchone()
            if not record:
                raise ValueError("No OTP request found for this phone number. Please request a new OTP.")

            if record["expires_at"] < now_iso:
                conn.execute("DELETE FROM phone_otps WHERE phone_number = ?", (normalized_phone,))
                conn.commit()
                raise ValueError("Your verification code has expired. Request a new code.")

            if record["attempts"] >= 3:
                conn.execute("DELETE FROM phone_otps WHERE phone_number = ?", (normalized_phone,))
                conn.commit()
                raise ValueError("Maximum OTP verification attempts exceeded. Please request a new OTP.")

            salt = bytes.fromhex(record["salt"])
            computed_hash = self._hash_password(clean_otp, salt)

            if not secrets.compare_digest(computed_hash, record["otp_hash"]):
                conn.execute(
                    "UPDATE phone_otps SET attempts = attempts + 1 WHERE phone_number = ?",
                    (normalized_phone,),
                )
                conn.commit()
                remaining = 2 - record["attempts"]
                if remaining > 0:
                    raise ValueError(f"Invalid verification code. {remaining} attempt(s) remaining.")
                raise ValueError("Invalid verification code. Maximum attempts reached. Please request a new code.")

            # OTP Validated - consume OTP token
            conn.execute("DELETE FROM phone_otps WHERE phone_number = ?", (normalized_phone,))

            # Find or create user
            u_cursor = conn.execute(
                "SELECT id, email, phone_number, full_name, auth_provider, avatar_url, created_at FROM users WHERE phone_number = ?",
                (normalized_phone,),
            )
            user_row = u_cursor.fetchone()

            if user_row:
                user_id = user_row["id"]
                full_name = user_row["full_name"]
                email = user_row["email"]
                avatar_url = user_row["avatar_url"]
                created_at = user_row["created_at"]
            else:
                user_id = f"user_{secrets.token_hex(8)}"
                full_name = req.full_name.strip() if req.full_name else f"Kisan {normalized_phone[-4:]}"
                email = f"farmer_{normalized_phone.replace('+', '')}@kshetraiq.local"
                avatar_url = None
                created_at = now_iso
                conn.execute(
                    """
                    INSERT INTO users (id, email, phone_number, full_name, password_hash, salt, auth_provider, created_at)
                    VALUES (?, ?, ?, ?, '!AUTH_PHONE_NO_PASSWORD', '', 'phone', ?)
                    """,
                    (user_id, email, normalized_phone, full_name, created_at),
                )

            conn.commit()

        display_email = None if email and email.endswith("@kshetraiq.local") else email

        return self._create_session(
            user_id=user_id,
            email=display_email or "",
            full_name=full_name,
            created_at=created_at,
            phone_number=normalized_phone,
            auth_provider="phone",
            avatar_url=avatar_url,
            remember_me=req.remember_me,
        )

    def get_google_auth_url(self, redirect_uri: str | None = None) -> GoogleAuthUrlResponse:
        """Construct Google OAuth2 authorization URL with secure single-use CSRF state."""
        if not self.settings.has_google_oauth:
            return GoogleAuthUrlResponse(
                configured=False,
                url="",
                state=None,
                message="Google OAuth is not configured on this server. Please provide GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend configuration.",
            )

        # Allow matching either 127.0.0.1 or localhost local development callback URIs
        allowed_redirects = {
            self.settings.google_redirect_uri.strip(),
            "http://127.0.0.1:3000/auth/callback",
            "http://localhost:3000/auth/callback",
        }
        if redirect_uri and redirect_uri.strip() in allowed_redirects:
            target_redirect = redirect_uri.strip()
        else:
            target_redirect = self.settings.google_redirect_uri
        state = secrets.token_urlsafe(32)
        now = datetime.datetime.now(datetime.timezone.utc)
        expires = now + datetime.timedelta(minutes=10)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO oauth_states (state, redirect_uri, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (state, target_redirect, now.isoformat(), expires.isoformat()),
            )
            conn.commit()

        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": target_redirect,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
        encoded_params = urllib.parse.urlencode(params)
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{encoded_params}"
        return GoogleAuthUrlResponse(configured=True, url=auth_url, state=state)

    def authenticate_with_google(
        self,
        code: str,
        redirect_uri: str | None = None,
        state: str | None = None,
        remember_me: bool = False,
    ) -> AuthTokenResponse:
        """Exchange Google authorization code for identity tokens and user profile."""
        if not self.settings.has_google_oauth:
            raise ValueError("Google OAuth credentials are not configured on this server.")

        now = datetime.datetime.now(datetime.timezone.utc)
        now_iso = now.isoformat()

        # State is mandatory: accepting a callback without it defeats CSRF protection.
        if not state:
            raise ValueError("Google Sign-In session is missing or expired. Please try again.")

        # Validate the redirect URI saved with the one-time state.
        target_redirect = redirect_uri or self.settings.google_redirect_uri
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT redirect_uri, expires_at FROM oauth_states WHERE state = ?", (state,))
            state_row = cursor.fetchone()
            if not state_row:
                raise ValueError("Google Sign-In failed: Invalid or expired OAuth state parameter. Please try again.")
            if state_row["expires_at"] < now_iso:
                conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
                conn.commit()
                raise ValueError("Google Sign-In session expired. Please try again.")
            # Consume before code exchange, so a code/state pair cannot be replayed.
            conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
            conn.commit()
            # Always use the redirect URI that was stored with the state token at
            # authorization time. This ensures authorization and token exchange always
            # use the same URI regardless of which origin the browser callback fires from.
            if state_row["redirect_uri"]:
                target_redirect = state_row["redirect_uri"]

        # 1. Exchange authorization code for access token
        with httpx.Client(timeout=10.0) as client:
            token_resp = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": target_redirect,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                logger.error("Google token exchange failed: %s", token_resp.text)
                raise ValueError("Failed to authenticate with Google. Invalid or expired authorization code.")

            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("Google OAuth response missing access token.")

            # 2. Fetch user profile
            profile_resp = client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if profile_resp.status_code != 200:
                raise ValueError("Failed to retrieve user profile from Google.")

            profile_data = profile_resp.json()

        google_id = str(profile_data.get("id") or profile_data.get("sub") or "")
        email = profile_data.get("email")
        full_name = profile_data.get("name") or "Google User"
        avatar_url = profile_data.get("picture")

        if not google_id or not email:
            raise ValueError("Google user profile did not include a verified identity.")
        is_verified = (profile_data.get("verified_email") is True) or (profile_data.get("email_verified") is True)
        if not is_verified:
            raise ValueError("Google did not verify this email address. Please use a verified Google account.")

        email_clean = email.lower().strip()

        with self._get_connection() as conn:
            # Check by Google provider ID first
            cursor = conn.execute(
                "SELECT id, email, phone_number, full_name, auth_provider, avatar_url, created_at FROM users WHERE provider_id = ?",
                (google_id,),
            )
            existing_user = cursor.fetchone()

            if existing_user:
                user_id = existing_user["id"]
                full_name = existing_user["full_name"] or full_name
                phone_number = existing_user["phone_number"]
                created_at = existing_user["created_at"]
                conn.execute(
                    "UPDATE users SET provider_id = ?, avatar_url = COALESCE(avatar_url, ?) WHERE id = ?",
                    (google_id, avatar_url, user_id),
                )
            else:
                # Safe account linking: if an account exists with the exact verified email,
                # attach provider_id without overwriting existing password or farm data.
                email_owner = conn.execute(
                    "SELECT id, full_name, phone_number, created_at FROM users WHERE email = ?",
                    (email_clean,),
                ).fetchone()
                if email_owner:
                    user_id = email_owner["id"]
                    full_name = email_owner["full_name"] or full_name
                    phone_number = email_owner["phone_number"]
                    created_at = email_owner["created_at"]
                    conn.execute(
                        "UPDATE users SET provider_id = ?, avatar_url = COALESCE(avatar_url, ?) WHERE id = ?",
                        (google_id, avatar_url, user_id),
                    )
                else:
                    user_id = f"user_{secrets.token_hex(8)}"
                    phone_number = None
                    created_at = now_iso
                    conn.execute(
                        """
                        INSERT INTO users (id, email, phone_number, full_name, password_hash, salt, auth_provider, provider_id, avatar_url, created_at)
                        VALUES (?, ?, NULL, ?, '!AUTH_GOOGLE_OAUTH', '', 'google', ?, ?, ?)
                        """,
                        (user_id, email_clean, full_name, google_id, avatar_url, created_at),
                    )
            conn.commit()

        return self._create_session(
            user_id=user_id,
            email=email_clean,
            full_name=full_name,
            created_at=created_at,
            phone_number=phone_number,
            auth_provider="google",
            avatar_url=avatar_url,
            remember_me=remember_me,
        )

    @staticmethod
    def _hash_reset_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def request_password_reset(self, req: PasswordResetRequest, frontend_base_url: str) -> None:
        """Create a short-lived, one-time token and deliver it only through configured email."""
        with self._get_connection() as conn:
            user = conn.execute(
                "SELECT id, email FROM users WHERE email = ? AND password_hash IS NOT NULL AND password_hash NOT LIKE '!%'",
                (req.email,),
            ).fetchone()
            if not user:
                return
            raw_token = secrets.token_urlsafe(32)
            now = datetime.datetime.now(datetime.timezone.utc)
            expires = now + datetime.timedelta(minutes=self.settings.password_reset_expiry_minutes)
            conn.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (user["id"],))
            conn.execute(
                "INSERT INTO password_reset_tokens (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (self._hash_reset_token(raw_token), user["id"], now.isoformat(), expires.isoformat()),
            )
            conn.commit()

        reset_url = f"{frontend_base_url.rstrip('/')}/reset-password?token={urllib.parse.quote(raw_token)}"
        if self.settings.has_email_delivery:
            message = EmailMessage()
            message["Subject"] = "Reset your KshetraIQ password"
            message["From"] = self.settings.email_from
            message["To"] = user["email"]
            message.set_content(
                f"Use this one-time KshetraIQ password-reset link within {self.settings.password_reset_expiry_minutes} minutes:\n{reset_url}"
            )
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as server:
                server.starttls()
                if self.settings.smtp_username and self.settings.smtp_password:
                    server.login(self.settings.smtp_username, self.settings.smtp_password)
                server.send_message(message)
        elif self.settings.environment == "development" and self.settings.email_provider.lower() == "console":
            # Intentional development-only delivery channel; API response stays generic.
            logger.info("Development password reset link for %s: %s", user["email"], reset_url)
        else:
            logger.warning("Password reset requested but no email provider is configured")

    def reset_password(self, req: PasswordResetConfirmRequest) -> None:
        if req.password != req.confirm_password:
            raise ValueError("Password confirmation does not match.")
        token_hash = self._hash_reset_token(req.token)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            token = conn.execute(
                "SELECT user_id, expires_at, used_at FROM password_reset_tokens WHERE token_hash = ?", (token_hash,)
            ).fetchone()
            if not token or token["used_at"] or token["expires_at"] < now:
                raise ValueError("This password-reset link is invalid or has expired.")
            salt = secrets.token_bytes(16)
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ?, auth_provider = 'email' WHERE id = ?",
                (self._hash_password(req.password, salt), salt.hex(), token["user_id"]),
            )
            conn.execute("UPDATE password_reset_tokens SET used_at = ? WHERE token_hash = ?", (now, token_hash))
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (token["user_id"],))
            conn.commit()

    def get_farm_profile(self, user_id: str) -> FarmProfileResponse | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM farm_profiles WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return None
        return FarmProfileResponse(**dict(row))

    def save_farm_profile(self, user_id: str, payload: FarmProfilePayload) -> FarmProfileResponse:
        updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO farm_profiles (user_id, farm_name, district, state, acreage, season, irrigation_method, water_availability, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                  farm_name=excluded.farm_name, district=excluded.district, state=excluded.state,
                  acreage=excluded.acreage, season=excluded.season, irrigation_method=excluded.irrigation_method,
                  water_availability=excluded.water_availability, updated_at=excluded.updated_at
                """,
                (user_id, payload.farm_name.strip(), payload.district.strip(), payload.state.strip(), payload.acreage,
                 payload.season.strip(), payload.irrigation_method.strip(), payload.water_availability.strip(), updated_at),
            )
            conn.commit()
        return FarmProfileResponse(user_id=user_id, updated_at=updated_at, **payload.model_dump())

    def _create_session(
        self,
        user_id: str,
        email: str,
        full_name: str,
        created_at: str,
        phone_number: str | None = None,
        auth_provider: str = "email",
        avatar_url: str | None = None,
        remember_me: bool = False,
    ) -> AuthTokenResponse:
        token = secrets.token_urlsafe(32)
        now = datetime.datetime.now(datetime.timezone.utc)
        if remember_me:
            days = getattr(self.settings, "persistent_session_days", 30)
            expires = now + datetime.timedelta(days=days)
        else:
            hours = getattr(self.settings, "session_expiry_hours", 24)
            expires = now + datetime.timedelta(hours=hours)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (token, user_id, created_at, expires_at, remember_me)
                VALUES (?, ?, ?, ?, ?)
                """,
                (token, user_id, now.isoformat(), expires.isoformat(), 1 if remember_me else 0),
            )
            conn.commit()

        user_profile = UserProfileResponse(
            user_id=user_id,
            email=email or None,
            phone_number=phone_number,
            full_name=full_name,
            auth_provider=auth_provider,
            avatar_url=avatar_url,
            created_at=created_at,
        )
        return AuthTokenResponse(
            token=token,
            expires_at=expires.isoformat(),
            user=user_profile,
            user_id=user_id,
            email=email or None,
            display_name=full_name,
            remember_me=remember_me,
        )

    def get_user_by_token(self, token: str) -> UserProfileResponse | None:
        """Validate bearer token and retrieve active user session with server-side expiration."""
        if not token:
            return None

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT u.id, u.email, u.phone_number, u.full_name, u.auth_provider, u.avatar_url, u.created_at, s.expires_at
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
                # Expired server-side session: revoke
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                return None

            email = row["email"]
            display_email = None if email and email.endswith("@kshetraiq.local") else email

            return UserProfileResponse(
                user_id=row["id"],
                email=display_email,
                phone_number=row["phone_number"],
                full_name=row["full_name"],
                auth_provider=row["auth_provider"] or "email",
                avatar_url=row["avatar_url"],
                created_at=row["created_at"],
            )

    def logout(self, token: str) -> bool:
        """Invalidate active session token from server database."""
        if not token:
            return False
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return cursor.rowcount > 0

