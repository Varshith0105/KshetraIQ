from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import Settings
from app.models.registry import assessment_model_status
from app.schemas.assessment import (
    AssessmentResponse,
    FarmAssessmentRequest,
    ReportPreview,
    WeatherObservations,
)
from app.services.advisor_service import AdvisorService
from app.services.report_service import ReportService
from app.services.storage import InMemoryStorage, SQLiteStorage, StorageBackend
from app.services.weather_service import WeatherService


class AssessmentService:
    """Assessment orchestration service connecting verified inference, persistence, and reports."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # NOTE: no Supabase client is implemented. Previously, setting SUPABASE_* env vars silently
        # switched to in-memory storage while reporting "supabase", so data was lost on restart.
        # SQLite is now always used unless STORAGE_BACKEND=memory is explicitly requested.
        if settings.storage_backend != "memory":
            self._storage: StorageBackend = SQLiteStorage(settings.resolved_sqlite_db_path)
            self._storage_mode = "sqlite_local"
        else:
            self._storage = InMemoryStorage()
            self._storage_mode = "in_memory"

        self._weather_service = WeatherService()
        self._advisor_service = AdvisorService(settings)
        self._report_service = ReportService()

    @property
    def storage_mode(self) -> str:
        return self._storage_mode

    def create(self, payload: FarmAssessmentRequest, user_id: str | None = None) -> AssessmentResponse:
        weather_source = "not_provided"
        actual_payload = payload

        # Sourcing weather observations if not provided or incomplete
        w = payload.weather
        has_full_weather = (
            w is not None
            and w.temperature_c is not None
            and w.humidity_percent is not None
            and w.rainfall_mm is not None
        )

        if has_full_weather:
            weather_source = "farmer_input"
        else:
            fetched_weather, fetch_status = self._weather_service.fetch_weather_for_location(
                district=payload.district,
                state=payload.state,
                season=payload.season,
            )
            if fetched_weather is not None:
                merged_temp = w.temperature_c if (w and w.temperature_c is not None) else fetched_weather.temperature_c
                merged_hum = w.humidity_percent if (w and w.humidity_percent is not None) else fetched_weather.humidity_percent
                merged_rain = w.rainfall_mm if (w and w.rainfall_mm is not None) else fetched_weather.rainfall_mm
                merged_weather = WeatherObservations(
                    temperature_c=merged_temp,
                    humidity_percent=merged_hum,
                    rainfall_mm=merged_rain,
                )
                actual_payload = payload.model_copy(update={"weather": merged_weather})
                weather_source = "open_meteo_live"
            else:
                weather_source = f"unresolved ({fetch_status})"

        results = assessment_model_status(actual_payload, self._settings.resolved_model_directory)

        # Extract verified crop prediction if available
        crop_model = next((r for r in results if r.model_id == "crop-recommendation-v1"), None)
        prediction = crop_model.prediction if crop_model else None

        advisor = self._advisor_service.generate_advice(actual_payload, prediction)

        limitations = []
        if self._storage_mode == "sqlite_local":
            limitations.append("Local SQLite database persistence active. Records survive server restarts.")
        elif self._storage_mode == "supabase":
            limitations.append("Supabase cloud database storage active.")
        else:
            limitations.append("In-memory storage active. Records will be lost upon server restart.")

        record = AssessmentResponse(
            assessment_id=str(uuid4()),
            created_at=datetime.now(UTC),
            input=actual_payload,
            weather_source=weather_source,
            results=results,
            advisor=advisor,
            assumptions=[
                "No laboratory soil values are inferred from photos or documents.",
                "Crop recommendation is computed strictly using the verified Random Forest classifier trained on 22 agricultural crop classes.",
            ],
            limitations=limitations,
            storage=self._storage_mode,
        )
        self._storage.save(record, user_id=user_id)
        return record

    def get(self, assessment_id: str, user_id: str | None = None) -> AssessmentResponse | None:
        return self._storage.get(assessment_id, user_id=user_id)

    def list_all(self, user_id: str | None = None) -> list[AssessmentResponse]:
        """Return all assessments, optionally filtered by user ID, most recent first."""
        return self._storage.list_all(user_id=user_id)

    def get_latest(self, user_id: str | None = None) -> AssessmentResponse | None:
        """Return the most recently created assessment, or None."""
        return self._storage.get_latest(user_id=user_id)

    def preview_report(self, assessment_id: str, user_id: str | None = None) -> ReportPreview | None:
        record = self.get(assessment_id, user_id=user_id)
        if not record:
            return None
        return self._report_service.create_preview(record)

    def generate_pdf(self, assessment_id: str, user_id: str | None = None) -> bytes | None:
        record = self.get(assessment_id, user_id=user_id)
        if not record:
            return None
        return self._report_service.generate_pdf(record)
