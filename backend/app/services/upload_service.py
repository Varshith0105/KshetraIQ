"""
KshetraIQ File Upload Service — Secure local temp storage for soil reports, field photos,
and crop/plant photos. Enforces file type, size limits, and safe filenames.
"""

import logging
import os
import re
import sqlite3
import uuid
from pathlib import Path

from app.core.config import Settings
from app.schemas.upload import UploadResponse

logger = logging.getLogger(__name__)

# Allowed MIME → extension mapping
ALLOWED_SOIL_REPORT_TYPES: dict[str, list[str]] = {
    "application/pdf": [".pdf"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
}

ALLOWED_PHOTO_TYPES: dict[str, list[str]] = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
}

ALLOWED_CATEGORIES = {"soil_report", "field_photo", "crop_photo"}

# Magic-byte signatures used to verify real file content (extension/MIME alone can be spoofed)
_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}


def _content_matches_extension(content: bytes, ext: str) -> bool:
    if ext == ".webp":
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    sigs = _SIGNATURES.get(ext)
    return bool(sigs) and any(content.startswith(sig) for sig in sigs)


def _safe_filename(original: str) -> str:
    """Strip path separators and dangerous characters, preserving the extension."""
    # Get only the basename (prevent path traversal)
    basename = os.path.basename(original)
    name, ext = os.path.splitext(basename)
    # Replace any non-alphanumeric/dash/underscore characters
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)[:80]
    safe_ext = ext.lower()[:10]
    file_id = uuid.uuid4().hex[:12]
    return f"{file_id}_{safe_name}{safe_ext}"


class UploadService:
    """Manages file uploads with server-side validation and safe local storage."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._upload_dir = Path(settings.resolved_model_directory).parent / ".uploads"
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        # Upload metadata is persisted in SQLite (was an in-memory dict, lost on every restart).
        self._db_path = Path(settings.resolved_sqlite_db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS uploads (
                    file_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    safe_filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_uploads_user ON uploads(user_id)")
        logger.info("Upload service initialized. Storage: %s", self._upload_dir)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def validate_and_save(
        self,
        file_content: bytes,
        original_filename: str,
        content_type: str | None,
        category: str,
        user_id: str | None = None,
    ) -> UploadResponse:
        """Validate file type, size, and category; save to local temp storage."""
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"Invalid upload category: {category}. Must be one of: {ALLOWED_CATEGORIES}")

        # Determine allowed types
        allowed = ALLOWED_SOIL_REPORT_TYPES if category == "soil_report" else ALLOWED_PHOTO_TYPES
        ext = os.path.splitext(original_filename)[1].lower()

        # Validate file type by extension
        valid_extension = False
        for mime, exts in allowed.items():
            if ext in exts:
                valid_extension = True
                break

        if not valid_extension:
            allowed_exts = sorted({e for exts in allowed.values() for e in exts})
            raise ValueError(
                f"File type '{ext}' is not allowed for {category}. "
                f"Accepted types: {', '.join(allowed_exts)}"
            )

        # Validate file size
        max_bytes = self._settings.max_upload_bytes
        if len(file_content) > max_bytes:
            max_mb = round(max_bytes / (1024 * 1024), 1)
            actual_mb = round(len(file_content) / (1024 * 1024), 1)
            raise ValueError(
                f"File size ({actual_mb} MB) exceeds the {max_mb} MB limit."
            )

        if len(file_content) == 0:
            raise ValueError("Uploaded file is empty.")

        if not _content_matches_extension(file_content, ext):
            raise ValueError(f"File content does not match its '{ext}' extension.")

        if content_type and content_type not in allowed and content_type != "application/octet-stream":
            raise ValueError(f"Content type '{content_type}' is not allowed for {category}.")

        if not user_id:
            raise ValueError("Authentication required to upload files.")

        # Generate safe filename and save
        safe_name = _safe_filename(original_filename)
        category_dir = self._upload_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        dest = category_dir / safe_name

        # Never overwrite
        if dest.exists():
            safe_name = f"dup_{uuid.uuid4().hex[:6]}_{safe_name}"
            dest = category_dir / safe_name

        dest.write_bytes(file_content)

        file_id = uuid.uuid4().hex
        record = {
            "file_id": file_id,
            "user_id": user_id,
            "original_filename": original_filename,
            "safe_filename": safe_name,
            "file_type": ext,
            "size_bytes": len(file_content),
            "category": category,
            "path": str(dest),
        }
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO uploads (file_id, user_id, original_filename, safe_filename, file_type, size_bytes, category, path)"
                " VALUES (:file_id, :user_id, :original_filename, :safe_filename, :file_type, :size_bytes, :category, :path)",
                record,
            )

        response = UploadResponse(
            file_id=file_id,
            original_filename=original_filename,
            safe_filename=safe_name,
            file_type=ext,
            size_bytes=len(file_content),
            category=category,
            storage="local_temp",
            message="File uploaded successfully to local server storage.",
        )
        logger.info("File uploaded: %s -> %s (%d bytes, user: %s)", original_filename, safe_name, len(file_content), user_id)
        return response

    def get_record(self, file_id: str, user_id: str | None = None) -> dict | None:
        if not user_id:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM uploads WHERE file_id = ? AND user_id = ?", (file_id, user_id)
            ).fetchone()
        return dict(row) if row else None

    def delete_file(self, file_id: str, user_id: str | None = None) -> bool:
        record = self.get_record(file_id, user_id)
        if not record:
            return False
        path = Path(record["path"]).resolve()
        if path.is_file() and self._upload_dir.resolve() in path.parents:
            path.unlink()
        with self._conn() as conn:
            conn.execute("DELETE FROM uploads WHERE file_id = ? AND user_id = ?", (file_id, user_id))
        return True

    def list_files(self, category: str | None = None, user_id: str | None = None) -> list[dict]:
        if not user_id:
            return []
        query = "SELECT * FROM uploads WHERE user_id = ?"
        params: list = [user_id]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "file_id": r["file_id"],
                "original_filename": r["original_filename"],
                "safe_filename": r["safe_filename"],
                "file_type": r["file_type"],
                "size_bytes": r["size_bytes"],
                "category": r["category"],
            }
            for r in rows
        ]
