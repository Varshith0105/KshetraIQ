"""
KshetraIQ Prediction History Service.

Tracks and persists every machine learning model execution and inference outcome
with complete input features, preprocessed features, outputs, model versions,
confidences, units, methodologies, and audit provenance.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class PredictionRecord:
    """Represents a persisted model prediction record."""

    def __init__(
        self,
        prediction_id: str,
        user_id: Optional[str],
        assessment_id: Optional[str],
        model_id: str,
        model_version: str,
        model_artifact: str,
        execution_timestamp: str,
        execution_status: str,
        input_features: Dict[str, Any],
        preprocessed_features: Optional[Dict[str, Any]],
        prediction_output: Dict[str, Any],
        confidence: Optional[float],
        units: Optional[str],
        prediction_methodology: str,
        data_source: str,
        warnings_or_errors: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.prediction_id = prediction_id
        self.user_id = user_id
        self.assessment_id = assessment_id
        self.model_id = model_id
        self.model_version = model_version
        self.model_artifact = model_artifact
        self.execution_timestamp = execution_timestamp
        self.execution_status = execution_status
        self.input_features = input_features
        self.preprocessed_features = preprocessed_features or {}
        self.prediction_output = prediction_output
        self.confidence = confidence
        self.units = units
        self.prediction_methodology = prediction_methodology
        self.data_source = data_source
        self.warnings_or_errors = warnings_or_errors
        self.provenance = provenance or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "user_id": self.user_id,
            "assessment_id": self.assessment_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "model_artifact": self.model_artifact,
            "execution_timestamp": self.execution_timestamp,
            "execution_status": self.execution_status,
            "input_features": self.input_features,
            "preprocessed_features": self.preprocessed_features,
            "prediction_output": self.prediction_output,
            "confidence": self.confidence,
            "units": self.units,
            "prediction_methodology": self.prediction_methodology,
            "data_source": self.data_source,
            "warnings_or_errors": self.warnings_or_errors,
            "provenance": self.provenance,
        }


class PredictionHistoryService:
    """Manages prediction persistence in SQLite with strict farmer isolation."""

    def __init__(self, settings: Optional[Settings] = None, db_path: Optional[Path] = None) -> None:
        self.settings = settings or get_settings()
        if db_path is not None:
            self.db_path = self.settings.resolve_db_path(db_path)
        else:
            self.db_path = self.settings.resolved_sqlite_db_path
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            logger.warning(
                "PredictionHistoryService could not create directory %s: %s. Falling back to writable temp directory.",
                self.db_path.parent,
                e,
            )
            fallback = self.settings.get_safe_fallback_dir()
            self.db_path = fallback / self.db_path.name
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create prediction_history table and performance indexes."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS model_predictions (
                    prediction_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    assessment_id TEXT,
                    model_id TEXT NOT NULL,
                    model_version TEXT,
                    model_artifact TEXT,
                    execution_timestamp TEXT NOT NULL,
                    execution_status TEXT NOT NULL,
                    input_features_json TEXT NOT NULL,
                    preprocessed_features_json TEXT,
                    prediction_output_json TEXT NOT NULL,
                    confidence REAL,
                    units TEXT,
                    prediction_methodology TEXT,
                    data_source TEXT,
                    warnings_or_errors TEXT,
                    provenance_json TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pred_user_id ON model_predictions(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pred_model_id ON model_predictions(model_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pred_user_model ON model_predictions(user_id, model_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pred_created_at ON model_predictions(execution_timestamp DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pred_assessment_id ON model_predictions(assessment_id)"
            )
            conn.commit()

    def record_prediction(
        self,
        model_id: str,
        input_features: Dict[str, Any],
        prediction_output: Dict[str, Any],
        user_id: Optional[str] = None,
        assessment_id: Optional[str] = None,
        model_version: str = "v1",
        model_artifact: str = "",
        execution_status: str = "success",
        confidence: Optional[float] = None,
        units: Optional[str] = None,
        prediction_methodology: str = "",
        data_source: str = "",
        preprocessed_features: Optional[Dict[str, Any]] = None,
        warnings_or_errors: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> PredictionRecord:
        """Record and persist an ML model execution result."""
        pid = f"pred_{uuid.uuid4().hex[:16]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        rec = PredictionRecord(
            prediction_id=pid,
            user_id=user_id,
            assessment_id=assessment_id,
            model_id=model_id,
            model_version=model_version,
            model_artifact=model_artifact,
            execution_timestamp=now_iso,
            execution_status=execution_status,
            input_features=input_features,
            preprocessed_features=preprocessed_features,
            prediction_output=prediction_output,
            confidence=confidence,
            units=units,
            prediction_methodology=prediction_methodology,
            data_source=data_source,
            warnings_or_errors=warnings_or_errors,
            provenance=provenance,
        )

        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO model_predictions (
                        prediction_id, user_id, assessment_id, model_id, model_version,
                        model_artifact, execution_timestamp, execution_status,
                        input_features_json, preprocessed_features_json, prediction_output_json,
                        confidence, units, prediction_methodology, data_source,
                        warnings_or_errors, provenance_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rec.prediction_id,
                        rec.user_id,
                        rec.assessment_id,
                        rec.model_id,
                        rec.model_version,
                        rec.model_artifact,
                        rec.execution_timestamp,
                        rec.execution_status,
                        json.dumps(rec.input_features),
                        json.dumps(rec.preprocessed_features) if rec.preprocessed_features else None,
                        json.dumps(rec.prediction_output),
                        rec.confidence,
                        rec.units,
                        rec.prediction_methodology,
                        rec.data_source,
                        rec.warnings_or_errors,
                        json.dumps(rec.provenance) if rec.provenance else None,
                    ),
                )
                conn.commit()
            logger.info("Persisted prediction %s for model %s (user: %s)", pid, model_id, user_id)
        except Exception as e:
            logger.error("Failed to persist prediction %s: %s", pid, e)

        return rec

    def get_prediction(self, prediction_id: str, user_id: Optional[str] = None) -> Optional[PredictionRecord]:
        """Fetch a single prediction by ID with optional user authorization."""
        with self._get_connection() as conn:
            if user_id is not None:
                cur = conn.execute(
                    "SELECT * FROM model_predictions WHERE prediction_id = ? AND user_id = ?",
                    (prediction_id, user_id),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM model_predictions WHERE prediction_id = ?",
                    (prediction_id,),
                )
            row = cur.fetchone()
            if row:
                return self._row_to_record(row)
        return None

    def list_predictions(
        self,
        user_id: Optional[str] = None,
        model_id: Optional[str] = None,
        assessment_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[PredictionRecord]:
        """List predictions newest first with optional filters."""
        query = "SELECT * FROM model_predictions WHERE 1=1"
        params: List[Any] = []

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        if model_id is not None:
            query += " AND model_id = ?"
            params.append(model_id)

        if assessment_id is not None:
            query += " AND assessment_id = ?"
            params.append(assessment_id)

        query += " ORDER BY execution_timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cur = conn.execute(query, tuple(params))
            rows = cur.fetchall()
            return [self._row_to_record(r) for r in rows]

    def get_latest_prediction(
        self,
        model_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[PredictionRecord]:
        """Get the most recent prediction for a model."""
        preds = self.list_predictions(user_id=user_id, model_id=model_id, limit=1)
        return preds[0] if preds else None

    def get_user_model_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Summary of all models run for this user."""
        query = """
            SELECT model_id, COUNT(*) as count, MAX(execution_timestamp) as last_run
            FROM model_predictions
            WHERE 1=1
        """
        params: List[Any] = []
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        query += " GROUP BY model_id"

        summary: Dict[str, Any] = {}
        with self._get_connection() as conn:
            cur = conn.execute(query, tuple(params))
            for row in cur.fetchall():
                summary[row["model_id"]] = {
                    "count": row["count"],
                    "last_run": row["last_run"],
                }
        return summary

    def migrate_from_existing_assessments(self) -> int:
        """One-time safe backfill: populate model_predictions from historical assessments."""
        migrated = 0
        try:
            with self._get_connection() as conn:
                # Check if already migrated
                cur = conn.execute("SELECT COUNT(*) FROM model_predictions WHERE model_id = 'crop-recommendation-v1'")
                existing_count = cur.fetchone()[0]
                if existing_count > 0:
                    return existing_count

                cur = conn.execute("SELECT assessment_id, created_at, payload_json, user_id FROM assessments")
                rows = cur.fetchall()
                for r in rows:
                    try:
                        aid = r["assessment_id"]
                        uid = r["user_id"]
                        created_at = r["created_at"]
                        data = json.loads(r["payload_json"])

                        input_data = data.get("input", {})
                        soil = input_data.get("soil", {})
                        weather = input_data.get("weather", {})
                        results = data.get("results", [])

                        for res in results:
                            mid = res.get("model_id")
                            pred = res.get("prediction")
                            if mid == "crop-recommendation-v1" and pred:
                                rec_crop = pred.get("recommended_crop")
                                conf = pred.get("confidence")
                                top_cands = pred.get("top_candidates", [])
                                features = {
                                    "nitrogen_kg_ha": soil.get("nitrogen_kg_ha"),
                                    "phosphorus_kg_ha": soil.get("phosphorus_kg_ha"),
                                    "potassium_kg_ha": soil.get("potassium_kg_ha"),
                                    "ph": soil.get("ph"),
                                    "temperature_c": weather.get("temperature_c") if weather else None,
                                    "humidity_percent": weather.get("humidity_percent") if weather else None,
                                    "rainfall_mm": weather.get("rainfall_mm") if weather else None,
                                    "district": input_data.get("district"),
                                    "state": input_data.get("state"),
                                    "season": input_data.get("season"),
                                }
                                output = {
                                    "recommended_crop": rec_crop,
                                    "recommended_crop_te": pred.get("recommended_crop_te"),
                                    "confidence": conf,
                                    "top_candidates": top_cands,
                                }
                                pid = f"pred_hist_{aid[:8]}"
                                conn.execute(
                                    """
                                    INSERT OR IGNORE INTO model_predictions (
                                        prediction_id, user_id, assessment_id, model_id, model_version,
                                        model_artifact, execution_timestamp, execution_status,
                                        input_features_json, preprocessed_features_json, prediction_output_json,
                                        confidence, units, prediction_methodology, data_source,
                                        warnings_or_errors, provenance_json
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        pid,
                                        uid,
                                        aid,
                                        mid,
                                        "v1",
                                        "crop_recommendation_model.pkl",
                                        created_at,
                                        "success",
                                        json.dumps(features),
                                        None,
                                        json.dumps(output),
                                        conf,
                                        "probability",
                                        "RandomForestClassifier (200 estimators)",
                                        "Historical Assessment Record",
                                        None,
                                        json.dumps({"source": "assessment_backfill"}),
                                    ),
                                )
                                migrated += 1
                    except Exception as row_exc:
                        logger.debug("Skipping row during assessment migration: %s", row_exc)
                conn.commit()
            logger.info("Migrated %d crop recommendations to model_predictions table", migrated)
        except Exception as e:
            logger.error("Error during assessment migration: %s", e)
        return migrated

    def _row_to_record(self, row: sqlite3.Row) -> PredictionRecord:
        input_features = {}
        if row["input_features_json"]:
            try:
                input_features = json.loads(row["input_features_json"])
            except Exception:
                pass

        preprocessed_features = {}
        if row["preprocessed_features_json"]:
            try:
                preprocessed_features = json.loads(row["preprocessed_features_json"])
            except Exception:
                pass

        prediction_output = {}
        if row["prediction_output_json"]:
            try:
                prediction_output = json.loads(row["prediction_output_json"])
            except Exception:
                pass

        provenance = {}
        if row["provenance_json"]:
            try:
                provenance = json.loads(row["provenance_json"])
            except Exception:
                pass

        return PredictionRecord(
            prediction_id=row["prediction_id"],
            user_id=row["user_id"],
            assessment_id=row["assessment_id"],
            model_id=row["model_id"],
            model_version=row["model_version"] or "v1",
            model_artifact=row["model_artifact"] or "",
            execution_timestamp=row["execution_timestamp"],
            execution_status=row["execution_status"],
            input_features=input_features,
            preprocessed_features=preprocessed_features,
            prediction_output=prediction_output,
            confidence=row["confidence"],
            units=row["units"],
            prediction_methodology=row["prediction_methodology"] or "",
            data_source=row["data_source"] or "",
            warnings_or_errors=row["warnings_or_errors"],
            provenance=provenance,
        )


# Global singleton
prediction_history_service = PredictionHistoryService()
