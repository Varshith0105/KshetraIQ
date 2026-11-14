from app.core.config import get_settings
from pathlib import Path

s = get_settings()
print(f"Environment: {s.environment}")
print(f"Google Client ID configured: {bool(s.google_client_id)}")
print(f"Google Client Secret configured: {bool(s.google_client_secret)}")
print(f"Google Redirect URI: {s.google_redirect_uri}")
print(f"CORS Origins: {s.cors_origins}")
print(f"Storage Backend: {s.storage_backend}")
print(f"SQLite DB Path: {s.sqlite_db_path}")
print(f"Env file path in config: {s.model_config.get('env_file')}")
if isinstance(s.model_config.get('env_file'), Path):
    print(f"Env file exists: {s.model_config.get('env_file').exists()}")

