from functools import lru_cache
import logging
import os
from pathlib import Path
import secrets
import tempfile

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def is_running_on_render() -> bool:
    """Detect whether the application is running inside a Render container environment."""
    return bool(os.environ.get("RENDER")) or bool(os.environ.get("IS_RENDER"))


def get_safe_fallback_dir() -> Path:
    """
    Return a guaranteed-writable application-local temporary directory.
    On Render/Linux, this is /tmp/kshetraiq.
    On Windows, this is <tempdir>/kshetraiq.
    """
    if is_running_on_render() or os.name != "nt":
        target = Path("/tmp/kshetraiq")
    else:
        target = Path(tempfile.gettempdir()) / "kshetraiq"
    try:
        target.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning("Could not create fallback directory %s: %s", target, e)
    return target


def ensure_writable_dir(directory: Path, fallback_dir: Path | None = None) -> Path:
    """
    Ensure the target directory exists and is writable.
    If directory creation or writing fails (e.g. PermissionError on '/var/data' on Render
    when no persistent disk is mounted), safely falls back to fallback_dir (/tmp/kshetraiq).
    """
    fb = fallback_dir or get_safe_fallback_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        # Test writability with a small probe file
        probe = directory / f".probe_{secrets.token_hex(4)}"
        try:
            probe.touch(exist_ok=True)
            probe.unlink(missing_ok=True)
            return directory
        except (PermissionError, OSError) as write_err:
            logger.warning(
                "Directory %s exists but is not writable (%s). Falling back to %s. "
                "NOTE: /tmp storage is temporary and may be lost when the service restarts or redeploys.",
                directory,
                write_err,
                fb,
            )
            try:
                fb.mkdir(parents=True, exist_ok=True)
            except Exception as fb_err:
                logger.warning("Could not create fallback directory %s: %s", fb, fb_err)
            return fb
    except (PermissionError, OSError) as perm_err:
        logger.warning(
            "Directory %s cannot be created or accessed (%s). Falling back to %s. "
            "NOTE: /tmp storage is temporary and may be lost when the service restarts or redeploys.",
            directory,
            perm_err,
            fb,
        )
        try:
            fb.mkdir(parents=True, exist_ok=True)
        except Exception as fb_err:
            logger.warning("Could not create fallback directory %s: %s", fb, fb_err)
        return fb


class Settings(BaseSettings):
    """Server-side configuration loaded from the repository root `.env` when present."""

    environment: str = Field(default="development", validation_alias=AliasChoices("KSHETRAIQ_ENVIRONMENT", "ENVIRONMENT"))
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://172.20.34.119:3000",
        validation_alias=AliasChoices("KSHETRAIQ_CORS_ORIGINS", "CORS_ORIGINS"),
    )
    model_directory: Path = Field(default=Path("Agriverse_Models"), validation_alias=AliasChoices("KSHETRAIQ_MODEL_DIRECTORY", "MODEL_DIRECTORY"))
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, validation_alias=AliasChoices("KSHETRAIQ_MAX_UPLOAD_BYTES", "MAX_UPLOAD_BYTES"))

    supabase_url: str | None = Field(default=None, validation_alias=AliasChoices("SUPABASE_URL", "KSHETRAIQ_SUPABASE_URL"))
    supabase_anon_key: str | None = Field(default=None, validation_alias=AliasChoices("SUPABASE_ANON_KEY", "KSHETRAIQ_SUPABASE_ANON_KEY"))
    supabase_service_role_key: str | None = Field(default=None, validation_alias=AliasChoices("SUPABASE_SERVICE_ROLE_KEY", "KSHETRAIQ_SUPABASE_SERVICE_ROLE_KEY"))

    storage_backend: str = Field(default="sqlite", validation_alias=AliasChoices("KSHETRAIQ_STORAGE_BACKEND", "STORAGE_BACKEND"))
    sqlite_db_path: Path | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "KSHETRAIQ_SQLITE_PATH",
            "SQLITE_PATH",
            "KSHETRAIQ_DB_PATH",
            "DB_PATH",
            "DATABASE_PATH",
        ),
    )
    cache_db_path: Path | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "KSHETRAIQ_CACHE_DB_PATH",
            "CACHE_DB_PATH",
            "KSHETRAIQ_CACHE_PATH",
            "CACHE_PATH",
        ),
    )
    cache_dir: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("KSHETRAIQ_CACHE_DIR", "CACHE_DIR"),
    )
    upload_dir: Path | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "KSHETRAIQ_UPLOAD_DIR",
            "UPLOAD_DIR",
            "KSHETRAIQ_UPLOAD_DIRECTORY",
            "UPLOAD_DIRECTORY",
        ),
    )
    data_dir: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("KSHETRAIQ_DATA_DIR", "DATA_DIR"),
    )

    google_client_id: str | None = Field(default=None, validation_alias=AliasChoices("GOOGLE_CLIENT_ID", "KSHETRAIQ_GOOGLE_CLIENT_ID"))
    google_client_secret: str | None = Field(default=None, validation_alias=AliasChoices("GOOGLE_CLIENT_SECRET", "KSHETRAIQ_GOOGLE_CLIENT_SECRET"))
    google_redirect_uri: str = Field(default="http://localhost:3000/auth/callback", validation_alias=AliasChoices("GOOGLE_REDIRECT_URI", "KSHETRAIQ_GOOGLE_REDIRECT_URI"))

    sms_provider: str = Field(default="console", validation_alias=AliasChoices("SMS_PROVIDER", "KSHETRAIQ_SMS_PROVIDER"))
    sms_api_key: str | None = Field(default=None, validation_alias=AliasChoices("SMS_API_KEY", "KSHETRAIQ_SMS_API_KEY"))
    sms_sender_id: str | None = Field(default="KSHTRA", validation_alias=AliasChoices("SMS_SENDER_ID", "KSHETRAIQ_SMS_SENDER_ID"))

    session_expiry_hours: int = Field(default=24, validation_alias=AliasChoices("SESSION_EXPIRY_HOURS", "KSHETRAIQ_SESSION_EXPIRY_HOURS"))
    persistent_session_days: int = Field(default=30, validation_alias=AliasChoices("PERSISTENT_SESSION_DAYS", "KSHETRAIQ_PERSISTENT_SESSION_DAYS"))
    password_reset_expiry_minutes: int = Field(default=30, validation_alias=AliasChoices("PASSWORD_RESET_EXPIRY_MINUTES", "KSHETRAIQ_PASSWORD_RESET_EXPIRY_MINUTES"))
    email_provider: str = Field(default="console", validation_alias=AliasChoices("EMAIL_PROVIDER", "KSHETRAIQ_EMAIL_PROVIDER"))
    email_from: str | None = Field(default=None, validation_alias=AliasChoices("EMAIL_FROM", "KSHETRAIQ_EMAIL_FROM"))
    smtp_host: str | None = Field(default=None, validation_alias=AliasChoices("SMTP_HOST", "KSHETRAIQ_SMTP_HOST"))
    smtp_port: int = Field(default=587, validation_alias=AliasChoices("SMTP_PORT", "KSHETRAIQ_SMTP_PORT"))
    smtp_username: str | None = Field(default=None, validation_alias=AliasChoices("SMTP_USERNAME", "KSHETRAIQ_SMTP_USERNAME"))
    smtp_password: str | None = Field(default=None, validation_alias=AliasChoices("SMTP_PASSWORD", "KSHETRAIQ_SMTP_PASSWORD"))

    llm_provider: str | None = Field(default=None, validation_alias=AliasChoices("LLM_PROVIDER", "KSHETRAIQ_LLM_PROVIDER"))
    llm_api_key: str | None = Field(default=None, validation_alias=AliasChoices("LLM_API_KEY", "KSHETRAIQ_LLM_API_KEY"))
    gemini_api_key: str | None = Field(default=None, validation_alias=AliasChoices("GEMINI_API_KEY", "KSHETRAIQ_GEMINI_API_KEY"))
    groq_api_key: str | None = Field(default=None, validation_alias=AliasChoices("GROQ_API_KEY", "KSHETRAIQ_GROQ_API_KEY"))
    openai_api_key: str | None = Field(default=None, validation_alias=AliasChoices("OPENAI_API_KEY", "KSHETRAIQ_OPENAI_API_KEY"))
    data_gov_in_api_key: str | None = Field(default=None, validation_alias=AliasChoices("DATA_GOV_IN_API_KEY", "KSHETRAIQ_DATA_GOV_IN_API_KEY"))
    # Optional heavyweight intelligence integrations.  These are deliberately
    # opt-in: model weights and Earth Engine credentials must never be fetched
    # or embedded by the API at start-up.
    sam_checkpoint_path: Path | None = Field(default=None, validation_alias=AliasChoices("SAM_CHECKPOINT_PATH", "KSHETRAIQ_SAM_CHECKPOINT_PATH"))
    earth_engine_project: str | None = Field(default=None, validation_alias=AliasChoices("EARTH_ENGINE_PROJECT", "KSHETRAIQ_EARTH_ENGINE_PROJECT"))
    earth_engine_service_account: str | None = Field(default=None, validation_alias=AliasChoices("EARTH_ENGINE_SERVICE_ACCOUNT", "KSHETRAIQ_EARTH_ENGINE_SERVICE_ACCOUNT"))
    earth_engine_credentials_path: Path | None = Field(default=None, validation_alias=AliasChoices("EARTH_ENGINE_CREDENTIALS_PATH", "KSHETRAIQ_EARTH_ENGINE_CREDENTIALS_PATH"))

    # Permit explicit Settings(...) values in tests and app factories while
    # still accepting the deployment aliases used in environment files.
    # Resolve from the repository root so `uvicorn app.main:app` started in
    # backend/ and scripts started at the repository root read the same file.
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def resolved_model_directory(self) -> Path:
        return (Path(__file__).resolve().parents[3] / self.model_directory).resolve()

    @property
    def resolved_sam_checkpoint_path(self) -> Path | None:
        if self.sam_checkpoint_path and Path(self.sam_checkpoint_path).is_file():
            return Path(self.sam_checkpoint_path)
        repo_root = Path(__file__).resolve().parents[3]
        candidates = [
            repo_root / "capstone-final" / "sam_vit_b_01ec64.pth",
            repo_root / "Agriverse_Models" / "sam_vit_b_01ec64.pth",
            repo_root / "capstone-final" / "sam_vit_h_4b8939.pth",
        ]
        for c in candidates:
            if c.is_file():
                return c
        return None

    @property
    def resolved_sqlite_db_path(self) -> Path:
        """
        Resolve SQLite database path safely across Render, Windows, and local Linux.
        If a persistent disk path (e.g. /var/data/kshetraiq.db) is configured but no disk
        is mounted or writable, safely falls back to /tmp/kshetraiq/kshetraiq.db.
        """
        # 1. Determine candidate path
        if self.sqlite_db_path is not None:
            p = self.sqlite_db_path
        elif self.data_dir is not None:
            p = self.data_dir / "kshetraiq.db"
        elif is_running_on_render():
            render_disk_dir = Path("/var/data")
            if render_disk_dir.is_dir() and os.access(render_disk_dir, os.W_OK):
                p = render_disk_dir / "kshetraiq.db"
            else:
                p = Path("/tmp/kshetraiq/kshetraiq.db")
        else:
            p = Path("backend/.tmp/kshetraiq.db")

        # In-memory database check
        if str(p) == ":memory:":
            return Path(":memory:")

        # 2. Resolve relative candidate paths against repository root
        if not p.is_absolute():
            root_candidate = (Path(__file__).resolve().parents[3] / p).resolve()
            if root_candidate.is_file() or root_candidate.parent.exists():
                p = root_candidate
            else:
                backend_candidate = (Path(__file__).resolve().parents[2] / p).resolve()
                if backend_candidate.is_file() or backend_candidate.parent.exists():
                    p = backend_candidate
                else:
                    p = root_candidate

        # 3. Ensure parent directory is writable; fallback to /tmp/kshetraiq on PermissionError
        safe_parent = ensure_writable_dir(p.parent)
        return safe_parent / p.name

    def resolve_db_path(self, db_path: Path | str | None = None) -> Path:
        """
        Safely resolve any candidate database path against writable storage.
        If parent directory is not writable (e.g. /var/data without persistent disk),
        falls back to a writable directory without raising PermissionError.
        """
        if db_path is None:
            return self.resolved_sqlite_db_path
        p = Path(db_path)
        if str(p) == ":memory:":
            return Path(":memory:")
        if not p.is_absolute():
            p = (Path(__file__).resolve().parents[3] / p).resolve()
        safe_parent = ensure_writable_dir(p.parent)
        return safe_parent / p.name

    @property
    def resolved_cache_db_path(self) -> Path:
        """
        Resolve SQLite cache database path for mandi observations and market cache.
        Defaults to sharing the primary SQLite database path unless explicitly configured.
        """
        if self.cache_db_path is not None:
            return self.resolve_db_path(self.cache_db_path)
        if self.cache_dir is not None:
            safe_dir = ensure_writable_dir(self.cache_dir)
            return safe_dir / "mandi_cache.db"
        return self.resolved_sqlite_db_path

    @property
    def resolved_upload_directory(self) -> Path:
        """
        Resolve file upload directory safely across environments.
        """
        if self.upload_dir is not None:
            p = self.upload_dir
            if not p.is_absolute():
                p = (Path(__file__).resolve().parents[3] / p).resolve()
            return ensure_writable_dir(p)
        if self.data_dir is not None:
            return ensure_writable_dir(self.data_dir / "uploads")
        if is_running_on_render():
            render_disk_dir = Path("/var/data")
            if render_disk_dir.is_dir() and os.access(render_disk_dir, os.W_OK):
                return ensure_writable_dir(render_disk_dir / "uploads")
            return ensure_writable_dir(Path("/tmp/kshetraiq/uploads"))
        local_uploads = (Path(__file__).resolve().parents[3] / ".uploads").resolve()
        return ensure_writable_dir(local_uploads)

    def ensure_writable_dir(self, directory: Path, fallback_dir: Path | None = None) -> Path:
        return ensure_writable_dir(directory, fallback_dir)

    def get_safe_fallback_dir(self) -> Path:
        return get_safe_fallback_dir()

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and (self.supabase_service_role_key or self.supabase_anon_key))

    @property
    def has_google_oauth(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def has_sms_provider(self) -> bool:
        return bool(self.sms_api_key or self.sms_provider == "console")

    @property
    def has_email_delivery(self) -> bool:
        return bool(self.email_provider.lower() == "smtp" and self.email_from and self.smtp_host)

    @property
    def effective_llm_api_key(self) -> str | None:
        if self.llm_api_key:
            return self.llm_api_key
        if self.llm_provider == "gemini" or not self.llm_provider:
            if self.gemini_api_key:
                return self.gemini_api_key
        if self.llm_provider == "groq":
            return self.groq_api_key
        if self.llm_provider == "openai":
            return self.openai_api_key
        return self.gemini_api_key or self.groq_api_key or self.openai_api_key

    @property
    def effective_llm_provider(self) -> str | None:
        if self.llm_provider:
            return self.llm_provider.lower()
        if self.gemini_api_key:
            return "gemini"
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"
        if self.llm_api_key:
            return "custom"
        return None

    @property
    def has_llm(self) -> bool:
        return bool(self.effective_llm_api_key)

    @property
    def cors_origins_list(self) -> list[str]:
        configured = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        defaults = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://172.20.34.119:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://172.20.34.119:8000",
        ]
        seen = set()
        merged: list[str] = []
        for origin in configured + defaults:
            if origin not in seen:
                seen.add(origin)
                merged.append(origin)
        return merged

    @property
    def cors_origin_regex(self) -> str | None:
        if self.environment == "development":
            # Allow local private LAN IPs and loopbacks on any port during development
            return r"^https?://(localhost|127\.0\.0\.1|172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?$"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
