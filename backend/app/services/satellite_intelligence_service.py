"""Dedicated Satellite Intelligence Service for KshetraIQ.

Reuses and adapts the research implementation from:
- capstone-final/satellitle_part.ipynb

Key capabilities:
1. Google Earth Engine authentication (local and service account).
2. Sentinel-2 L2A collection (COPERNICUS/S2_SR_HARMONIZED).
3. Cloud filtering with CLOUDY_PIXEL_PERCENTAGE.
4. ROI geometry creation with buffering and area calculation.
5. 10m Normalized Difference Vegetation Index (NDVI: B8, B4).
6. 10m Enhanced Vegetation Index (EVI: B8, B4, B2).
7. Zonal reduction statistics (Mean, Min, Max, Canopy Health classification).
8. RGB and NDVI visualization generation.
9. 12-month median composite NDVI time-series trend analysis.
10. Truthful status reporting (REQUIRES_CREDENTIALS when unauthenticated).
"""
from __future__ import annotations

import io
import json
import logging
import math
import os
import sqlite3
import time
import urllib.request
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Constants matching notebook
SATELLITE_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
DEFAULT_CLOUD_PERCENTAGE = 20
DEFAULT_RADIUS_METERS = 5000
MAX_RADIUS_METERS = 25000
MIN_RADIUS_METERS = 100
MAX_DATE_RANGE_DAYS = 366


class SatelliteIntelligenceService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.db_path = self.settings.resolved_sqlite_db_path
        self.root = self.settings.ensure_writable_dir(self.settings.resolved_upload_directory / "intelligence")
        self._ee_initialized = False
        self._ee_init_error: str | None = None
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.db_path), timeout=15)
        c.row_factory = sqlite3.Row
        return c

    def _init_db(self) -> None:
        """Ensure the shared intelligence_analyses table exists."""
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS intelligence_analyses (
                analysis_id TEXT PRIMARY KEY, workflow_type TEXT NOT NULL,
                user_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                manifest_json TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_intelligence_user ON intelligence_analyses(user_id, created_at DESC)")

    def _write(self, manifest: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        manifest["updated_at"] = now
        with self._conn() as c:
            c.execute("""INSERT INTO intelligence_analyses(analysis_id,workflow_type,user_id,created_at,updated_at,manifest_json)
              VALUES(?,?,?,?,?,?) ON CONFLICT(analysis_id) DO UPDATE SET updated_at=excluded.updated_at, manifest_json=excluded.manifest_json""",
              (manifest["analysis_id"], manifest["workflow_type"], manifest.get("user_id"), manifest["created_at"], now, json.dumps(manifest)))

    def _read(self, analysis_id: str, user_id: str | None) -> dict[str, Any] | None:
        q, args = "SELECT manifest_json FROM intelligence_analyses WHERE analysis_id = ? AND workflow_type = 'satellite'", [analysis_id]
        if user_id is not None:
            q += " AND (user_id = ? OR user_id IS NULL)"; args.append(user_id)
        with self._conn() as c:
            r = c.execute(q, args).fetchone()
        return json.loads(r["manifest_json"]) if r else None

    def get(self, analysis_id: str, user_id: str | None) -> dict[str, Any] | None:
        return self._read(analysis_id, user_id)

    def history(self, user_id: str | None, limit: int = 30) -> list[dict[str, Any]]:
        q, args = "SELECT manifest_json FROM intelligence_analyses WHERE workflow_type = 'satellite'", []
        if user_id is not None:
            q += " AND (user_id = ? OR user_id IS NULL)"; args.append(user_id)
        q += " ORDER BY created_at DESC LIMIT ?"; args.append(min(max(limit, 1), 100))
        with self._conn() as c:
            rows = c.execute(q, args).fetchall()
        return [json.loads(r["manifest_json"]) for r in rows]

    def _asset(self, analysis_id: str, name: str, data: bytes) -> str:
        folder = self.settings.ensure_writable_dir(self.root / analysis_id)
        path = folder / name
        path.write_bytes(data)
        return str(path)

    # ─────────────────────────────────────────────────────────────
    # Earth Engine Initialization & Authentication
    # ─────────────────────────────────────────────────────────────

    def initialize_earth_engine(self) -> tuple[bool, str | None]:
        """Initializes Earth Engine supporting service account or user credentials."""
        if self._ee_initialized:
            return True, None

        try:
            import ee
        except ImportError:
            self._ee_init_error = "earthengine-api Python package is not installed."
            return False, self._ee_init_error

        project = self.settings.earth_engine_project or "able-pottery-463117-r0"
        sa_email = self.settings.earth_engine_service_account
        key_path = self.settings.earth_engine_credentials_path

        try:
            # 1. Service account JSON credentials (Production)
            if sa_email and key_path and Path(key_path).is_file():
                logger.info("Initializing Earth Engine with service account %s...", sa_email)
                credentials = ee.ServiceAccountCredentials(sa_email, str(key_path))
                ee.Initialize(credentials, project=project)
                self._ee_initialized = True
                self._ee_init_error = None
                return True, None

            # 2. Local user credentials or gcloud token
            logger.info("Initializing Earth Engine with project '%s'...", project)
            ee.Initialize(project=project)
            self._ee_initialized = True
            self._ee_init_error = None
            return True, None
        except Exception as exc:
            err_msg = str(exc)
            logger.warning("Earth Engine initialization could not authenticate: %s", err_msg)
            self._ee_initialized = False
            self._ee_init_error = err_msg
            return False, err_msg

    def get_service_status(self) -> dict[str, Any]:
        """Returns truthful Earth Engine service and model availability status."""
        is_ok, err = self.initialize_earth_engine()
        if is_ok:
            return {
                "model": "sentinel2_ndvi_evi",
                "status": "READY",
                "is_live": True,
                "data_source": SATELLITE_COLLECTION,
                "project": self.settings.earth_engine_project or "able-pottery-463117-r0",
                "supported_operations": [
                    "Sentinel-2 L2A Top-of-Canopy Reflectance",
                    "10m NDVI (Normalized Difference Vegetation Index)",
                    "10m EVI (Enhanced Vegetation Index)",
                    "Zonal Mean/Min/Max Reductions",
                    "True Color RGB (B4, B3, B2)",
                    "12-Month Median NDVI Progression Trend",
                ],
                "reason": "Google Earth Engine connected and authorized for Copernicus Sentinel-2 queries.",
            }
        else:
            return {
                "model": "sentinel2_ndvi_evi",
                "status": "REQUIRES_CREDENTIALS",
                "is_live": False,
                "data_source": SATELLITE_COLLECTION,
                "project": self.settings.earth_engine_project or "able-pottery-463117-r0",
                "supported_operations": [
                    "Sentinel-2 L2A Top-of-Canopy Reflectance",
                    "10m NDVI (Normalized Difference Vegetation Index)",
                    "10m EVI (Enhanced Vegetation Index)",
                    "Zonal Mean/Min/Max Reductions",
                ],
                "reason": (
                    f"Google Earth Engine requires authentication ({err}). "
                    "Authorize access by setting up service account credentials or running 'earthengine authenticate'."
                ),
            }

    # ─────────────────────────────────────────────────────────────
    # Request Validation & Geometry Helpers
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_area_metrics(radius_meters: float) -> dict[str, float]:
        """Calculates area coverage in square meters, hectares, acres, and sq km."""
        area_sq_m = math.pi * (radius_meters ** 2)
        area_ha = area_sq_m / 10000.0
        area_acres = area_ha * 2.47105
        area_sq_km = area_sq_m / 1000000.0
        return {
            "radius_meters": round(radius_meters, 1),
            "area_sq_m": round(area_sq_m, 2),
            "area_hectares": round(area_ha, 2),
            "area_acres": round(area_acres, 2),
            "area_sq_km": round(area_sq_km, 3),
        }

    def validate_analysis_request(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        radius_meters: int = DEFAULT_RADIUS_METERS,
        cloud_percentage: int = DEFAULT_CLOUD_PERCENTAGE,
    ) -> None:
        """Validates geographic coordinates, dates, and parameters."""
        if not (-90.0 <= latitude <= 90.0):
            raise ValueError(f"Latitude {latitude} is outside valid range [-90.0, 90.0].")
        if not (-180.0 <= longitude <= 180.0):
            raise ValueError(f"Longitude {longitude} is outside valid range [-180.0, 180.0].")
        if start_date > end_date:
            raise ValueError(f"Start date ({start_date}) cannot be after end date ({end_date}).")
        date_diff = (end_date - start_date).days
        if date_diff > MAX_DATE_RANGE_DAYS:
            raise ValueError(f"Date range ({date_diff} days) exceeds maximum allowable window of {MAX_DATE_RANGE_DAYS} days.")
        if not (MIN_RADIUS_METERS <= radius_meters <= MAX_RADIUS_METERS):
            raise ValueError(f"Buffer radius {radius_meters}m is outside valid bounds [{MIN_RADIUS_METERS}m, {MAX_RADIUS_METERS}m].")
        if not (0 <= cloud_percentage <= 100):
            raise ValueError(f"Cloud percentage {cloud_percentage}% is outside valid range [0, 100].")

    def create_roi_geometry(self, latitude: float, longitude: float, radius_meters: int) -> Any:
        """Adapts notebook Cell 3: point = ee.Geometry.Point([lon, lat]).buffer(radius).bounds()."""
        import ee
        # Notice in Earth Engine, coordinates are [longitude, latitude]
        point = ee.Geometry.Point([longitude, latitude])
        roi = point.buffer(radius_meters).bounds()
        return roi

    # ─────────────────────────────────────────────────────────────
    # Sentinel-2 Imagery & Indices Calculations (Notebook Cells 4 - 6)
    # ─────────────────────────────────────────────────────────────

    def get_sentinel2_collection(self, roi: Any, start_date: date, end_date: date, cloud_percentage: int) -> Any:
        """Adapts notebook Cell 4: Filters COPERNICUS/S2_SR_HARMONIZED by bounds, date, and cloud cover."""
        import ee
        return (
            ee.ImageCollection(SATELLITE_COLLECTION)
            .filterBounds(roi)
            .filterDate(start_date.isoformat(), end_date.isoformat())
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_percentage))
        )

    @staticmethod
    def calculate_ndvi(image: Any) -> Any:
        """Adapts notebook Cell 5: ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')."""
        return image.normalizedDifference(["B8", "B4"]).rename("NDVI")

    @staticmethod
    def calculate_evi(image: Any) -> Any:
        """Adapts notebook Cell 5: EVI calculation using NIR (B8), Red (B4), and Blue (B2) divided by 10000."""
        nir = image.select("B8").divide(10000)
        red = image.select("B4").divide(10000)
        blue = image.select("B2").divide(10000)
        return image.expression(
            "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
            {"NIR": nir, "RED": red, "BLUE": blue},
        ).rename("EVI")

    def calculate_region_statistics(self, indices_image: Any, roi: Any) -> dict[str, Any]:
        """Adapts notebook Cell 6: reduceRegion mean, min, and max across the ROI."""
        import ee
        reducer = ee.Reducer.mean().combine(reducer2=ee.Reducer.minMax(), sharedInputs=True)
        stats = indices_image.select(["NDVI", "EVI"]).reduceRegion(
            reducer=reducer,
            geometry=roi,
            scale=10,
            maxPixels=1e8,
        ).getInfo()
        return stats or {}

    # ─────────────────────────────────────────────────────────────
    # Visualizations & Monthly Series (Notebook Cells 7 - 10)
    # ─────────────────────────────────────────────────────────────

    def generate_rgb_visualization(self, image: Any, roi: Any) -> tuple[str, bytes | None]:
        """Adapts notebook Cell 7: RGB visual using bands B4, B3, B2, min 0, max 3000."""
        vis = {"region": roi, "dimensions": 768, "format": "png", "bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}
        rgb_url = image.getThumbURL(vis)
        raw_bytes = None
        try:
            raw_bytes = urlopen(rgb_url, timeout=30).read()
        except Exception as exc:
            logger.warning("Could not download RGB thumbnail from Earth Engine: %s", exc)
        return rgb_url, raw_bytes

    def generate_ndvi_visualization(self, ndvi: Any, roi: Any) -> tuple[str, bytes | None]:
        """Adapts notebook Cell 7: NDVI visual with palette ['brown', 'yellow', 'green']."""
        vis = {"region": roi, "dimensions": 768, "format": "png", "min": -1, "max": 1, "palette": ["brown", "yellow", "green"]}
        ndvi_url = ndvi.getThumbURL(vis)
        raw_bytes = None
        try:
            raw_bytes = urlopen(ndvi_url, timeout=30).read()
        except Exception as exc:
            logger.warning("Could not download NDVI thumbnail from Earth Engine: %s", exc)
        return ndvi_url, raw_bytes

    def generate_monthly_ndvi_series(self, roi: Any, year: int, cloud_percentage: int = 30) -> list[dict[str, Any]]:
        """Adapts notebook Cell 9: Monthly 12-month median composite NDVI progression."""
        import ee
        monthly_trends = []
        for mo in range(1, 13):
            m_start = f"{year}-{mo:02d}-01"
            m_end = f"{year}-{mo:02d}-28" if mo == 2 else f"{year}-{mo:02d}-30"
            try:
                m_col = (
                    ee.ImageCollection(SATELLITE_COLLECTION)
                    .filterBounds(roi)
                    .filterDate(m_start, m_end)
                    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_percentage))
                )
                if m_col.size().getInfo() > 0:
                    m_med = m_col.median().normalizedDifference(["B8", "B4"]).rename("NDVI")
                    m_stat = m_med.reduceRegion(ee.Reducer.mean(), roi, 20, 1e7).getInfo()
                    if m_stat and m_stat.get("NDVI") is not None:
                        monthly_trends.append({
                            "month": f"{year}-{mo:02d}",
                            "ndvi": round(float(m_stat["NDVI"]), 3),
                        })
            except Exception as e:
                logger.debug("Monthly trend error for %s-%02d: %s", year, mo, e)
        return monthly_trends

    def generate_trend_plot(self, monthly_trends: list[dict[str, Any]], aid: str) -> str | None:
        """Adapts notebook Cell 10: Generates matplotlib time-series chart of monthly NDVI."""
        if not monthly_trends:
            return None
        try:
            import matplotlib.pyplot as plt
            months = [t["month"] for t in monthly_trends]
            ndvis = [t["ndvi"] for t in monthly_trends]
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(months, ndvis, marker="o", color="#166534", linewidth=2.5, markersize=6, label="Mean NDVI")
            ax.axhline(0.6, color="#22c55e", linestyle="--", alpha=0.6, label="Dense Canopy (0.6)")
            ax.axhline(0.3, color="#eab308", linestyle="--", alpha=0.6, label="Moderate Vigour (0.3)")
            ax.set_title("Sentinel-2 Monthly Mean NDVI Progression", fontsize=12, fontweight="bold", color="#166534")
            ax.set_xlabel("Observation Month", fontsize=10)
            ax.set_ylabel("Mean NDVI (10m)", fontsize=10)
            ax.set_ylim(-0.1, 1.0)
            ax.grid(True, linestyle=":", alpha=0.6)
            ax.legend(loc="upper left", fontsize=8)
            plt.xticks(rotation=45)
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format="PNG", dpi=180, bbox_inches="tight")
            plt.close(fig)
            return self._asset(aid, "sentinel2-monthly-trend.png", buf.getvalue())
        except Exception as exc:
            logger.warning("Could not generate NDVI trend plot: %s", exc)
            return None

    # ─────────────────────────────────────────────────────────────
    # End-to-End Analysis Workflow Execution
    # ─────────────────────────────────────────────────────────────

    def run_satellite_analysis(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        user_id: str | None,
        radius_meters: int = DEFAULT_RADIUS_METERS,
        cloud_percentage: int = DEFAULT_CLOUD_PERCENTAGE,
    ) -> dict[str, Any]:
        """Runs the complete satellite analysis workflow, recording provenance and status."""
        self.validate_analysis_request(latitude, longitude, start_date, end_date, radius_meters, cloud_percentage)
        area_metrics = self.calculate_area_metrics(radius_meters)

        aid = f"satellite_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc).isoformat()
        manifest: dict[str, Any] = {
            "analysis_id": aid,
            "workflow_type": "satellite",
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "radius_m": radius_meters,
                "area_metrics": area_metrics,
            },
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "cloud_percentage_threshold": cloud_percentage,
            },
            "status": "PROCESSING",
            "data_source": SATELLITE_COLLECTION,
            "result": None,
            "error": None,
            "reports": [],
        }
        self._write(manifest)

        # Check Earth Engine connection
        is_authenticated, auth_error = self.initialize_earth_engine()
        if not is_authenticated:
            err_msg = (
                f"Google Earth Engine requires authentication: {auth_error}. "
                "Authorize access by setting up service account credentials or running 'earthengine authenticate'."
            )
            manifest.update(status="UNAVAILABLE", error=err_msg)
            self._write(manifest)
            return manifest

        import ee

        try:
            roi = self.create_roi_geometry(latitude, longitude, radius_meters)
            collection = self.get_sentinel2_collection(roi, start_date, end_date, cloud_percentage)
            count = collection.size().getInfo()

            if not count:
                err_msg = f"No Sentinel-2 scenes with <{cloud_percentage}% cloud cover were found for this location and date window. Try widening the date window or increasing the cloud threshold."
                manifest.update(status="NO_IMAGERY_FOUND", error=err_msg)
                self._write(manifest)
                return manifest

            # Select least-cloudy image matching notebook Cell 4
            image = collection.sort("CLOUDY_PIXEL_PERCENTAGE").first()
            actual_date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd").getInfo()
            actual_cloud_pct = image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()

            # Compute indices matching notebook Cell 5
            ndvi = self.calculate_ndvi(image)
            evi = self.calculate_evi(image)
            indices = image.addBands([ndvi, evi])

            # Zonal reduction matching notebook Cell 6
            stats = self.calculate_region_statistics(indices, roi)

            # Monthly trends matching notebook Cell 9
            year = start_date.year
            monthly_trends = self.generate_monthly_ndvi_series(roi, year, cloud_percentage=30)
            trend_plot_asset = self.generate_trend_plot(monthly_trends, aid)

            # Generate RGB and NDVI visualizations matching notebook Cell 7
            rgb_url, rgb_bytes = self.generate_rgb_visualization(image, roi)
            ndvi_url, ndvi_bytes = self.generate_ndvi_visualization(ndvi, roi)

            visual_assets = []
            if rgb_bytes:
                visual_assets.append(self._asset(aid, "sentinel2-rgb.png", rgb_bytes))
            if ndvi_bytes:
                visual_assets.append(self._asset(aid, "sentinel2-ndvi.png", ndvi_bytes))
            if trend_plot_asset:
                visual_assets.append(trend_plot_asset)

            mean_ndvi = stats.get("NDVI_mean", stats.get("NDVI"))
            min_ndvi = stats.get("NDVI_min")
            max_ndvi = stats.get("NDVI_max")

            mean_evi = stats.get("EVI_mean", stats.get("EVI"))
            min_evi = stats.get("EVI_min")
            max_evi = stats.get("EVI_max")

            # Agronomic interpretation
            if mean_ndvi is not None:
                if mean_ndvi > 0.6:
                    veg_health = "Dense, high-vigour vegetative crop canopy"
                elif mean_ndvi > 0.35:
                    veg_health = "Moderate crop vigour / active vegetative growth"
                elif mean_ndvi > 0.2:
                    veg_health = "Early emergence, sparse canopy, or partial vegetation cover"
                else:
                    veg_health = "Bare soil, fallow ground, or non-vegetated terrain"
            else:
                veg_health = "Indeterminate canopy condition"

            result = {
                "scene_count": count,
                "observation_date": actual_date,
                "cloud_coverage_pct": round(float(actual_cloud_pct), 2) if actual_cloud_pct is not None else None,
                "mean_ndvi": round(float(mean_ndvi), 4) if mean_ndvi is not None else None,
                "min_ndvi": round(float(min_ndvi), 4) if min_ndvi is not None else None,
                "max_ndvi": round(float(max_ndvi), 4) if max_ndvi is not None else None,
                "mean_evi": round(float(mean_evi), 4) if mean_evi is not None else None,
                "min_evi": round(float(min_evi), 4) if min_evi is not None else None,
                "max_evi": round(float(max_evi), 4) if max_evi is not None else None,
                "vegetation_status": veg_health,
                "rgb_preview_url": rgb_url,
                "ndvi_preview_url": ndvi_url,
                "monthly_trends": monthly_trends,
                "visual_assets": visual_assets,
                "area_metrics": area_metrics,
                "methodology": "Copernicus Sentinel-2 SR Harmonized; least-cloudy scene selection; 10m spatial resolution NDVI and EVI computed across farm boundary.",
            }

            manifest.update(status="COMPLETED", result=result, error=None)
            self._write(manifest)
            return manifest
        except Exception as exc:
            logger.exception("Satellite processing failed for analysis %s: %s", aid, exc)
            manifest.update(status="UNAVAILABLE", error=str(exc))
            self._write(manifest)
            return manifest

    # ─────────────────────────────────────────────────────────────
    # Report Generation (PDF)
    # ─────────────────────────────────────────────────────────────

    def generate_report(self, analysis_id: str, user_id: str | None) -> tuple[dict[str, Any], bytes]:
        """Generates an official PDF report for satellite analysis using ReportLab."""
        m = self.get(analysis_id, user_id)
        if not m:
            raise KeyError(analysis_id)

        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.platypus import HRFlowable, Image as PDFImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError as e:
            raise RuntimeError("reportlab is required to generate satellite intelligence reports.") from e

        report_dir = self.settings.ensure_writable_dir(self.root / analysis_id)
        path = report_dir / "report.pdf"
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=22, leading=26, textColor=colors.HexColor("#166534"), alignment=TA_CENTER)
        sub_style = ParagraphStyle("ReportSub", parent=styles["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#555555"), alignment=TA_CENTER)
        h1_style = ParagraphStyle("ReportH1", parent=styles["Heading1"], fontSize=14, leading=18, textColor=colors.HexColor("#166534"), spaceBefore=12, spaceAfter=6)
        body_style = ParagraphStyle("ReportBody", parent=styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#2d3748"))

        story.append(Paragraph("KshetraIQ Agri Intelligence", title_style))
        story.append(Paragraph("Copernicus Sentinel-2 Satellite Geospatial Intelligence Report", sub_style))
        story.append(Paragraph(f"Analysis ID: {analysis_id} &nbsp;|&nbsp; Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", sub_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#166534"), spaceBefore=4, spaceAfter=12))

        loc = m.get("location", {})
        area_m = loc.get("area_metrics") or self.calculate_area_metrics(loc.get("radius_m", 5000))
        sat_res = m.get("result") or {}

        sat_table = [
            [Paragraph("<b>Target Coordinates:</b>", body_style), Paragraph(f"Latitude: {loc.get('latitude')}, Longitude: {loc.get('longitude')}", body_style)],
            [Paragraph("<b>Farm Study Buffer:</b>", body_style), Paragraph(f"Radius {loc.get('radius_m')}m (~{area_m['area_acres']} acres / {area_m['area_hectares']} ha)", body_style)],
            [Paragraph("<b>Status:</b>", body_style), Paragraph(f"<b>{m.get('status')}</b>", body_style)],
            [Paragraph("<b>Sentinel-2 Acquisition:</b>", body_style), Paragraph(f"{sat_res.get('observation_date', 'N/A')}", body_style)],
            [Paragraph("<b>Mean 10m NDVI:</b>", body_style), Paragraph(f"<b>{sat_res.get('mean_ndvi', 'N/A')}</b>", body_style)],
            [Paragraph("<b>Mean 10m EVI:</b>", body_style), Paragraph(f"<b>{sat_res.get('mean_evi', 'N/A')}</b>", body_style)],
            [Paragraph("<b>Canopy Health Condition:</b>", body_style), Paragraph(f"{sat_res.get('vegetation_status', 'N/A')}", body_style)],
            [Paragraph("<b>Data Provenance:</b>", body_style), Paragraph("European Space Agency (ESA) Copernicus Sentinel-2 L2A via Google Earth Engine", body_style)],
        ]
        t = Table(sat_table, colWidths=[150, 350])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#86efac")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 14))

        # Visual assets
        sat_assets = sat_res.get("visual_assets", [])
        for asset in sat_assets:
            if Path(asset).is_file():
                story.append(Spacer(1, 8))
                story.append(PDFImage(asset, width=460, height=280, kind="proportional"))

        with path.open("wb") as output:
            SimpleDocTemplate(output, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36).build(story)

        rec = {"path": str(path), "generated_at": datetime.now(timezone.utc).isoformat()}
        m["reports"].append(rec)
        self._write(m)
        return rec, path.read_bytes()


# Singleton instance
satellite_intelligence_service = SatelliteIntelligenceService()
