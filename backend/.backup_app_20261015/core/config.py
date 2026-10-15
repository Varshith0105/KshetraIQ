from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    sqlite_db_path: Path = Field(default=Path("backend/.tmp/kshetraiq.db"), validation_alias=AliasChoices("KSHETRAIQ_SQLITE_PATH", "SQLITE_PATH"))

    llm_provider: str | None = Field(default=None, validation_alias=AliasChoices("LLM_PROVIDER", "KSHETRAIQ_LLM_PROVIDER"))
    llm_api_key: str | None = Field(default=None, validation_alias=AliasChoices("LLM_API_KEY", "KSHETRAIQ_LLM_API_KEY"))
    gemini_api_key: str | None = Field(default=None, validation_alias=AliasChoices("GEMINI_API_KEY", "KSHETRAIQ_GEMINI_API_KEY"))
    groq_api_key: str | None = Field(default=None, validation_alias=AliasChoices("GROQ_API_KEY", "KSHETRAIQ_GROQ_API_KEY"))
    openai_api_key: str | None = Field(default=None, validation_alias=AliasChoices("OPENAI_API_KEY", "KSHETRAIQ_OPENAI_API_KEY"))

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def resolved_model_directory(self) -> Path:
        return (Path(__file__).resolve().parents[3] / self.model_directory).resolve()

    @property
    def resolved_sqlite_db_path(self) -> Path:
        p = self.sqlite_db_path
        if not p.is_absolute():
            root_candidate = (Path(__file__).resolve().parents[3] / p).resolve()
            if root_candidate.is_file() or root_candidate.parent.exists():
                return root_candidate
            backend_candidate = (Path(__file__).resolve().parents[2] / p).resolve()
            if backend_candidate.is_file() or backend_candidate.parent.exists():
                return backend_candidate
            return root_candidate
        return p

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and (self.supabase_service_role_key or self.supabase_anon_key))

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
