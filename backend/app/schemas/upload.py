"""Pydantic schemas for file upload responses."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    file_id: str
    original_filename: str
    safe_filename: str
    file_type: str
    size_bytes: int
    category: str  # "soil_report" | "field_photo" | "crop_photo"
    storage: str  # "local_temp" | "supabase"
    message: str
