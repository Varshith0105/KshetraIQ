"""FastAPI router for Satellite Intelligence module.

Provides endpoints for Earth Engine status, Sentinel-2 analysis,
historical records, and PDF report generation.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Cookie, Header, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.satellite_intelligence_service import (
    DEFAULT_CLOUD_PERCENTAGE,
    DEFAULT_RADIUS_METERS,
    SATELLITE_COLLECTION,
    satellite_intelligence_service,
)

router = APIRouter(prefix="/api/satellite-intelligence", tags=["Satellite Intelligence"])


class SatelliteAnalysisRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Target field latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Target field longitude")
    radius_meters: int | None = Field(default=None, description="Study area buffer radius in meters")
    radius_m: int | None = Field(default=None, description="Legacy parameter for radius in meters")
    start_date: date = Field(..., description="Start of observation date range")
    end_date: date = Field(..., description="End of observation date range")
    cloud_percentage: int = Field(default=DEFAULT_CLOUD_PERCENTAGE, ge=0, le=100, description="Maximum acceptable cloudy pixel percentage")

    @property
    def effective_radius(self) -> int:
        if self.radius_meters is not None:
            return self.radius_meters
        if self.radius_m is not None:
            return self.radius_m
        return DEFAULT_RADIUS_METERS


def _get_auth_user_id(authorization: str | None, kshetraiq_session: str | None) -> str | None:
    """Extract authenticated user_id from Bearer token or session cookie."""
    from app.services.auth_service import auth_service
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif kshetraiq_session:
        token = kshetraiq_session
    if not token:
        return None
    user = auth_service.get_user_by_token(token)
    return user.user_id if user else None


@router.get("/status")
def get_satellite_status() -> dict[str, Any]:
    """Returns Earth Engine authentication status and capabilities."""
    return satellite_intelligence_service.get_service_status()


@router.get("/models/status")
def get_satellite_models_status() -> list[dict[str, Any]]:
    """Legacy-compatible array format for frontend dashboard model status."""
    st = satellite_intelligence_service.get_service_status()
    return [st]


@router.get("/data-availability")
def get_data_availability() -> dict[str, Any]:
    """Returns details on data availability and prerequisites."""
    st = satellite_intelligence_service.get_service_status()
    return {
        "data_source": SATELLITE_COLLECTION,
        "status": st["status"],
        "is_live": st["is_live"],
        "project": st.get("project"),
        "reason": st.get("reason"),
        "supported_operations": st.get("supported_operations", []),
        "requirements": ["latitude", "longitude", "date range", "Earth Engine credentials"],
    }


@router.post("/analyze")
def analyze_satellite_intelligence(
    payload: SatelliteAnalysisRequest,
    authorization: str | None = Header(default=None),
    kshetraiq_session: str | None = Cookie(default=None),
) -> dict[str, Any]:
    """Runs Sentinel-2 satellite analysis over selected farm coordinates and date window."""
    user_id = _get_auth_user_id(authorization, kshetraiq_session)
    try:
        return satellite_intelligence_service.run_satellite_analysis(
            latitude=payload.latitude,
            longitude=payload.longitude,
            start_date=payload.start_date,
            end_date=payload.end_date,
            user_id=user_id,
            radius_meters=payload.effective_radius,
            cloud_percentage=payload.cloud_percentage,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err)) from val_err
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Satellite analysis failed: {exc}") from exc


@router.get("/history")
def get_satellite_history(
    limit: int = Query(default=30, ge=1, le=100),
    authorization: str | None = Header(default=None),
    kshetraiq_session: str | None = Cookie(default=None),
) -> list[dict[str, Any]]:
    """Returns recent satellite analysis sessions for the authenticated user."""
    user_id = _get_auth_user_id(authorization, kshetraiq_session)
    return satellite_intelligence_service.history(user_id=user_id, limit=limit)


@router.get("/reports")
def get_satellite_reports(
    authorization: str | None = Header(default=None),
    kshetraiq_session: str | None = Cookie(default=None),
) -> list[dict[str, Any]]:
    """Lists completed satellite reports for the current user."""
    user_id = _get_auth_user_id(authorization, kshetraiq_session)
    items = satellite_intelligence_service.history(user_id=user_id)
    return [{"analysis_id": x["analysis_id"], "reports": x.get("reports", [])} for x in items if x.get("reports")]


@router.get("/{analysis_id}")
@router.get("/{analysis_id}/status")
def get_satellite_analysis_by_id(
    analysis_id: str,
    authorization: str | None = Header(default=None),
    kshetraiq_session: str | None = Cookie(default=None),
) -> dict[str, Any]:
    """Retrieves a specific satellite analysis by ID, verifying user ownership."""
    user_id = _get_auth_user_id(authorization, kshetraiq_session)
    m = satellite_intelligence_service.get(analysis_id, user_id=user_id)
    if not m:
        raise HTTPException(status_code=404, detail="Satellite analysis session not found.")
    return m


@router.post("/{analysis_id}/report")
def generate_satellite_report(
    analysis_id: str,
    authorization: str | None = Header(default=None),
    kshetraiq_session: str | None = Cookie(default=None),
) -> Response:
    """Generates and downloads the official PDF report for a satellite analysis."""
    user_id = _get_auth_user_id(authorization, kshetraiq_session)
    try:
        _, pdf_data = satellite_intelligence_service.generate_report(analysis_id, user_id=user_id)
        return Response(
            pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{analysis_id}_report.pdf"'},
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Satellite analysis not found.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate satellite report: {exc}")


@router.get("/{analysis_id}/report")
@router.get("/{analysis_id}/report/preview")
def preview_satellite_report(
    analysis_id: str,
    authorization: str | None = Header(default=None),
    kshetraiq_session: str | None = Cookie(default=None),
) -> FileResponse:
    """Previews the generated PDF report."""
    user_id = _get_auth_user_id(authorization, kshetraiq_session)
    m = satellite_intelligence_service.get(analysis_id, user_id=user_id)
    if not m or not m.get("reports"):
        raise HTTPException(status_code=404, detail="No generated report found for this analysis.")
    report_path = Path(m["reports"][-1]["path"])
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Report PDF file is missing on server.")
    return FileResponse(report_path, media_type="application/pdf")


@router.get("/{analysis_id}/assets/{asset_name}")
def get_satellite_asset(
    analysis_id: str,
    asset_name: str,
    authorization: str | None = Header(default=None),
    kshetraiq_session: str | None = Cookie(default=None),
) -> FileResponse:
    """Streams a generated satellite asset (RGB preview, NDVI map, or trend chart)."""
    user_id = _get_auth_user_id(authorization, kshetraiq_session)
    m = satellite_intelligence_service.get(analysis_id, user_id=user_id)
    if not m:
        raise HTTPException(status_code=404, detail="Satellite analysis not found.")
    sat_res = m.get("result") or {}
    candidates = [Path(p) for p in sat_res.get("visual_assets", [])]
    target = next((p for p in candidates if p.name == asset_name), None)
    if not target or not target.is_file():
        raise HTTPException(status_code=404, detail="Asset not found.")
    return FileResponse(target)
