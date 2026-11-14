"""Idempotent database migration script for KshetraIQ.

Ensures the canonical schema:
- users: id, email, phone_number, full_name, password_hash, salt, auth_provider, provider_id, avatar_url, created_at
- sessions: token, user_id, created_at, expires_at, remember_me
- phone_otps: phone_number, otp_hash, salt, attempts, created_at, expires_at
- oauth_states: state, redirect_uri, created_at, expires_at
- assessments: user_id column
- Preserves all existing records!
"""

import sqlite3
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.services.auth_service import AuthService
from app.core.config import get_settings


def migrate():
    settings = get_settings()
    db_paths = [
        settings.resolved_sqlite_db_path,
        backend_dir / ".tmp" / "kshetraiq.db",
        backend_dir.parent / ".tmp" / "kshetraiq.db",
    ]
    seen = set()
    for p in db_paths:
        resolved = p.resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        print(f"[*] Applying migration to: {resolved}")
        # AuthService.__init__ triggers _init_tables
        svc = AuthService(db_path=resolved, settings=settings)
        conn = sqlite3.connect(str(resolved))
        cur = conn.cursor()
        cols = [r[1] for r in cur.execute("PRAGMA table_info(users)").fetchall()]
        print(f"    Users columns: {cols}")
        user_count = cur.execute("SELECT count(*) FROM users").fetchone()[0]
        print(f"    Users count (preserved): {user_count}")
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"    Tables: {tables}")
        if "assessments" in tables:
            ass_count = cur.execute("SELECT count(*) FROM assessments").fetchone()[0]
            print(f"    Assessments count (preserved): {ass_count}")
        conn.close()
    print("[+] Migration completed successfully!")


if __name__ == "__main__":
    migrate()

