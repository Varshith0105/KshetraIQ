"""
Tests for configurable storage, cache, and upload paths and Render permission safety.

Verifies:
- Safe fallback to /tmp/kshetraiq when /var/data is not writable (no persistent disk on Render)
- Zero PermissionError crashes during startup across all SQLite-backed services
- Preservation of local development paths
- Support for environment variable configuration of database, cache, and uploads
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from app.core.config import (
    Settings,
    ensure_writable_dir,
    get_safe_fallback_dir,
    is_running_on_render,
)
from app.services.activity_service import ActivityService
from app.services.auth_service import AuthService
from app.services.conversation_service import ConversationService
from app.services.market_price_service import MarketPriceService
from app.services.prediction_history_service import PredictionHistoryService
from app.services.profile_service import ProfileService
from app.services.storage import SQLiteStorage
from app.services.upload_service import UploadService


def test_is_running_on_render_detection():
    with patch.dict(os.environ, {"RENDER": "true"}, clear=False):
        assert is_running_on_render() is True
    with patch.dict(os.environ, {}, clear=True):
        assert is_running_on_render() is False


def test_ensure_writable_dir_falls_back_on_permission_error(tmp_path: Path):
    fallback_dir = tmp_path / "safe_fallback"
    forbidden_dir = Path("/var/data/unwritable_probe")

    orig_mkdir = Path.mkdir

    def mock_mkdir(self, *args, **kwargs):
        if "unwritable_probe" in str(self).replace("\\", "/"):
            raise PermissionError(13, "Permission denied")
        return orig_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", side_effect=mock_mkdir, autospec=True):
        result = ensure_writable_dir(forbidden_dir, fallback_dir=fallback_dir)
        assert result == fallback_dir
        assert fallback_dir.exists()


def test_settings_resolved_sqlite_db_path_fallback_on_render(tmp_path: Path):
    safe_temp = tmp_path / "render_tmp"

    with patch.dict(os.environ, {"RENDER": "true"}, clear=False):
        with patch("app.core.config.get_safe_fallback_dir", return_value=safe_temp):
            # Configure /var/data/kshetraiq.db as often set in Render templates
            settings = Settings(
                environment="production",
                sqlite_db_path=Path("/var/data/kshetraiq.db"),
                _env_file=None,
            )

            # When /var/data cannot be created (no disk attached on Render free tier)
            def mock_mkdir(self, *args, **kwargs):
                if "/var/data" in str(self).replace("\\", "/"):
                    raise PermissionError(13, "Permission denied: '/var/data'")
                return orig_mkdir(self, *args, **kwargs)

            orig_mkdir = Path.mkdir
            with patch.object(Path, "mkdir", side_effect=mock_mkdir, autospec=True):
                resolved = settings.resolved_sqlite_db_path
                # Must fall back to the safe application temp directory without PermissionError
                assert resolved.parent == safe_temp
                assert resolved.name == "kshetraiq.db"


def test_render_defaults_to_temp_when_no_persistent_disk(tmp_path: Path):
    safe_temp = tmp_path / "kshetraiq_tmp"

    with patch.dict(os.environ, {"RENDER": "true"}, clear=False):
        with patch("app.core.config.get_safe_fallback_dir", return_value=safe_temp):
            settings = Settings(
                environment="production",
                sqlite_db_path=None,
                _env_file=None,
            )
            resolved = settings.resolved_sqlite_db_path
            assert resolved.name == "kshetraiq.db"
            assert resolved.parent == safe_temp or "tmp" in str(resolved).lower()


def test_activity_service_startup_with_unwritable_var_data(tmp_path: Path):
    safe_temp = tmp_path / "activity_safe"

    with patch("app.core.config.get_safe_fallback_dir", return_value=safe_temp):
        settings = Settings(
            environment="production",
            sqlite_db_path=Path("/var/data/kshetraiq.db"),
            _env_file=None,
        )

        orig_mkdir = Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            if "/var/data" in str(self).replace("\\", "/"):
                raise PermissionError(13, "Permission denied: '/var/data'")
            return orig_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", side_effect=mock_mkdir, autospec=True):
            # Must not raise PermissionError during ActivityService instantiation
            svc = ActivityService(settings=settings, db_path=Path("/var/data/kshetraiq.db"))
            assert svc.db_path.parent.exists()
            assert svc.db_path.exists()

            # Verify functionality is completely preserved
            res = svc.log_activity(
                user_id="test_farmer_1",
                action="assessment_created",
                entity_type="assessment",
                entity_id="asmt_123",
                metadata={"crop": "Rice", "acreage": 3.0},
            )
            assert res.user_id == "test_farmer_1"
            recent = svc.get_recent_activities(user_id="test_farmer_1")
            assert len(recent) == 1
            assert recent[0].action == "assessment_created"


def test_market_price_service_mandi_cache_startup_with_unwritable_var_data(tmp_path: Path):
    safe_temp = tmp_path / "mandi_cache_safe"

    with patch("app.core.config.get_safe_fallback_dir", return_value=safe_temp):
        settings = Settings(
            environment="production",
            sqlite_db_path=Path("/var/data/kshetraiq.db"),
            _env_file=None,
        )

        orig_mkdir = Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            if "/var/data" in str(self).replace("\\", "/"):
                raise PermissionError(13, "Permission denied: '/var/data'")
            return orig_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", side_effect=mock_mkdir, autospec=True):
            # Must not raise PermissionError and must initialize mandi cache table
            with patch("app.core.config.get_settings", return_value=settings):
                market_svc = MarketPriceService(db_path=Path("/var/data/kshetraiq.db"))
                assert market_svc.db_path.parent.exists()
                assert market_svc.db_path.exists()

                # Verify table exists in the fallback database
                import sqlite3
                with sqlite3.connect(str(market_svc.db_path)) as conn:
                    cur = conn.cursor()
                    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                    assert "mandi_market_observations" in tables


def test_auth_service_startup_with_unwritable_var_data(tmp_path: Path):
    safe_temp = tmp_path / "auth_safe"

    with patch("app.core.config.get_safe_fallback_dir", return_value=safe_temp):
        settings = Settings(
            environment="production",
            sqlite_db_path=Path("/var/data/kshetraiq.db"),
            _env_file=None,
        )

        orig_mkdir = Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            if "/var/data" in str(self).replace("\\", "/"):
                raise PermissionError(13, "Permission denied: '/var/data'")
            return orig_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", side_effect=mock_mkdir, autospec=True):
            auth_svc = AuthService(settings=settings, db_path=Path("/var/data/kshetraiq.db"))
            assert auth_svc.db_path.parent.exists()
            assert auth_svc.db_path.exists()


def test_sqlite_storage_with_unwritable_var_data(tmp_path: Path):
    safe_temp = tmp_path / "storage_safe"

    with patch("app.core.config.get_safe_fallback_dir", return_value=safe_temp):
        orig_mkdir = Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            if "/var/data" in str(self).replace("\\", "/"):
                raise PermissionError(13, "Permission denied: '/var/data'")
            return orig_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", side_effect=mock_mkdir, autospec=True):
            storage = SQLiteStorage(db_path=Path("/var/data/kshetraiq.db"))
            assert storage.db_path.parent.exists()
            assert storage.db_path.exists()


def test_upload_service_with_unwritable_var_data(tmp_path: Path):
    safe_temp = tmp_path / "upload_safe"

    with patch("app.core.config.get_safe_fallback_dir", return_value=safe_temp):
        settings = Settings(
            environment="production",
            upload_dir=Path("/var/data/uploads"),
            _env_file=None,
        )

        orig_mkdir = Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            if "/var/data" in str(self).replace("\\", "/"):
                raise PermissionError(13, "Permission denied: '/var/data'")
            return orig_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", side_effect=mock_mkdir, autospec=True):
            upload_svc = UploadService(settings=settings)
            assert upload_svc._upload_dir.exists()
            assert upload_svc._upload_dir != Path("/var/data/uploads")


def test_conversation_prediction_profile_services_with_unwritable_path(tmp_path: Path):
    safe_temp = tmp_path / "misc_services_safe"

    with patch("app.core.config.get_safe_fallback_dir", return_value=safe_temp):
        settings = Settings(
            environment="production",
            sqlite_db_path=Path("/var/data/kshetraiq.db"),
            _env_file=None,
        )

        orig_mkdir = Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            if "/var/data" in str(self).replace("\\", "/"):
                raise PermissionError(13, "Permission denied: '/var/data'")
            return orig_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", side_effect=mock_mkdir, autospec=True):
            conv_svc = ConversationService(settings=settings, db_path=Path("/var/data/kshetraiq.db"))
            assert conv_svc.db_path.parent.exists()

            pred_svc = PredictionHistoryService(settings=settings)
            assert pred_svc.db_path.parent.exists()

            prof_svc = ProfileService(settings=settings, db_path=Path("/var/data/kshetraiq.db"))
            assert prof_svc.db_path.parent.exists()


def test_configurable_cache_and_upload_paths(tmp_path: Path):
    custom_cache = tmp_path / "custom_cache" / "cache.db"
    custom_upload = tmp_path / "custom_uploads"
    custom_db = tmp_path / "custom_db" / "main.db"

    settings = Settings(
        sqlite_db_path=custom_db,
        cache_db_path=custom_cache,
        upload_dir=custom_upload,
        _env_file=None,
    )

    assert settings.resolved_sqlite_db_path == custom_db
    assert settings.resolved_cache_db_path == custom_cache
    assert settings.resolved_upload_directory == custom_upload


def test_in_memory_db_path():
    settings = Settings(sqlite_db_path=Path(":memory:"), _env_file=None)
    assert settings.resolved_sqlite_db_path == Path(":memory:")
    assert settings.resolve_db_path(":memory:") == Path(":memory:")
