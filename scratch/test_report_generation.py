import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import get_settings
from app.services.storage import SQLiteStorage
from app.services.report_service import ReportService

settings = get_settings()
storage = SQLiteStorage(settings.resolved_sqlite_db_path)
all_assessments = storage.list_all()

print(f"Total assessments found: {len(all_assessments)}")
if not all_assessments:
    print("No assessments found in database")
    sys.exit(0)

# Pick an assessment that has completed results
completed = [
    a for a in all_assessments
    if any(r.model_id == "crop-recommendation-v1" and r.prediction is not None for r in (a.results or []))
]
print(f"Completed assessments found: {len(completed)}")
target = completed[0] if completed else all_assessments[0]

report_svc = ReportService()
pdf_bytes = report_svc.generate_pdf(target)
print(f"Generated PDF successfully! Size: {len(pdf_bytes)} bytes")
assert len(pdf_bytes) > 1000
assert pdf_bytes.startswith(b"%PDF")
print("PDF HEADER & SIZE VERIFIED!")
