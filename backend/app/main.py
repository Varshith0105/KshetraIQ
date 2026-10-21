import logging
from typing import Any

from fastapi import Cookie, FastAPI, File, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.errors import validation_exception_handler
from app.models.registry import MODEL_REGISTRY, get_crop_recommender, get_model_health
from app.schemas.assessment import AssessmentResponse, FarmAssessmentRequest, ReportPreview
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.prediction import (
    ClimateScenarioRequest,
    ClimateScenarioResponse,
    CropYieldRequest,
    CropYieldResponse,
    IrrigationRequest,
    IrrigationResponse,
    MarketPriceRequest,
    MarketPriceResponse,
    ModelHealthResponse,
    PlantDiseaseResponse,
    SustainabilityRequest,
    SustainabilityResponse,
    WeatherRiskRequest,
    WeatherRiskResponse,
)
from app.schemas.upload import UploadResponse
from app.services.assessments import AssessmentService
from app.services.auth_service import (
    AuthTokenResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
    auth_service,
)
from app.services.chat_service import ChatService
from app.services.climate_recommender import ClimateScenarioService
from app.services.irrigation_service import irrigation_service
from app.services.market_price_service import market_price_service
from app.services.plant_disease_service import plant_disease_service
from app.services.sustainability_service import SustainabilityService
from app.services.upload_service import UploadService
from app.services.weather_risk_service import WeatherRiskService
from app.services.weather_service import WeatherService
from app.services.yield_recommender import CropYieldService

logger = logging.getLogger("kshetraiq.api")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="KshetraIQ API", version="0.4.0")
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    cors_kwargs = {
        "allow_origins": settings.cors_origins_list,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "OPTIONS", "HEAD", "PUT", "DELETE"],
        "allow_headers": ["*"],
        "allow_private_network": True,
    }
    if settings.cors_origin_regex:
        cors_kwargs["allow_origin_regex"] = settings.cors_origin_regex

    app.add_middleware(CORSMiddleware, **cors_kwargs)
    service = AssessmentService(settings)
    weather_service = WeatherService()
    chat_service = ChatService(settings)
    upload_service = UploadService(settings)

    # Initialize model adapters
    model_dir = settings.resolved_model_directory
    yield_service = CropYieldService(model_dir)
    climate_service = ClimateScenarioService(model_dir)
    sustainability_service = SustainabilityService(model_dir)
    weather_risk_service = WeatherRiskService(model_dir)

    @app.get("/health")
    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "kshetraiq-api",
            "version": "0.4.0",
            "environment": settings.environment,
            "storage_mode": service.storage_mode,
            "supabase_configured": str(settings.has_supabase).lower(),
            "llm_configured": str(settings.has_llm).lower(),
            "llm_provider": settings.effective_llm_provider or "none",
        }

    # ──────────── Model Registry & Health Endpoints ────────────

    @app.get("/api/v1/models")
    def list_models() -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for m in MODEL_REGISTRY:
            health_info = get_model_health(m.model_id, model_dir)
            result.append({
                "model_id": m.model_id,
                "display_name": m.display_name,
                "artifact": m.artifact,
                "contract_status": health_info.status if health_info else m.contract_status,
                "note": m.note,
                "endpoint": m.endpoint,
                "smoke_test_passed": health_info.smoke_test_passed if health_info else False,
                "limitations": health_info.limitations if health_info else None,
            })
        return result

    @app.get("/api/v1/models/{model_id}/health", response_model=ModelHealthResponse)
    def model_health(model_id: str) -> ModelHealthResponse:
        health_info = get_model_health(model_id, model_dir)
        if health_info is None:
            raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in registry")
        return health_info

    # ──────────── Prediction Endpoints ────────────

    @app.post("/api/v1/predictions/crop-yield", response_model=CropYieldResponse)
    def predict_crop_yield(payload: CropYieldRequest) -> CropYieldResponse:
        if not yield_service.is_ready:
            raise HTTPException(
                status_code=503,
                detail=f"Crop yield model unavailable: {yield_service.load_error or 'Artifact not loaded'}",
            )
        try:
            return yield_service.predict(payload)
        except Exception as e:
            logger.exception("Yield prediction execution failed")
            raise HTTPException(status_code=500, detail="Yield prediction execution failed. Please try again or contact support.")

    @app.post("/api/v1/predictions/climate-scenario", response_model=ClimateScenarioResponse)
    def predict_climate_scenario(payload: ClimateScenarioRequest) -> ClimateScenarioResponse:
        if not climate_service.is_ready:
            raise HTTPException(
                status_code=503,
                detail=f"Climate scenario model unavailable: {climate_service.load_error or 'Artifact not loaded'}",
            )
        try:
            return climate_service.predict(payload)
        except Exception as e:
            logger.exception("Climate scenario execution failed")
            raise HTTPException(status_code=500, detail="Climate scenario execution failed. Please try again or contact support.")

    @app.post("/api/v1/predictions/sustainability", response_model=SustainabilityResponse)
    def calculate_sustainability(payload: SustainabilityRequest) -> SustainabilityResponse:
        if not sustainability_service.is_ready:
            raise HTTPException(
                status_code=503,
                detail=f"Sustainability calculation service unavailable: {sustainability_service.load_error or 'Config not loaded'}",
            )
        try:
            return sustainability_service.calculate(payload)
        except Exception as e:
            logger.exception("Sustainability calculation failed")
            raise HTTPException(status_code=500, detail="Sustainability calculation failed. Please try again or contact support.")

    @app.post("/api/v1/predictions/weather-risk", response_model=WeatherRiskResponse)
    def predict_weather_risk(payload: WeatherRiskRequest) -> WeatherRiskResponse:
        if not weather_risk_service.is_ready:
            raise HTTPException(
                status_code=503,
                detail=f"Weather risk model unavailable: {weather_risk_service.load_error or 'Artifact not loaded'}",
            )
        try:
            return weather_risk_service.predict(payload)
        except Exception as e:
            logger.exception("Weather risk prediction failed")
            raise HTTPException(status_code=500, detail="Weather risk prediction failed. Please try again or contact support.")

    def _get_auth_user(
        authorization: str | None = None,
        session_cookie: str | None = None,
    ) -> UserProfileResponse | None:
        token = None
        if authorization:
            parts = authorization.strip().split()
            token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization.strip()
        elif session_cookie:
            token = session_cookie.strip()

        if not token:
            return None
        return auth_service.get_user_by_token(token)

    def _require_user(authorization: str | None, session_cookie: str | None) -> UserProfileResponse:
        user = _get_auth_user(authorization, session_cookie)
        if user is None:
            raise HTTPException(status_code=401, detail="Please sign in to access saved farm records.")
        return user

    async def _read_limited(file: UploadFile) -> bytes:
        """Read an upload in chunks, aborting as soon as the configured size limit is exceeded."""
        limit = settings.max_upload_bytes
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum size of {limit // (1024 * 1024)} MB.",
                )
            chunks.append(chunk)
        return b"".join(chunks)

    # ──────────── Authentication Endpoints ────────────

    @app.post("/api/v1/auth/register", response_model=AuthTokenResponse, status_code=201)
    def register_user(payload: UserRegisterRequest, response: Response) -> AuthTokenResponse:
        try:
            token_resp = auth_service.register(payload)
            response.set_cookie(
                key="kshetraiq_session",
                value=token_resp.token,
                httponly=True,
                samesite="lax",
                secure=(settings.environment == "production"),
                max_age=30 * 86400,
            )
            return token_resp
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.exception("Registration failed")
            raise HTTPException(status_code=500, detail="Registration failed. Please try again or contact support.")

    @app.post("/api/v1/auth/login", response_model=AuthTokenResponse)
    def login_user(payload: UserLoginRequest, response: Response) -> AuthTokenResponse:
        try:
            token_resp = auth_service.login(payload)
            response.set_cookie(
                key="kshetraiq_session",
                value=token_resp.token,
                httponly=True,
                samesite="lax",
                secure=(settings.environment == "production"),
                max_age=30 * 86400,
            )
            return token_resp
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            logger.exception("Login failed")
            raise HTTPException(status_code=500, detail="Login failed. Please try again or contact support.")

    @app.get("/api/v1/auth/me", response_model=UserProfileResponse)
    def get_current_user_profile(
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> UserProfileResponse:
        user = _get_auth_user(authorization, kshetraiq_session)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required or token expired.")
        return user

    @app.post("/api/v1/auth/logout")
    def logout_user(
        response: Response,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> dict[str, str]:
        token = None
        if authorization:
            parts = authorization.strip().split()
            token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization.strip()
        elif kshetraiq_session:
            token = kshetraiq_session.strip()

        if token:
            auth_service.logout(token)

        response.delete_cookie(
            key="kshetraiq_session",
            samesite="lax",
            secure=(settings.environment == "production"),
        )
        return {"status": "logged_out"}

    # ──────────── Market Price Prediction & Mandi Adapter ────────────

    @app.post("/api/v1/predictions/market-price", response_model=MarketPriceResponse)
    def predict_market_price(payload: MarketPriceRequest | None = None) -> MarketPriceResponse:
        req = payload or MarketPriceRequest()
        if not market_price_service.is_available():
            raise HTTPException(
                status_code=503,
                detail=f"Market price models unavailable: {market_price_service._load_error or 'Artifacts not loaded'}",
            )
        try:
            return MarketPriceResponse.model_validate(
                market_price_service.forecast_price(
                    commodity=req.commodity,
                    mandi=req.mandi,
                    target_date_str=req.target_date,
                    days_ahead=req.days_ahead,
                )
            )
        except Exception as e:
            logger.exception("Market price forecast failed")
            raise HTTPException(status_code=500, detail="Market price forecast failed. Please try again or contact support.")

    @app.get("/api/v1/market/prices")
    def get_market_observations(
        commodity: str = Query(default="Wheat"),
        mandi: str = Query(default="Varanasi(Grain)"),
    ) -> dict:
        return market_price_service.get_latest_observation(commodity=commodity, mandi=mandi)

    # ──────────── Plant Disease Vision Diagnostic ────────────

    @app.post("/api/v1/predictions/plant-disease", response_model=PlantDiseaseResponse)
    async def predict_plant_disease(file: UploadFile = File(...)) -> PlantDiseaseResponse:
        if not plant_disease_service.is_available():
            raise HTTPException(
                status_code=503,
                detail=f"Plant disease vision model unavailable: {plant_disease_service._load_error or 'Artifacts not loaded'}",
            )

        content_type = file.content_type or ""
        valid_types = {"image/jpeg", "image/png", "image/webp", "application/octet-stream"}
        if content_type not in valid_types and not any((file.filename or "").lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            raise HTTPException(
                status_code=400,
                detail="Invalid image format. Supported formats are JPEG, PNG, and WEBP.",
            )

        image_bytes = await _read_limited(file)

        try:
            result = plant_disease_service.predict_image(
                image_bytes=image_bytes,
                filename=file.filename or "uploaded_leaf.jpg",
            )
            return PlantDiseaseResponse.model_validate(result)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.exception("Disease inference failed")
            raise HTTPException(status_code=500, detail="Disease inference failed. Please try again or contact support.")

    # ──────────── Irrigation Advisory ────────────

    @app.post("/api/v1/predictions/irrigation", response_model=IrrigationResponse)
    def calculate_irrigation(payload: IrrigationRequest) -> IrrigationResponse:
        try:
            res = irrigation_service.calculate_irrigation(
                crop=payload.crop,
                crop_days=payload.crop_days,
                soil_moisture=payload.soil_moisture,
                soil_type=payload.soil_type,
                temperature=payload.temperature,
                rainfall_forecast_mm=payload.rainfall_forecast_mm,
                area_acres=payload.area_acres,
            )
            return IrrigationResponse.model_validate(res)
        except Exception as e:
            logger.exception("Irrigation advisory calculation failed")
            raise HTTPException(status_code=500, detail="Irrigation advisory calculation failed. Please try again or contact support.")

    # ──────────── Weather Lookup ────────────

    @app.get("/api/v1/weather/lookup")
    def lookup_weather(
        district: str = Query(min_length=2),
        state: str = Query(min_length=2),
        season: str = Query(default="kharif"),
    ) -> dict[str, str | float | None]:
        weather, source = weather_service.fetch_weather_for_location(district, state, season)
        if weather is None:
            return {
                "status": "unavailable",
                "source": source,
                "temperature_c": None,
                "humidity_percent": None,
                "rainfall_mm": None,
            }
        return {
            "status": "available",
            "source": source,
            "temperature_c": weather.temperature_c,
            "humidity_percent": weather.humidity_percent,
            "rainfall_mm": weather.rainfall_mm,
        }

    # ──────────── Assessment Orchestration Endpoints ────────────

    @app.post("/api/v1/assessments", response_model=AssessmentResponse, status_code=201)
    def create_assessment(
        payload: FarmAssessmentRequest,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> AssessmentResponse:
        user = _get_auth_user(authorization, kshetraiq_session)
        return service.create(payload, user_id=user.user_id if user else None)

    @app.get("/api/v1/assessments", response_model=list[AssessmentResponse])
    def list_assessments(
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> list[AssessmentResponse]:
        user = _require_user(authorization, kshetraiq_session)
        return service.list_all(user_id=user.user_id)

    @app.get("/api/v1/assessments/{assessment_id}", response_model=AssessmentResponse)
    def get_assessment(
        assessment_id: str,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> AssessmentResponse:
        user = _require_user(authorization, kshetraiq_session)
        record = service.get(assessment_id, user_id=user.user_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Assessment not found or access denied")
        return record

    @app.get("/api/v1/assessments/{assessment_id}/report/preview", response_model=ReportPreview)
    def preview_report(
        assessment_id: str,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> ReportPreview:
        user = _require_user(authorization, kshetraiq_session)
        preview = service.preview_report(assessment_id, user_id=user.user_id)
        if preview is None:
            raise HTTPException(status_code=404, detail="Assessment not found or access denied")
        return preview

    @app.post("/api/v1/assessments/{assessment_id}/report/confirm")
    def confirm_and_download_report(
        assessment_id: str,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> Response:
        user = _require_user(authorization, kshetraiq_session)
        pdf_bytes = service.generate_pdf(assessment_id, user_id=user.user_id)
        if pdf_bytes is None:
            raise HTTPException(status_code=404, detail="Assessment not found or access denied")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="KshetraIQ_Report_{assessment_id[:8]}.pdf"'},
        )

    # ──────────── Chatbot Endpoint ────────────

    @app.post("/api/v1/chat", response_model=ChatResponse)
    def chat(
        request: ChatRequest,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> ChatResponse:
        user = _get_auth_user(authorization, kshetraiq_session)
        assessment = None
        if request.assessment_id:
            assessment = service.get(request.assessment_id, user_id=user.user_id) if user else None
        else:
            assessment = service.get_latest(user_id=user.user_id) if user else None
        return chat_service.respond(request, assessment)

    # ──────────── File Upload Endpoints ────────────

    @app.post("/api/v1/uploads/{category}", response_model=UploadResponse)
    async def upload_file(
        category: str,
        file: UploadFile = File(...),
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> UploadResponse:
        user = _require_user(authorization, kshetraiq_session)
        if category not in {"soil_report", "field_photo", "crop_photo"}:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category '{category}'. Must be 'soil_report', 'field_photo', or 'crop_photo'.",
            )

        content = await _read_limited(file)
        try:
            return upload_service.validate_and_save(
                file_content=content,
                original_filename=file.filename or "unknown",
                content_type=file.content_type,
                category=category,
                user_id=user.user_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/v1/uploads")
    def list_uploads(
        category: str | None = Query(default=None),
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> list[dict]:
        user = _require_user(authorization, kshetraiq_session)
        return upload_service.list_files(category=category, user_id=user.user_id)

    @app.delete("/api/v1/uploads/{file_id}")
    def delete_upload(
        file_id: str,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> dict[str, str]:
        user = _require_user(authorization, kshetraiq_session)
        if upload_service.delete_file(file_id, user_id=user.user_id):
            return {"status": "deleted", "file_id": file_id}
        raise HTTPException(status_code=404, detail="File not found or access denied")

    return app


app = create_app()
