from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from app.core.config import Settings
from app.services.intelligence_service import IntelligenceService


def _png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (80, 60), color=(32, 130, 54)).save(output, format="PNG")
    return output.getvalue()


def test_plant_manifest_preserves_original_and_defers_empty_model_list(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        sqlite_db_path=tmp_path / "intelligence.db",
        upload_dir=tmp_path / "uploads",
    )
    service = IntelligenceService(settings)

    manifest = service.create_plant(_png_bytes(), "leaf.png", "farmer-a", selected=[])

    assert manifest["workflow_type"] == "plant"
    assert Path(manifest["original_image"]).read_bytes() == _png_bytes()
    assert all(item["status"] == "NOT_RUN" for item in manifest["executed_models"].values())
    assert service.get(manifest["analysis_id"], "farmer-b") is None


def test_plant_pdf_contains_stored_original_asset(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        sqlite_db_path=tmp_path / "intelligence.db",
        upload_dir=tmp_path / "uploads",
    )
    service = IntelligenceService(settings)
    manifest = service.create_plant(_png_bytes(), "leaf.png", "farmer-a", selected=[])

    report, content = service.generate_report(manifest["analysis_id"], "farmer-a")

    assert content.startswith(b"%PDF")
    assert Path(report["path"]).is_file()
    reader = PdfReader(io.BytesIO(content))
    assert any(
        page.get("/Resources", {}).get("/XObject")
        for page in reader.pages
    ), "The saved original image must be embedded in the generated PDF."
    reopened = service.get(manifest["analysis_id"], "farmer-a")
    assert reopened is not None
    assert reopened["reports"][-1]["path"] == report["path"]
