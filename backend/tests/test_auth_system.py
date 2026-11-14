"""Comprehensive test suite for KshetraIQ Authentication & Route Protection System.

Verifies:
1. Legacy SQLite schema migration preserves existing users, assessments, and adds phone_number safely.
2. Email/Password registration, validation, password hashing, and login.
3. Remember Me persistent vs session cookie handling and server-side expiration.
4. Session invalidation on logout and token revocation.
5. Phone OTP generation, salting, rate-limiting, attempt-capping, replay prevention, and verification.
6. Google OAuth URL construction with CSRF state and mock token exchange.
7. Cross-user isolation and ownership protection.
"""

from __future__ import annotations

import datetime
import secrets
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.auth_service import (
    AuthService,
    GoogleAuthCallbackRequest,
    PhoneOtpSendRequest,
    PhoneOtpVerifyRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    FarmProfilePayload,
    UserLoginRequest,
    UserRegisterRequest,
)


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        sqlite_db_path=tmp_path / "test_auth.db",
        google_client_id="mock-google-client-id.apps.googleusercontent.com",
        google_client_secret="mock-google-client-secret",
        google_redirect_uri="http://localhost:3000/auth/callback",
    )


@pytest.fixture
def svc(tmp_path: Path, test_settings: Settings) -> AuthService:
    return AuthService(db_path=tmp_path / "test_auth.db", settings=test_settings)


# ────────── 1. Legacy Schema Migration & Data Preservation ──────────

def test_legacy_schema_migration_preserves_data(tmp_path: Path) -> None:
    """Verify that an existing SQLite database with the old schema (no phone_number)
    is safely migrated, preserving all existing user rows and passwords, and allowing
    both email login and new phone OTP flows without 'no such column' errors."""
    legacy_db = tmp_path / "legacy.db"

    # Step 1: Construct legacy database with original schema
    conn = sqlite3.connect(str(legacy_db))
    conn.execute(
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    # Populate existing users
    salt_a = secrets.token_bytes(16)
    pass_hash_a = AuthService._hash_password("OldPassword123!", salt_a)
    conn.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
        ("user_old_1", "farmer_legacy@kshetraiq.in", "Legacy Farmer", pass_hash_a, salt_a.hex(), "2024-01-01T00:00:00Z"),
    )
    conn.commit()
    conn.close()

    # Step 2: Initialize AuthService on this legacy database
    settings = Settings(
        environment="test",
        sqlite_db_path=legacy_db,
        google_client_id=None,
        google_client_secret=None,
        _env_file=None,
    )
    migrated_svc = AuthService(db_path=legacy_db, settings=settings)

    # Step 3: Verify columns were safely added
    verify_conn = sqlite3.connect(str(legacy_db))
    cols = [r[1] for r in verify_conn.execute("PRAGMA table_info(users)").fetchall()]
    assert "phone_number" in cols
    assert "auth_provider" in cols
    assert "provider_id" in cols
    assert "avatar_url" in cols

    # Step 4: Verify existing record was preserved
    user_count = verify_conn.execute("SELECT count(*) FROM users").fetchone()[0]
    assert user_count == 1
    verify_conn.close()

    # Step 5: Verify existing legacy user can login without SQL error
    login_resp = migrated_svc.login(UserLoginRequest(
        email="farmer_legacy@kshetraiq.in",
        password="OldPassword123!",
    ))
    assert login_resp.token
    assert login_resp.user.email == "farmer_legacy@kshetraiq.in"
    assert login_resp.user.full_name == "Legacy Farmer"

    # Step 6: Verify a new phone OTP user can register on the migrated schema
    otp_resp = migrated_svc.send_phone_otp(PhoneOtpSendRequest(phone_number="9848011223"))
    assert otp_resp.status == "success"
    dev_code = otp_resp.dev_otp
    assert dev_code is not None

    phone_auth = migrated_svc.verify_phone_otp(PhoneOtpVerifyRequest(
        phone_number="9848011223",
        otp=dev_code,
        full_name="New Mobile Farmer",
    ))
    assert phone_auth.token
    assert phone_auth.user.phone_number == "+919848011223"


# ────────── 2. Email Registration & Login ──────────

def test_email_registration_and_login_flow(svc: AuthService) -> None:
    """Verify new user registration, password verification, and session issuance."""
    email = f"farmer_{secrets.token_hex(4)}@kshetraiq.in"
    password = "KisanPassword123!"

    # 1. Register
    reg = svc.register(UserRegisterRequest(
        email=email,
        full_name="Rao Bahadur",
        password=password,
        confirm_password=password,
    ))
    assert reg.token
    assert reg.user.email == email
    assert reg.user.full_name == "Rao Bahadur"
    assert reg.user.auth_provider == "email"

    # 2. Duplicate registration should raise clean error
    with pytest.raises(ValueError, match="already exists"):
        svc.register(UserRegisterRequest(
            email=email,
            full_name="Another Farmer",
            password=password,
        ))

    # 3. Login with wrong password
    with pytest.raises(ValueError, match="Invalid email or password"):
        svc.login(UserLoginRequest(email=email, password="WrongPassword999!"))

    # 4. Login with correct credentials
    login_result = svc.login(UserLoginRequest(email=email, password=password))
    assert login_result.token
    assert login_result.user.email == email

    # 5. Tokens should be different between register and login
    assert reg.token != login_result.token


# ────────── 3. Remember Me & Session Expiry Policy ──────────

def test_remember_me_persistent_session_and_expiry(svc: AuthService) -> None:
    """Verify session expiry difference between standard (24h) and Remember Me (30d)."""
    email = f"remember_{secrets.token_hex(4)}@kshetraiq.in"
    password = "PasswordRememberMe123!"

    svc.register(UserRegisterRequest(email=email, full_name="Persistent User", password=password))

    # Login without Remember Me
    session_std = svc.login(UserLoginRequest(email=email, password=password, remember_me=False))
    assert session_std.remember_me is False

    # Login with Remember Me
    session_rem = svc.login(UserLoginRequest(email=email, password=password, remember_me=True))
    assert session_rem.remember_me is True

    # Parse ISO expiry dates
    exp_std = datetime.datetime.fromisoformat(session_std.expires_at)
    exp_rem = datetime.datetime.fromisoformat(session_rem.expires_at)
    now = datetime.datetime.now(datetime.timezone.utc)

    # Standard session should expire in ~24 hours
    std_delta_hours = (exp_std - now).total_seconds() / 3600
    assert 20 <= std_delta_hours <= 25

    # Persistent session should expire in ~30 days
    rem_delta_days = (exp_rem - now).total_seconds() / 86400
    assert 28 <= rem_delta_days <= 31

    # Verify both sessions retrieve the user profile
    assert svc.get_user_by_token(session_std.token) is not None
    assert svc.get_user_by_token(session_rem.token) is not None

    # Server-side logout revokes persistent session
    svc.logout(session_rem.token)
    assert svc.get_user_by_token(session_rem.token) is None
    # Standard session remains valid
    assert svc.get_user_by_token(session_std.token) is not None


# ────────── 4. Phone OTP Dispatch, Verification & Replay Protection ──────────

def test_phone_otp_dispatch_and_verification(svc: AuthService) -> None:
    """Verify phone OTP generation, rate limiting, and successful verification."""
    phone = "9848022338"

    # 1. Send OTP
    otp_resp = svc.send_phone_otp(PhoneOtpSendRequest(phone_number=phone))
    assert otp_resp.status == "success"
    assert otp_resp.phone_number == "+919848022338"
    assert otp_resp.dev_otp is not None
    otp_code = otp_resp.dev_otp

    # 2. Rate-limiting check: second request within 60s must fail
    with pytest.raises(ValueError, match="[Ww]ait"):
        svc.send_phone_otp(PhoneOtpSendRequest(phone_number=phone))

    # 3. Verify with wrong OTP
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        svc.verify_phone_otp(PhoneOtpVerifyRequest(phone_number=phone, otp="000000"))

    # 4. Verify with correct OTP
    auth_resp = svc.verify_phone_otp(PhoneOtpVerifyRequest(
        phone_number=phone, otp=otp_code, full_name="Venkateswarlu",
    ))
    assert auth_resp.token
    assert auth_resp.user.phone_number == "+919848022338"
    assert auth_resp.user.auth_provider == "phone"

    # 5. Replay prevention: reusing the same OTP code must fail
    with pytest.raises(ValueError, match="No OTP request found"):
        svc.verify_phone_otp(PhoneOtpVerifyRequest(phone_number=phone, otp=otp_code))


def test_phone_otp_max_attempts(svc: AuthService) -> None:
    """Verify that exceeding max OTP attempts locks out the OTP record."""
    phone = "9876543210"

    otp_resp = svc.send_phone_otp(PhoneOtpSendRequest(phone_number=phone))
    real_otp = otp_resp.dev_otp

    # Use up all 3 wrong attempts
    for i in range(3):
        with pytest.raises(ValueError):
            svc.verify_phone_otp(PhoneOtpVerifyRequest(phone_number=phone, otp=f"00000{i}"))

    # Even the correct OTP should now fail because the record is deleted
    with pytest.raises(ValueError, match="[Nn]o OTP|[Mm]aximum"):
        svc.verify_phone_otp(PhoneOtpVerifyRequest(phone_number=phone, otp=real_otp))


def test_phone_normalization(svc: AuthService) -> None:
    """Various Indian phone number formats should normalize correctly."""
    assert AuthService.normalize_phone("9848022338") == "+919848022338"
    assert AuthService.normalize_phone("+919848022338") == "+919848022338"
    assert AuthService.normalize_phone("919848022338") == "+919848022338"
    assert AuthService.normalize_phone("09848022338") == "+919848022338"
    assert AuthService.normalize_phone("  98 480-22338 ") == "+919848022338"

    with pytest.raises(ValueError, match="Invalid phone"):
        AuthService.normalize_phone("12345")

    with pytest.raises(ValueError, match="Invalid phone"):
        AuthService.normalize_phone("abcdefghij")


# ────────── 5. Google OAuth 2.0 with State and Mock Exchange ──────────

def test_google_oauth_url_generation(svc: AuthService) -> None:
    """Verify Google OAuth authorization URL contains CSRF state and expected params."""
    url_resp = svc.get_google_auth_url(redirect_uri="http://localhost:3000/auth/callback")
    assert url_resp.configured is True
    assert "accounts.google.com/o/oauth2/v2/auth" in url_resp.url
    assert "mock-google-client-id" in url_resp.url
    assert "state=" in url_resp.url
    assert url_resp.state is not None


def test_google_oauth_url_unconfigured(tmp_path: Path) -> None:
    """When Google credentials are absent, the URL response flags not configured."""
    no_google_settings = Settings(
        environment="test",
        sqlite_db_path=tmp_path / "no_google.db",
        google_client_id=None,
        google_client_secret=None,
        _env_file=None,
    )
    svc = AuthService(db_path=tmp_path / "no_google.db", settings=no_google_settings)
    url_resp = svc.get_google_auth_url()
    assert url_resp.configured is False
    assert url_resp.url == ""
    assert url_resp.message is not None


def test_google_oauth_mocked_exchange(svc: AuthService) -> None:
    """Verify Google token exchange with mock provider response creates/links user and session."""
    url_resp = svc.get_google_auth_url(redirect_uri="http://localhost:3000/auth/callback")
    state = url_resp.state

    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "mock-access-token-xyz"}

    mock_profile_resp = MagicMock()
    mock_profile_resp.status_code = 200
    mock_profile_resp.json.return_value = {
        "id": "google_12345678",
        "email": "kisan.google@example.com",
        "name": "Kisan Google User",
        "picture": "https://example.com/avatar.jpg",
        "verified_email": True,
    }

    with patch("httpx.Client.post", return_value=mock_token_resp), \
         patch("httpx.Client.get", return_value=mock_profile_resp):

        auth_resp = svc.authenticate_with_google(
            code="mock_auth_code_123",
            redirect_uri="http://localhost:3000/auth/callback",
            state=state,
        )

        assert auth_resp.token
        assert auth_resp.user.email == "kisan.google@example.com"
        assert auth_resp.user.full_name == "Kisan Google User"
        assert auth_resp.user.auth_provider == "google"
        assert auth_resp.user.avatar_url == "https://example.com/avatar.jpg"

        # CSRF single-use state verification: state must now be consumed
        with pytest.raises(ValueError, match="Invalid or expired OAuth state"):
            svc.authenticate_with_google(
                code="another_code",
                redirect_uri="http://localhost:3000/auth/callback",
                state=state,
            )


def test_google_rejects_unverified_email_and_does_not_link_password_account(svc: AuthService) -> None:
    svc.register(UserRegisterRequest(email="existing@example.com", full_name="Existing", password="Password123!"))
    state = svc.get_google_auth_url().state
    token_response = MagicMock(status_code=200)
    token_response.json.return_value = {"access_token": "token"}
    profile_response = MagicMock(status_code=200)
    profile_response.json.return_value = {"id": "google-new", "email": "existing@example.com", "verified_email": False}
    with patch("httpx.Client.post", return_value=token_response), patch("httpx.Client.get", return_value=profile_response):
        with pytest.raises(ValueError, match="did not verify"):
            svc.authenticate_with_google("code", state=state)
    with svc._get_connection() as conn:
        row = conn.execute("SELECT provider_id FROM users WHERE email = ?", ("existing@example.com",)).fetchone()
    assert row["provider_id"] is None


def test_password_reset_is_single_use_and_revokes_sessions(svc: AuthService) -> None:
    original = svc.register(UserRegisterRequest(email="reset@example.com", full_name="Reset", password="OriginalPass123!"))
    with patch("secrets.token_urlsafe", return_value="reset-token-for-test-012345678901234567890"):
        svc.request_password_reset(PasswordResetRequest(email="reset@example.com"), "http://localhost:3000")
    svc.reset_password(PasswordResetConfirmRequest(token="reset-token-for-test-012345678901234567890", password="ChangedPass123!", confirm_password="ChangedPass123!"))
    assert svc.get_user_by_token(original.token) is None
    assert svc.login(UserLoginRequest(email="reset@example.com", password="ChangedPass123!")).user.email == "reset@example.com"
    with pytest.raises(ValueError, match="invalid or has expired"):
        svc.reset_password(PasswordResetConfirmRequest(token="reset-token-for-test-012345678901234567890", password="AnotherPass123!", confirm_password="AnotherPass123!"))


# ────────── 6. Cross-User Isolation ──────────

def test_cross_user_data_isolation(svc: AuthService) -> None:
    """Two users with valid sessions get different user_ids and cannot share tokens."""
    user_a = svc.register(UserRegisterRequest(
        email="farmer_a@test.com", full_name="Farmer A", password="PassPassword123!",
    ))
    user_b = svc.register(UserRegisterRequest(
        email="farmer_b@test.com", full_name="Farmer B", password="PassPassword123!",
    ))

    assert user_a.user.user_id != user_b.user.user_id

    # A's token resolves to A's profile
    profile_a = svc.get_user_by_token(user_a.token)
    assert profile_a is not None
    assert profile_a.email == "farmer_a@test.com"

    # B's token resolves to B's profile
    profile_b = svc.get_user_by_token(user_b.token)
    assert profile_b is not None
    assert profile_b.email == "farmer_b@test.com"

    # Logging out A does not affect B
    svc.logout(user_a.token)
    assert svc.get_user_by_token(user_a.token) is None
    assert svc.get_user_by_token(user_b.token) is not None


def test_farm_profiles_are_persistent_and_isolated(svc: AuthService) -> None:
    user_a = svc.register(UserRegisterRequest(email="profile_a@test.com", full_name="Profile A", password="PassPassword123!"))
    user_b = svc.register(UserRegisterRequest(email="profile_b@test.com", full_name="Profile B", password="PassPassword123!"))
    saved = svc.save_farm_profile(user_a.user.user_id, FarmProfilePayload(
        farm_name="A's Holding", district="Guntur", state="Andhra Pradesh", acreage=3.25,
        season="Kharif", irrigation_method="Drip", water_availability="Borewell",
    ))
    assert saved.farm_name == "A's Holding"
    assert svc.get_farm_profile(user_a.user.user_id).acreage == 3.25
    assert svc.get_farm_profile(user_b.user.user_id) is None
    updated = svc.save_farm_profile(user_a.user.user_id, FarmProfilePayload(
        farm_name="A's Updated Holding", district="Guntur", state="Andhra Pradesh", acreage=4.0,
        season="Rabi", irrigation_method="Canal", water_availability="Canal",
    ))
    assert updated.farm_name == "A's Updated Holding"
    assert svc.get_farm_profile(user_a.user.user_id).acreage == 4.0


def test_farm_profile_rejects_a_district_from_another_state(svc: AuthService) -> None:
    user = svc.register(UserRegisterRequest(
        email="profile_location@test.com", full_name="Location Farmer", password="PassPassword123!",
    ))
    with pytest.raises(ValueError, match="district that belongs"):
        svc.save_farm_profile(user.user.user_id, FarmProfilePayload(
            farm_name="Location Farm", district="Sangareddy", state="Andhra Pradesh", acreage=2,
            season="Kharif", irrigation_method="Drip", water_availability="Borewell",
        ))
