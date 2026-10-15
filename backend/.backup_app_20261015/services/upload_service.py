"""
KshetraIQ File Upload Service — Secure local temp storage for soil reports, field photos,
and crop/plant photos. Enforces file type, size limits, and safe filenames.
"""

import logging
import os
import re
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
        self._records: dict[str, dict] = {}
        logger.info("Upload service initialized. Storage: %s", self._upload_dir)

    def validate_and_save(
        self,
        file_content: bytes,
        original_filename: str,
        content_type: str | None,
        category: str,
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
            "original_filename": original_filename,
            "safe_filename": safe_name,
            "file_type": ext,
            "size_bytes": len(file_content),
            "category": category,
            "path": str(dest),
        }
        self._records[file_id] = record

        response = UploadResponse(
            file_id=file_id,
            original_filename=original_filename,
            safe_filename=safe_name,
            file_type=ext,
            size_bytes=len(file_content),
            category=category,
            storage="local_temp",
            message=f"File uploaded successfully. Note: stored in local temporary directory. Configure Supabase Storage for persistent private storage.",
        )
        logger.info("File uploaded: %s -> %s (%d bytes)", original_filename, safe_name, len(file_content))
        return response

    def get_record(self, file_id: str) -> dict | None:
        return self._records.get(file_id)

    def delete_file(self, file_id: str) -> bool:
        record = self._records.get(file_id)
        if not record:
            return False
        path = Path(record["path"])
        if path.is_file():
            path.unlink()
        del self._records[file_id]
        return True

    def list_files(self, category: str | None = None) -> list[dict]:
        records = list(self._records.values())
        if category:
            records = [r for r in records if r["category"] == category]
        return [
            {
                "file_id": r["file_id"],
                "original_filename": r["original_filename"],
                "safe_filename": r["safe_filename"],
                "file_type": r["file_type"],
                "size_bytes": r["size_bytes"],
                "category": r["category"],
            }
            for r in records
        ]
