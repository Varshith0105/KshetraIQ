import logging
from typing import Any

from fastapi import Cookie, FastAPI, File, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.errors import validation_exception_handler
from app.models.registry import MODEL_REGISTRY, get_crop_recommender, get_model_health
from app.schemas.assessment import AssessmentResponse, FarmAssessmentRequest, ReportPreview, SoilHealthScoreRequest
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.prediction import (
    ClimateScenarioRequest,
    ClimateScenarioResponse,
    CropYieldRequest,
    CropYieldResponse,
    IrrigationRequest,
    IrrigationResponse,
    MarketCommoditiesResponse,
    MarketPriceRequest,
    MarketPriceResponse,
    ModelHealthResponse,
    PlantDiseaseResponse,
    SustainabilityRequest,
    SustainabilityResponse,
    WeatherRiskRequest,
    WeatherRiskResponse,
)
from app.schemas.chat import (
    ChatMessageItem,
    ChatRequest,
    ChatResponse,
    ConversationSummary,
    UserActivityPayload,
    UserActivityResponse,
)
from app.schemas.upload import UploadResponse
from app.services.assessments import AssessmentService
from app.services.auth_service import (
    AuthTokenResponse,
    FarmProfilePayload,
    FarmProfileResponse,
    GoogleAuthCallbackRequest,
    GoogleAuthUrlResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    PhoneOtpSendRequest,
    PhoneOtpSendResponse,
    PhoneOtpVerifyRequest,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
    AuthService,
)
from app.services.chat_service import ChatService
from app.services.climate_recommender import ClimateScenarioService
from app.services.irrigation_service import irrigation_service
from app.services.market_price_service import market_price_service
from app.services.plant_disease_service import plant_disease_service
from app.services.sustainability_service import SustainabilityService
from app.services.upload_service import UploadService
from app.services.weather_risk_service import WeatherRiskService

logger = logging.getLogger("kshetraiq.api")
from app.services.activity_service import ActivityService
from app.services.conversation_service import conversation_service
from app.services.langgraph_orchestrator import SUGGESTIONS_BY_SCREEN
from app.services.prediction_history_service import PredictionHistoryService
from app.services.soil_health_service import soil_health_service
from app.services.weather_service import WeatherService
from app.services.yield_recommender import CropYieldService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    # Keep each application instance bound to its own configured database.
    # This is essential for isolated tests and avoids cross-environment sessions.
    auth_service = AuthService(settings=settings)
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
    # Keep prediction records in the same database as the application instance.
    # This matters for test/tenant instances as well as the production SQLite file.
    prediction_history_service = PredictionHistoryService(settings=settings)
    activity_service = ActivityService(settings=settings)
    weather_service = WeatherService()
    chat_service = ChatService(settings)
    upload_service = UploadService(settings)

    # Initialize model adapters
    model_dir = settings.resolved_model_directory
    yield_service = CropYieldService(model_dir)
    climate_service = ClimateScenarioService(model_dir)
    sustainability_service = SustainabilityService(model_dir)
    weather_risk_service = WeatherRiskService(model_dir)

    # Run one-time prediction history backfill from existing assessments (in non-test environments)
    if settings.environment != "test":
        try:
            migrated = prediction_history_service.migrate_from_existing_assessments()
            if migrated:
                logger.info("Prediction history: %d records available", migrated)
        except Exception as e:
            logger.debug("Prediction history migration skipped: %s", e)

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
                "model_type": m.model_type,
                "artifact": m.artifact,
                "active_artifact": health_info.active_artifact if health_info else m.artifact,
                "contract_status": health_info.status if health_info else m.contract_status,
                "readiness_status": health_info.readiness_status if health_info else "VERIFIED",
                "prediction_status": health_info.prediction_status if health_info else "NOT RUN",
                "runtime_verification_result": health_info.runtime_verification_result if health_info else "passed",
                "supported_inputs": health_info.required_inputs if health_info else list(m.required_fields),
                "missing_input_explanation": health_info.missing_input_explanation if health_info else None,
                "last_verified_at": health_info.last_verified_at if health_info else None,
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
    def predict_crop_yield(
        payload: CropYieldRequest,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> CropYieldResponse:
        if not yield_service.is_ready:
            raise HTTPException(
                status_code=503,
                detail=f"Crop yield model unavailable: {yield_service.load_error or 'Artifact not loaded'}",
            )
        try:
            response = yield_service.predict(payload)
            user = _get_auth_user(authorization, kshetraiq_session)
            prediction_history_service.record_prediction(
                model_id="crop-yield-v1", input_features=payload.model_dump(),
                prediction_output=response.model_dump(), user_id=user.user_id if user else None,
                model_version="v1", model_artifact="crop_yield_prediction_model.pkl",
                units="tonnes/hectare", prediction_methodology="Random Forest regressor",
                data_source="Farmer-supplied yield parameters",
            )
            return response
        except Exception:
            raise HTTPException(status_code=500, detail="Yield prediction execution failed. Please try again.")

    @app.post("/api/v1/predictions/climate-scenario", response_model=ClimateScenarioResponse)
    def predict_climate_scenario(
        payload: ClimateScenarioRequest,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> ClimateScenarioResponse:
        if not climate_service.is_ready:
            raise HTTPException(
                status_code=503,
                detail=f"Climate scenario model unavailable: {climate_service.load_error or 'Artifact not loaded'}",
            )
        try:
            response = climate_service.predict(payload)
            user = _get_auth_user(authorization, kshetraiq_session)
            prediction_history_service.record_prediction(
                model_id="climate-scenario-v1", input_features=payload.model_dump(),
                prediction_output=response.model_dump(), user_id=user.user_id if user else None,
                model_version="v1", model_artifact="climate_change_yield_model.pkl",
                units="tonnes/hectare", prediction_methodology="Climate scenario simulation",
                data_source="Farmer-supplied climate parameters",
            )
            return response
        except Exception:
            raise HTTPException(status_code=500, detail="Climate scenario execution failed. Please try again.")

    @app.post("/api/v1/predictions/sustainability", response_model=SustainabilityResponse)
    def calculate_sustainability(
        payload: SustainabilityRequest,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> SustainabilityResponse:
        if not sustainability_service.is_ready:
            raise HTTPException(
                status_code=503,
                detail=f"Sustainability calculation service unavailable: {sustainability_service.load_error or 'Config not loaded'}",
            )
        try:
            response = sustainability_service.calculate(payload)
            user = _get_auth_user(authorization, kshetraiq_session)
            prediction_history_service.record_prediction(
                model_id="sustainability-v1", input_features=payload.model_dump(),
                prediction_output=response.model_dump(), user_id=user.user_id if user else None,
                model_version="v1", model_artifact="sustainability_score_config.pkl",
                units="score / 100", prediction_methodology="ICAR agronomic sustainability index",
                data_source="Farmer-supplied sustainability parameters",
            )
            return response
        except Exception:
            raise HTTPException(status_code=500, detail="Sustainability calculation failed. Please try again.")

    @app.post("/api/v1/predictions/weather-risk", response_model=WeatherRiskResponse)
    def predict_weather_risk(
        payload: WeatherRiskRequest,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> WeatherRiskResponse:
        if not weather_risk_service.is_ready:
            raise HTTPException(
                status_code=503,
                detail=f"Weather risk model unavailable: {weather_risk_service.load_error or 'Artifact not loaded'}",
            )
        try:
            response = weather_risk_service.predict(payload)
            user = _get_auth_user(authorization, kshetraiq_session)
            prediction_history_service.record_prediction(
                model_id="weather-risk-v1", input_features=payload.model_dump(),
                prediction_output=response.model_dump(), user_id=user.user_id if user else None,
                model_version="v1", model_artifact="weather_risk_xgboost_model.pkl",
                prediction_methodology="XGBoost weather-risk classifier",
                data_source="Farmer-supplied weather and location parameters",
            )
            return response
        except Exception:
            raise HTTPException(status_code=500, detail="Weather risk prediction failed. Please try again.")

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
        """Read an upload in bounded chunks to avoid unbounded memory use."""
        chunks: list[bytes] = []
        total = 0
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > settings.max_upload_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum size of {settings.max_upload_bytes // (1024 * 1024)} MB.",
                )
            chunks.append(chunk)
        return b"".join(chunks)

    # ──────────── Authentication Endpoints ────────────

    @app.post("/api/v1/auth/register", response_model=AuthTokenResponse, status_code=201)
    def register_user(payload: UserRegisterRequest, response: Response) -> AuthTokenResponse:
        try:
            token_resp = auth_service.register(payload)
            cookie_max_age = (settings.persistent_session_days * 86400) if token_resp.remember_me else None
            response.set_cookie(
                key="kshetraiq_session",
                value=token_resp.token,
                httponly=True,
                samesite="lax",
                secure=(settings.environment == "production"),
                max_age=cookie_max_age,
            )
            return token_resp
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Registration internal error: %s", e)
            raise HTTPException(status_code=500, detail="Registration failed. Please check your details and try again.")

    @app.post("/api/v1/auth/login", response_model=AuthTokenResponse)
    def login_user(payload: UserLoginRequest, response: Response) -> AuthTokenResponse:
        try:
            token_resp = auth_service.login(payload)
            cookie_max_age = (settings.persistent_session_days * 86400) if token_resp.remember_me else None
            response.set_cookie(
                key="kshetraiq_session",
                value=token_resp.token,
                httponly=True,
                samesite="lax",
                secure=(settings.environment == "production"),
                max_age=cookie_max_age,
            )
            return token_resp
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            logger.error("Login error: %s", e)
            raise HTTPException(status_code=500, detail="Unable to sign in. Check your credentials and try again.")

    @app.get("/api/v1/auth/me", response_model=UserProfileResponse)
    def get_current_user_profile(
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> UserProfileResponse:
        user = _get_auth_user(authorization, kshetraiq_session)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required or token expired.")
        return user

    @app.get("/api/v1/farm-profile", response_model=FarmProfileResponse)
    def get_farm_profile(
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> FarmProfileResponse:
        user = _require_user(authorization, kshetraiq_session)
        profile = auth_service.get_farm_profile(user.user_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="No farm profile has been saved yet.")
        return profile

    @app.put("/api/v1/farm-profile", response_model=FarmProfileResponse)
    def save_farm_profile(
        payload: FarmProfilePayload,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> FarmProfileResponse:
        user = _require_user(authorization, kshetraiq_session)
        return auth_service.save_farm_profile(user.user_id, payload)

    # ──────────── Location Endpoints (All 28 States & 8 UTs) ────────────

    @app.get("/api/v1/locations/states")
    def get_supported_states() -> list[str]:
        from app.data.india_locations import get_states
        return get_states()

    @app.get("/api/v1/locations/districts")
    def get_supported_districts(state: str = Query(...)) -> dict[str, Any]:
        from app.data.india_locations import get_districts
        districts = get_districts(state)
        if not districts:
            raise HTTPException(
                status_code=404,
                detail=f"State '{state}' not found. Please provide a valid Indian state or Union Territory.",
            )
        return {"state": state, "districts": districts}

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

    @app.post("/api/v1/auth/password-reset/request", response_model=PasswordResetRequestResponse)
    def request_password_reset(payload: PasswordResetRequest, request: Request) -> PasswordResetRequestResponse:
        # Keep account enumeration impossible: the same confirmation is returned in every case.
        frontend_origin = request.headers.get("origin") or settings.google_redirect_uri.rsplit("/auth/callback", 1)[0]
        try:
            auth_service.request_password_reset(payload, frontend_origin)
        except Exception as exc:
            logger.error("Password reset delivery failed: %s", exc)
        return PasswordResetRequestResponse(
            message="If an account exists for that email, password-reset instructions have been sent."
        )

    @app.post("/api/v1/auth/password-reset/confirm")
    def confirm_password_reset(payload: PasswordResetConfirmRequest) -> dict[str, str]:
        try:
            auth_service.reset_password(payload)
            return {"status": "password_reset"}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/v1/auth/otp/send", response_model=PhoneOtpSendResponse)
    def send_phone_otp(payload: PhoneOtpSendRequest) -> PhoneOtpSendResponse:
        try:
            return auth_service.send_phone_otp(payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("OTP send error: %s", e)
            raise HTTPException(status_code=500, detail="OTP dispatch failed. Please try again.")

    @app.post("/api/v1/auth/otp/verify", response_model=AuthTokenResponse)
    def verify_phone_otp(payload: PhoneOtpVerifyRequest, response: Response) -> AuthTokenResponse:
        try:
            token_resp = auth_service.verify_phone_otp(payload)
            cookie_max_age = (settings.persistent_session_days * 86400) if token_resp.remember_me else None
            response.set_cookie(
                key="kshetraiq_session",
                value=token_resp.token,
                httponly=True,
                samesite="lax",
                secure=(settings.environment == "production"),
                max_age=cookie_max_age,
            )
            return token_resp
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("OTP verification error: %s", e)
            raise HTTPException(status_code=500, detail="OTP verification failed. Please try again.")

    @app.get("/api/v1/auth/google/url", response_model=GoogleAuthUrlResponse)
    def get_google_auth_url(redirect_uri: str | None = Query(default=None)) -> GoogleAuthUrlResponse:
        return auth_service.get_google_auth_url(redirect_uri=redirect_uri)

    @app.post("/api/v1/auth/google/callback", response_model=AuthTokenResponse)
    def google_auth_callback(payload: GoogleAuthCallbackRequest, response: Response) -> AuthTokenResponse:
        try:
            token_resp = auth_service.authenticate_with_google(
                code=payload.code,
                redirect_uri=payload.redirect_uri,
                state=payload.state,
                remember_me=payload.remember_me,
            )
            cookie_max_age = (settings.persistent_session_days * 86400) if token_resp.remember_me else None
            response.set_cookie(
                key="kshetraiq_session",
                value=token_resp.token,
                httponly=True,
                samesite="lax",
                secure=(settings.environment == "production"),
                max_age=cookie_max_age,
            )
            return token_resp
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Google auth callback error: %s", e)
            raise HTTPException(status_code=500, detail="Google authentication could not be completed. Please try again.")

    # ──────────── Market Price Prediction & Mandi Adapter ────────────

    @app.post("/api/v1/predictions/market-price", response_model=MarketPriceResponse)
    def predict_market_price(
        payload: MarketPriceRequest,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> MarketPriceResponse:
        req = payload
        if not market_price_service.is_available():
            raise HTTPException(
                status_code=503,
                detail=f"Market price models unavailable: {market_price_service._load_error or 'Artifacts not loaded'}",
            )
        try:
            result_data = market_price_service.forecast_price(
                commodity=req.commodity,
                mandi=req.mandi,
                state=req.state,
                district=req.district,
                variety=req.variety,
                target_date_str=req.target_date,
                days_ahead=req.days_ahead,
            )
            response = MarketPriceResponse.model_validate(result_data)

            # Record prediction history
            try:
                user = _get_auth_user(authorization, kshetraiq_session)
                prediction_history_service.record_prediction(
                    model_id="market-price-v2",
                    input_features={
                        "commodity": req.commodity,
                        "mandi": req.mandi,
                        "state": req.state,
                        "district": req.district,
                        "variety": req.variety,
                        "days_ahead": req.days_ahead,
                    },
                    prediction_output=result_data if isinstance(result_data, dict) else response.model_dump(),
                    user_id=user.user_id if user else None,
                    model_version="v2",
                    model_artifact="market_lgb_model.txt",
                    confidence=None,
                    units="INR/quintal",
                    prediction_methodology=response.forecast_method_label,
                    data_source=response.data_source or "AGMARKNET",
                )
            except Exception as rec_err:
                logger.debug("Failed recording market prediction: %s", rec_err)

            return response
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.exception("Market price forecast error: %s", e)
            raise HTTPException(status_code=500, detail=f"Market price forecast failed: {e}")

    @app.get("/api/v1/market/prices")
    def get_market_observations(
        commodity: str = Query(default="Wheat"),
        mandi: str = Query(default="Varanasi(Grain)"),
        state: str | None = Query(default=None),
        district: str | None = Query(default=None),
    ) -> dict:
        return market_price_service.get_latest_observation(
            commodity=commodity, mandi=mandi, state=state, district=district
        )

    @app.get("/api/v1/market/commodities", response_model=MarketCommoditiesResponse)
    def get_supported_market_commodities() -> MarketCommoditiesResponse:
        """Returns the verified catalog of supported commodities and APMC mandis."""
        return MarketCommoditiesResponse.model_validate(
            market_price_service.get_supported_catalog()
        )

    # ──────────── Plant Disease Vision Diagnostic ────────────

    @app.post("/api/v1/predictions/plant-disease", response_model=PlantDiseaseResponse)
    async def predict_plant_disease(
        file: UploadFile = File(...),
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> PlantDiseaseResponse:
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
            response = PlantDiseaseResponse.model_validate(result)

            # Record prediction history
            try:
                user = _get_auth_user(authorization, kshetraiq_session)
                prediction_history_service.record_prediction(
                    model_id="plant-disease-v1",
                    input_features={
                        "filename": file.filename,
                        "content_type": content_type,
                        "image_size_bytes": len(image_bytes),
                    },
                    prediction_output=result if isinstance(result, dict) else response.model_dump(),
                    user_id=user.user_id if user else None,
                    model_version="v1",
                    model_artifact="plant_disease_model.pth",
                    confidence=response.confidence if hasattr(response, "confidence") else None,
                    prediction_methodology="ResNet CNN Image Classifier",
                    data_source="User uploaded leaf image",
                )
            except Exception as rec_err:
                logger.debug("Failed recording disease prediction: %s", rec_err)

            return response
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            raise HTTPException(status_code=500, detail="Disease inference failed. Please try again.")

    # ──────────── Irrigation Advisory ────────────

    @app.post("/api/v1/predictions/irrigation", response_model=IrrigationResponse)
    def calculate_irrigation(
        payload: IrrigationRequest,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> IrrigationResponse:
        try:
            res = irrigation_service.calculate_irrigation(
                crop=payload.crop,
                crop_days=payload.crop_days,
                soil_moisture=payload.soil_moisture,
                soil_type=payload.soil_type,
                temperature=payload.temperature,
                rainfall_forecast_mm=payload.rainfall_forecast_mm,
                area_acres=payload.area_acres,
                soil_temperature=payload.soil_temperature,
                humidity=payload.humidity,
                is_sensor_data=payload.is_sensor_data,
                force_deterministic=payload.force_deterministic,
            )
            response = IrrigationResponse.model_validate(res)

            # Record prediction history
            try:
                user = _get_auth_user(authorization, kshetraiq_session)
                prediction_history_service.record_prediction(
                    model_id="irrigation-rl-v1",
                    input_features={
                        "crop": payload.crop,
                        "crop_days": payload.crop_days,
                        "soil_moisture": payload.soil_moisture,
                        "soil_type": payload.soil_type,
                        "temperature": payload.temperature,
                        "rainfall_forecast_mm": payload.rainfall_forecast_mm,
                        "area_acres": payload.area_acres,
                    },
                    prediction_output=res if isinstance(res, dict) else response.model_dump(),
                    user_id=user.user_id if user else None,
                    model_version="v1",
                    model_artifact="irrigation_rl_policy.zip",
                    prediction_methodology="RL PPO Policy + ICAR Water Budgeting",
                    data_source="User irrigation parameters",
                )
            except Exception as rec_err:
                logger.debug("Failed recording irrigation prediction: %s", rec_err)

            return response
        except Exception:
            raise HTTPException(status_code=500, detail="Irrigation advisory calculation failed. Please try again.")

    # ──────────── Weather Lookup ────────────

    @app.get("/api/v1/weather/lookup")
    def lookup_weather(
        district: str = Query(min_length=2),
        state: str = Query(min_length=2),
        season: str = Query(default="kharif"),
    ) -> dict[str, str | float | None]:
        weather, source = weather_service.fetch_weather_for_location(district, state, season)
        if weather is None:
            hint = (
                "Open-Meteo rate limit reached. Try again in a few minutes."
                if source == "rate_limited"
                else "Live weather data is currently unavailable. Please retry or enter verified field observations manually."
            )
            return {
                "status": "unavailable",
                "source": source,
                "hint": hint,
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

    @app.get("/api/v1/weather/forecast")
    def get_7day_forecast(
        district: str = Query(min_length=2),
        state: str = Query(min_length=2),
    ) -> dict:
        """Return full 7-day daily forecast from Open-Meteo for the WeatherView panel."""
        result = weather_service.fetch_7day_forecast(district, state)
        if result is None:
            return {
                "status": "unavailable",
                "hint": "Live 7-day forecast is currently unavailable for this location.",
                "current": None,
                "daily": None,
            }
        return {"status": "available", **result}

    # ──────────── Assessment Orchestration Endpoints ────────────

    @app.post("/api/v1/assessments", response_model=AssessmentResponse, status_code=201)
    def create_assessment(
        payload: FarmAssessmentRequest,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> AssessmentResponse:
        user = _require_user(authorization, kshetraiq_session)
        record = service.create(payload, user_id=user.user_id)

        # A verified assessment already contains a real crop inference. Persist
        # that exact response once; never recompute it while answering history.
        crop_result = next(
            (item for item in record.results
             if item.model_id == "crop-recommendation-v1" and item.prediction is not None),
            None,
        )
        if crop_result and crop_result.prediction:
            crop_prediction = crop_result.prediction
            prediction_history_service.record_prediction(
                model_id="crop-recommendation-v1",
                assessment_id=record.assessment_id,
                user_id=user.user_id,
                model_version="v1",
                model_artifact=crop_prediction.artifact_name,
                input_features={
                    "nitrogen_kg_ha": record.input.soil.nitrogen_kg_ha,
                    "phosphorus_kg_ha": record.input.soil.phosphorus_kg_ha,
                    "potassium_kg_ha": record.input.soil.potassium_kg_ha,
                    "ph": record.input.soil.ph,
                    "temperature_c": record.input.weather.temperature_c if record.input.weather else None,
                    "humidity_percent": record.input.weather.humidity_percent if record.input.weather else None,
                    "rainfall_mm": record.input.weather.rainfall_mm if record.input.weather else None,
                    "season": record.input.season,
                    "district": record.input.district,
                    "state": record.input.state,
                },
                prediction_output=crop_prediction.model_dump(),
                confidence=crop_prediction.confidence,
                units="probability",
                prediction_methodology=crop_prediction.algorithm,
                data_source=record.weather_source,
                provenance={"assessment_created_at": record.created_at.isoformat()},
            )
        activity_service.log_activity(
            user_id=user.user_id,
            action="assessment_completed",
            entity_type="assessment",
            entity_id=record.assessment_id,
            metadata={"weather_source": record.weather_source, "farm_name": record.input.farm_name},
        )
        return record

    @app.get("/api/v1/assessments", response_model=list[AssessmentResponse])
    def list_assessments(
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> list[AssessmentResponse]:
        user = _require_user(authorization, kshetraiq_session)
        return service.list_all(user_id=user.user_id)

    # ──────────── Assessment Summary Endpoint (must precede /{assessment_id}) ────────────

    @app.get("/api/v1/assessments/summary")
    def get_assessment_summary(
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> dict[str, Any]:
        """Return a summary of the user's assessments: total, completed, incomplete, latest."""
        user = _require_user(authorization, kshetraiq_session)
        all_assessments = service.list_all(user_id=user.user_id)

        completed = []
        incomplete = []
        for a in all_assessments:
            has_crop_rec = any(
                r.model_id == "crop-recommendation-v1" and r.prediction is not None
                for r in (a.results or [])
            )
            if has_crop_rec:
                completed.append(a)
            else:
                incomplete.append(a)

        latest_completed = completed[0] if completed else None
        previous_completed = completed[1] if len(completed) > 1 else None

        return {
            "total": len(all_assessments),
            "completed": len(completed),
            "incomplete": len(incomplete),
            "latest_completed": latest_completed.model_dump() if latest_completed else None,
            "previous_completed": previous_completed.model_dump() if previous_completed else None,
        }

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
        activity_service.log_activity(
            user_id=user.user_id, action="pdf_report_generated", entity_type="assessment",
            entity_id=assessment_id,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="KshetraIQ_Report_{assessment_id[:8]}.pdf"'},
        )

    # ──────────── Context-Aware Agricultural AI Assistant ────────────

    @app.post("/api/v1/chat", response_model=ChatResponse)
    def chat(
        request: ChatRequest,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> ChatResponse:
        user = _get_auth_user(authorization, kshetraiq_session)
        user_id = user.user_id if user else None
        assessment = None
        if request.assessment_id:
            assessment = service.get(request.assessment_id, user_id=user_id)
        else:
            assessment = service.get_latest(user_id=user_id)
        past_assessments = service.list_all(user_id=user_id) if user_id else []
        return chat_service.respond(
            request,
            assessment=assessment,
            user_id=user_id,
            past_assessments=past_assessments,
        )

    @app.get("/api/v1/chat/suggestions")
    def get_chat_suggestions(
        screen_id: str = Query(default="dashboard"),
        language: str = Query(default="en"),
    ) -> dict[str, Any]:
        """Return dynamic, screen-aware suggested questions for the farmer."""
        norm_screen = screen_id.lower().strip()
        screen_dict = SUGGESTIONS_BY_SCREEN.get(norm_screen, SUGGESTIONS_BY_SCREEN["dashboard"])
        suggestions = screen_dict.get(language, screen_dict["en"])
        return {
            "screen_id": norm_screen,
            "language": language,
            "suggestions": suggestions,
        }

    @app.get("/api/v1/chat/conversations", response_model=list[ConversationSummary])
    def list_conversations(
        limit: int = Query(default=15, ge=1, le=50),
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> list[ConversationSummary]:
        user = _require_user(authorization, kshetraiq_session)
        return conversation_service.list_conversations(user_id=user.user_id, limit=limit)

    @app.get("/api/v1/chat/conversations/{conversation_id}", response_model=list[ChatMessageItem])
    def get_conversation_history(
        conversation_id: str,
        limit: int = Query(default=30, ge=1, le=100),
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> list[ChatMessageItem]:
        user = _require_user(authorization, kshetraiq_session)
        messages = conversation_service.get_messages(
            conversation_id=conversation_id,
            user_id=user.user_id,
            limit=limit,
        )
        return messages

    @app.delete("/api/v1/chat/conversations/{conversation_id}")
    def delete_conversation(
        conversation_id: str,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> dict[str, str]:
        user = _require_user(authorization, kshetraiq_session)
        if conversation_service.delete_conversation(conversation_id, user_id=user.user_id):
            return {"status": "deleted", "conversation_id": conversation_id}
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")

    # ──────────── Prediction History Endpoints ────────────

    @app.get("/api/v1/predictions/history")
    def get_prediction_history(
        model_id: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> list[dict[str, Any]]:
        """Return the authenticated user's ML prediction history, newest first."""
        user = _require_user(authorization, kshetraiq_session)
        records = prediction_history_service.list_predictions(
            user_id=user.user_id, model_id=model_id, limit=limit
        )
        return [r.to_dict() for r in records]

    @app.get("/api/v1/predictions/history/{prediction_id}")
    def get_single_prediction(
        prediction_id: str,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> dict[str, Any]:
        """Fetch a single prediction record with user authorization."""
        user = _require_user(authorization, kshetraiq_session)
        record = prediction_history_service.get_prediction(prediction_id, user_id=user.user_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Prediction not found or access denied")
        return record.to_dict()

    @app.get("/api/v1/predictions/summary")
    def get_prediction_summary(
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> dict[str, Any]:
        """Return a summary of all ML model executions for the authenticated user."""
        user = _require_user(authorization, kshetraiq_session)
        return prediction_history_service.get_user_model_summary(user_id=user.user_id)

    # ──────────── Soil Health Score Endpoints ────────────

    @app.post("/api/v1/soil/health-score")
    def calculate_soil_health_score(
        payload: SoilHealthScoreRequest | None = None,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> dict[str, Any]:
        """Calculate transparent soil-health score (0-100) across 5 bands with recommendations.
        If measurements are omitted, evaluates user's latest saved assessment.
        """
        user = _require_user(authorization, kshetraiq_session)
        soil_data: dict[str, Any] = {}
        if payload:
            raw = payload.model_dump(exclude_none=True)
            if raw:
                soil_data = raw

        if not soil_data:
            user_assessments = service.list_all(user_id=user.user_id)
            if user_assessments:
                latest = user_assessments[0]
                if latest.input and getattr(latest.input, "soil", None):
                    soil_obj = latest.input.soil
                    soil_data = {
                        "nitrogen": getattr(soil_obj, "nitrogen_kg_ha", None),
                        "phosphorus": getattr(soil_obj, "phosphorus_kg_ha", None),
                        "potassium": getattr(soil_obj, "potassium_kg_ha", None),
                        "ph": getattr(soil_obj, "ph", None),
                        "soil_moisture": getattr(soil_obj, "soil_moisture_percent", None),
                    }

        return soil_health_service.assess(soil_data)

    @app.get("/api/v1/soil/health-score")
    def get_user_soil_health_score(
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> dict[str, Any]:
        """Fetch soil health score for the authenticated farmer's latest assessment."""
        user = _require_user(authorization, kshetraiq_session)
        user_assessments = service.list_all(user_id=user.user_id)
        soil_data: dict[str, Any] = {}
        if user_assessments:
            latest = user_assessments[0]
            if latest.input and getattr(latest.input, "soil", None):
                soil_obj = latest.input.soil
                soil_data = {
                    "nitrogen": getattr(soil_obj, "nitrogen_kg_ha", None),
                    "phosphorus": getattr(soil_obj, "phosphorus_kg_ha", None),
                    "potassium": getattr(soil_obj, "potassium_kg_ha", None),
                    "ph": getattr(soil_obj, "ph", None),
                    "soil_moisture": getattr(soil_obj, "soil_moisture_percent", None),
                }
        return soil_health_service.assess(soil_data)


    # ──────────── User Activity Endpoints ────────────

    @app.post("/api/v1/user/activities", response_model=UserActivityResponse)
    def log_user_activity(
        payload: UserActivityPayload,
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> UserActivityResponse:
        user = _require_user(authorization, kshetraiq_session)
        return activity_service.log_activity(
            user_id=user.user_id,
            action=payload.action,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            metadata=payload.metadata,
        )

    @app.get("/api/v1/user/activities", response_model=list[UserActivityResponse])
    def get_user_activities(
        limit: int = Query(default=15, ge=1, le=50),
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> list[UserActivityResponse]:
        user = _require_user(authorization, kshetraiq_session)
        return activity_service.get_recent_activities(user_id=user.user_id, limit=limit)

    # ──────────── File Upload Endpoints ────────────

    @app.post("/api/v1/uploads/soil_report/extract")
    async def extract_soil_report(
        file: UploadFile = File(...),
        authorization: str | None = Header(default=None),
        kshetraiq_session: str | None = Cookie(default=None),
    ) -> dict[str, Any]:
        _ = _require_user(authorization, kshetraiq_session)
        content = await _read_limited(file)
        from app.services.soil_report_parser import SoilReportParser
        parser = SoilReportParser()
        return parser.extract_from_bytes(
            file_bytes=content,
            filename=file.filename or "unknown",
            content_type=file.content_type,
        )

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
