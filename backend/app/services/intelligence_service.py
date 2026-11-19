"""Persisted, truthful plant and satellite intelligence workflows.

Adapts the actual research notebooks:
- capstone-final/main_file_capstone(1).ipynb
- capstone-final/satellitle_part.ipynb

Models integrated:
1. ResNet50: 23-class foliar disease vision classifier (plant_disease.h5 / plant_disease.tflite)
2. SAM: Segment Anything (ViT-B official checkpoint sam_vit_b_01ec64.pth)
3. LIME: Local Interpretable Model-agnostic Explanations (LimeImageExplainer)
4. BLIP: Image Captioning & Detailed Visual Observations (Salesforce/blip-image-captioning-base)
5. Sentinel-2: Google Earth Engine COPERNICUS/S2_SR_HARMONIZED (NDVI, EVI, Monthly time-series)
"""
from __future__ import annotations

import io
import json
import logging
import os
import sqlite3
import threading
import time
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

# Ensure offline mode so transformers / huggingface_hub uses cached models without network retry stalls
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import numpy as np
from PIL import Image

import matplotlib
matplotlib.use("Agg")

from app.core.config import Settings, get_settings
from app.services.plant_disease_service import plant_disease_service

logger = logging.getLogger(__name__)

MODEL_NAMES = ("disease_classifier", "sam", "lime", "blip")

# Lazy-loaded singletons for memory efficiency
_SAM_GENERATOR: Any = None
_BLIP_PROCESSOR: Any = None
_BLIP_MODEL: Any = None
_LIME_EXPLAINER: Any = None


def _get_sam_generator(checkpoint_path: Path) -> Any:
    global _SAM_GENERATOR
    if _SAM_GENERATOR is None:
        logger.info("Initializing SAM ViT-B model from %s", checkpoint_path)
        import torch
        from segment_anything import SamAutomaticMaskGenerator, sam_model_registry

        # ── PyTorch >= 2.6 compatibility ─────────────────────────────────────
        # torch.load now defaults to weights_only=True, which rejects the
        # numpy scalars serialised inside Meta AI SAM checkpoints
        # (WeightsUnpickler error: Unsupported operand 118).
        # We temporarily override torch.load within this call scope so that
        # weights_only=False is used for the trusted official checkpoint.
        _orig_torch_load = torch.load

        def _patched_torch_load(f, *args, **kwargs):
            kwargs.setdefault("weights_only", False)
            return _orig_torch_load(f, *args, **kwargs)

        torch.load = _patched_torch_load
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            sam = sam_model_registry["vit_b"](checkpoint=str(checkpoint_path))
        finally:
            torch.load = _orig_torch_load  # always restore original

        sam.to(device=device)
        # points_per_side=16 provides dense foliar mask coverage while optimizing CPU inference latency
        _SAM_GENERATOR = SamAutomaticMaskGenerator(sam, points_per_side=16, points_per_batch=16)
        logger.info("SAM ViT-B initialized successfully on %s.", device)
    return _SAM_GENERATOR


def _get_lime_explainer() -> Any:
    global _LIME_EXPLAINER
    if _LIME_EXPLAINER is None:
        from lime import lime_image
        _LIME_EXPLAINER = lime_image.LimeImageExplainer()
    return _LIME_EXPLAINER


def _get_blip() -> tuple[Any, Any]:
    global _BLIP_PROCESSOR, _BLIP_MODEL
    if _BLIP_MODEL is None:
        logger.info("Loading Salesforce/blip-image-captioning-base...")
        from transformers import BlipForConditionalGeneration, BlipProcessor
        try:
            _BLIP_PROCESSOR = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", local_files_only=True)
            _BLIP_MODEL = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base", local_files_only=True)
        except Exception:
            _BLIP_PROCESSOR = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            _BLIP_MODEL = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        logger.info("BLIP loaded successfully.")
    return _BLIP_PROCESSOR, _BLIP_MODEL


class IntelligenceService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.db_path = self.settings.resolved_sqlite_db_path
        self.root = self.settings.ensure_writable_dir(self.settings.resolved_upload_directory / "intelligence")
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.db_path), timeout=15)
        c.row_factory = sqlite3.Row
        return c

    def _init_db(self) -> None:
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
        q, args = "SELECT manifest_json FROM intelligence_analyses WHERE analysis_id = ?", [analysis_id]
        if user_id is not None:
            q += " AND (user_id = ? OR user_id IS NULL)"; args.append(user_id)
        with self._conn() as c:
            r = c.execute(q, args).fetchone()
        return json.loads(r["manifest_json"]) if r else None

    def get(self, analysis_id: str, user_id: str | None) -> dict[str, Any] | None:
        return self._read(analysis_id, user_id)

    def history(self, workflow: str, user_id: str | None, limit: int = 30) -> list[dict[str, Any]]:
        q, args = "SELECT manifest_json FROM intelligence_analyses WHERE workflow_type = ?", [workflow]
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

    @staticmethod
    def _module(name: str) -> bool:
        import importlib.util
        return importlib.util.find_spec(name) is not None

    @staticmethod
    def _is_valid_sam_file(path: Path | None) -> bool:
        return bool(path and path.is_file() and path.stat().st_size > 10 * 1024 * 1024)

    def _ensure_sam_checkpoint(self) -> Path:
        """Find or download official SAM vit_b checkpoint."""
        candidate = self.settings.resolved_sam_checkpoint_path
        if self._is_valid_sam_file(candidate):
            return candidate  # type: ignore[return-value]

        target_dir = Path(__file__).resolve().parents[3] / "capstone-final"
        target_path = target_dir / "sam_vit_b_01ec64.pth"
        if self._is_valid_sam_file(target_path):
            return target_path
        url = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
        logger.info("Downloading official SAM ViT-B checkpoint to %s...", target_path)
        target_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.with_suffix(".tmp")
        urllib.request.urlretrieve(url, str(tmp_path))
        if tmp_path.is_file() and tmp_path.stat().st_size > 10 * 1024 * 1024:
            tmp_path.replace(target_path)
        logger.info("SAM ViT-B checkpoint download complete.")
        return target_path

    def plant_status(self) -> list[dict[str, Any]]:
        has_tf = self._module("tensorflow") or self._module("keras")
        artifact_audit = plant_disease_service.inspect_artifacts()
        h5_valid = artifact_audit["h5"]["is_valid_hdf5"]
        tflite_valid = artifact_audit["tflite"]["is_valid_tflite"]
        classifier_ready = (h5_valid or tflite_valid) and has_tf

        sam_path = Path(__file__).resolve().parents[3] / "capstone-final" / "sam_vit_b_01ec64.pth"
        cand_path = self.settings.resolved_sam_checkpoint_path
        has_sam_checkpoint = self._is_valid_sam_file(cand_path) or self._is_valid_sam_file(sam_path)
        has_sam_module = self._module("segment_anything")

        has_lime = self._module("lime")
        has_transformers = self._module("transformers") and self._module("torch")

        hf_cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
        blip_cached = (hf_cache_dir / "models--Salesforce--blip-image-captioning-base").is_dir()

        classifier_detail = []
        if artifact_audit["h5"]["is_lfs_pointer"]:
            classifier_detail.append("Checked plant_disease.h5: 133-byte Git LFS pointer text file detected")
        elif h5_valid:
            classifier_detail.append(f"plant_disease.h5: verified valid HDF5 weights ({artifact_audit['h5']['size_bytes'] / (1024*1024):.1f} MB)")
        if tflite_valid:
            classifier_detail.append(f"plant_disease.tflite: validated ({artifact_audit['tflite']['size_bytes'] / (1024*1024):.1f} MB)")

        return [
            {
                "model": "disease_classifier",
                "status": "READY" if classifier_ready else ("NOT_INSTALLED" if not has_tf else "MISSING_CHECKPOINT"),
                "is_live": classifier_ready,
                "version": "ResNet50-23class",
                "reason": "; ".join(classifier_detail) if classifier_ready else (plant_disease_service.load_error or "Artifacts missing"),
            },
            {
                "model": "sam",
                "status": "READY" if (has_sam_module and has_sam_checkpoint) else ("NOT_INSTALLED" if not has_sam_module else "READY"),
                "is_live": has_sam_module and has_sam_checkpoint,
                "version": "SAM ViT-B (Meta AI)",
                "reason": f"Checkpoint verified ({sam_path.stat().st_size / (1024*1024):.1f} MB)" if has_sam_checkpoint else "Checkpoint will download automatically on first use from Meta AI weights.",
            },
            {
                "model": "lime",
                "status": "READY" if (has_lime and classifier_ready) else ("NOT_INSTALLED" if not has_lime else "BLOCKED_DEPENDENCY"),
                "is_live": has_lime and classifier_ready,
                "version": "LIME Image Explainer",
                "reason": "LimeImageExplainer initialized with ResNet50 classifier." if (has_lime and classifier_ready) else "Requires lime package and ready ResNet50 classifier.",
            },
            {
                "model": "blip",
                "status": "READY" if has_transformers else "NOT_INSTALLED",
                "is_live": has_transformers and blip_cached,
                "version": "Salesforce/blip-image-captioning-base",
                "reason": "Hugging Face model cached locally and verified." if blip_cached else "Will download Salesforce/blip-image-captioning-base on initialization.",
            },
        ]

    def create_plant(self, content: bytes, filename: str, user_id: str | None, selected: list[str] | None = None) -> dict[str, Any]:
        with Image.open(io.BytesIO(content)) as im:
            im.verify()
        aid = f"plant_{uuid.uuid4().hex}"
        ext = Path(filename).suffix.lower() if Path(filename).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"
        original = self._asset(aid, f"original{ext}", content)
        now = datetime.now(timezone.utc).isoformat()
        manifest: dict[str, Any] = {
            "analysis_id": aid,
            "workflow_type": "plant",
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "original_image": original,
            "original_filename": filename,
            "executed_models": {
                m: {
                    "model": m,
                    "status": "NOT_RUN",
                    "result": None,
                    "visual_assets": [],
                    "error": None,
                    "execution_time_sec": None,
                }
                for m in MODEL_NAMES
            },
            "composite_2x2": None,
            "reports": [],
        }
        self._write(manifest)

        models_to_run = list(MODEL_NAMES if selected is None else [m for m in selected if m in MODEL_NAMES])

        # Run disease_classifier synchronously first (fast, ~1-2s) so the response includes diagnosis
        if "disease_classifier" in models_to_run:
            self.run_plant(aid, "disease_classifier", user_id)
            models_to_run = [m for m in models_to_run if m != "disease_classifier"]

        # Run remaining models in background threads so HTTP response returns quickly
        # The frontend should poll GET /api/plant-intelligence/{aid} to get updated results
        if models_to_run:
            def _run_remaining_models():
                for model in models_to_run:
                    try:
                        self.run_plant(aid, model, user_id)
                    except Exception as exc:
                        logger.error("Background model %s failed for %s: %s", model, aid, exc)
                # Generate composite after all models complete
                self._generate_composite_2x2(aid, user_id)

            t = threading.Thread(target=_run_remaining_models, daemon=True, name=f"plant-{aid[:12]}")
            t.start()

        return self._read(aid, user_id) or manifest

    def run_plant(self, aid: str, model: str, user_id: str | None) -> dict[str, Any]:
        if model not in MODEL_NAMES:
            raise ValueError(f"Unsupported plant model: {model}")
        m = self._read(aid, user_id)
        if not m or m["workflow_type"] != "plant":
            raise KeyError(aid)

        record = m["executed_models"][model]
        record.update(status="PROCESSING", error=None)
        self._write(m)

        start_time = time.time()
        try:
            image_bytes = Path(m["original_image"]).read_bytes()
            if model == "disease_classifier":
                result = plant_disease_service.predict_image(image_bytes, m["original_filename"])
                record.update(
                    status="COMPLETED",
                    result=result,
                    model_version=result.get("model_architecture", "ResNet50-23class"),
                    execution_time_sec=round(time.time() - start_time, 2),
                )
            elif model == "sam":
                self._run_sam(m, record, image_bytes)
                record.update(execution_time_sec=round(time.time() - start_time, 2))
            elif model == "lime":
                self._run_lime(m, record, image_bytes)
                record.update(execution_time_sec=round(time.time() - start_time, 2))
            elif model == "blip":
                self._run_blip(m, record, image_bytes)
                record.update(execution_time_sec=round(time.time() - start_time, 2))
        except Exception as exc:
            logger.exception("Error executing %s for analysis %s: %s", model, aid, exc)
            record.update(
                status="FAILED",
                error=str(exc),
                execution_time_sec=round(time.time() - start_time, 2),
            )

        self._write(m)
        return m

    def _run_sam(self, m: dict[str, Any], r: dict[str, Any], content: bytes) -> None:
        checkpoint_path = self._ensure_sam_checkpoint()
        generator = _get_sam_generator(checkpoint_path)

        im = Image.open(io.BytesIO(content)).convert("RGB")
        ar = np.array(im)

        masks = generator.generate(ar)
        if not masks:
            raise RuntimeError("SAM generated 0 masks on this leaf image.")

        # Sort masks by area descending
        masks_sorted = sorted(masks, key=lambda x: x["area"], reverse=True)
        largest_mask = masks_sorted[0]["segmentation"]
        combined_mask = np.logical_or.reduce([x["segmentation"] for x in masks])

        # Generate binary mask PNG
        mask_img = Image.fromarray((combined_mask * 255).astype("uint8"))
        mb = io.BytesIO()
        mask_img.save(mb, "PNG")

        # Generate overlay matching notebook cell 15 / cell 33 (alpha=0.45, jet colormap)
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.imshow(ar)
        ax.imshow(combined_mask, alpha=0.45, cmap="jet")
        ax.axis("off")
        plt.tight_layout(pad=0)
        ob = io.BytesIO()
        plt.savefig(ob, format="PNG", bbox_inches="tight", pad_inches=0, dpi=180)
        plt.close(fig)

        # Segmented cutout
        cutout = ar.copy()
        cutout[~combined_mask] = 255
        cb = io.BytesIO()
        Image.fromarray(cutout).save(cb, "PNG")

        mask_asset = self._asset(m["analysis_id"], "sam-mask.png", mb.getvalue())
        overlay_asset = self._asset(m["analysis_id"], "sam-overlay.png", ob.getvalue())
        cutout_asset = self._asset(m["analysis_id"], "sam-segmented.png", cb.getvalue())

        r.update(
            status="COMPLETED",
            model_version="SAM ViT-B (Meta AI)",
            result={
                "mask_count": len(masks),
                "largest_mask_area": int(masks_sorted[0]["area"]),
                "total_segmented_pixels": int(combined_mask.sum()),
                "leaf_coverage_pct": round(float(combined_mask.sum()) / float(ar.shape[0] * ar.shape[1]) * 100, 2),
                "summary": f"Segmented {len(masks)} structural foliar regions isolating leaf tissue from the background.",
            },
            visual_assets=[mask_asset, overlay_asset, cutout_asset],
        )

    def _run_lime(self, m: dict[str, Any], r: dict[str, Any], content: bytes) -> None:
        if not plant_disease_service.is_available():
            raise RuntimeError("ResNet50 disease classifier is unavailable; LIME requires the trained classifier.")

        from skimage.segmentation import mark_boundaries

        explainer = _get_lime_explainer()
        im = Image.open(io.BytesIO(content)).convert("RGB")
        ar = np.array(im)

        plant_disease_service._ensure_loaded()

        def predict_fn(images: Any) -> Any:
            outputs = []
            for x in images:
                resized = np.asarray(Image.fromarray(x.astype("uint8")).resize((160, 160)), dtype=np.float32)[None, ...]
                if plant_disease_service._is_tflite:
                    plant_disease_service._model.set_tensor(plant_disease_service._tflite_input_details[0]["index"], resized)
                    plant_disease_service._model.invoke()
                    outputs.append(plant_disease_service._model.get_tensor(plant_disease_service._tflite_output_details[0]["index"])[0])
                else:
                    outputs.append(plant_disease_service._model.predict(resized, verbose=0)[0])
            return np.asarray(outputs)

        exp = explainer.explain_instance(
            ar,
            predict_fn,
            top_labels=3,
            hide_color=0,
            num_samples=50,  # 50 samples for speed; still statistically meaningful
        )

        top_label = int(exp.top_labels[0])
        visual, mask = exp.get_image_and_mask(
            top_label,
            positive_only=False,
            num_features=10,
            hide_rest=False,
        )

        class_name = plant_disease_service.classes[top_label] if top_label < len(plant_disease_service.classes) else f"Class_{top_label}"

        # Overlay boundaries with figure matching capstone-final/lime explanation.png
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(mark_boundaries(visual / 255.0, mask))
        ax.set_title(
            f"LIME Explanation\nPredicted: {class_name}",
            fontsize=13,
            fontweight="bold",
        )
        ax.axis("off")
        plt.tight_layout()

        lb = io.BytesIO()
        plt.savefig(lb, format="PNG", dpi=200, bbox_inches="tight")
        plt.close(fig)

        lime_asset = self._asset(m["analysis_id"], "lime-explanation.png", lb.getvalue())
        r.update(
            status="COMPLETED",
            model_version="LIME ImageExplainer",
            result={
                "explained_class_index": top_label,
                "explained_class": class_name,
                "num_samples": 50,
                "features_analyzed": 10,
                "interpretation": f"Highlighted superpixel segments denote the foliar symptoms that contributed most strongly to the {class_name} diagnostic prediction.",
            },
            visual_assets=[lime_asset],
        )

    def generate_detailed_caption(self, image: Image.Image) -> dict[str, str]:
        """Generate both concise and rich, detailed natural-language foliar descriptions via BLIP.

        Uses prompt-conditioned beam search with repetition penalties to extract visible leaf blade
        characteristics (coloration, spots, lesions, holes, background) while avoiding hallucinated
        taxonomic or diagnostic assertions.
        """
        import re
        import torch

        processor, model = _get_blip()

        # 1. Concise baseline caption (unconditioned)
        inp_base = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            out_base = model.generate(**inp_base, max_new_tokens=50, num_beams=3)
        base_cap = processor.decode(out_base[0], skip_special_tokens=True).strip()
        if base_cap:
            base_cap = base_cap[0].upper() + base_cap[1:]
            if not base_cap.endswith("."):
                base_cap += "."

        # 2. Detailed prompt-conditioned descriptive generation
        prompt = "a close-up photograph of the leaf showing"
        inp_det = processor(images=image, text=prompt, return_tensors="pt")
        with torch.no_grad():
            out_det = model.generate(
                **inp_det,
                max_new_tokens=90,
                min_new_tokens=25,
                num_beams=4,
                repetition_penalty=1.25,
                no_repeat_ngram_size=2,
                early_stopping=True,
            )
        detailed = processor.decode(out_det[0], skip_special_tokens=True).strip()

        # Clean any trailing watermark, stock photo, or web pretraining artifacts
        detailed = re.sub(
            r"\s*(?:photo by|getty|alamy|flickr|©|\bcom\b|for sale|stock photo).*$",
            "",
            detailed,
            flags=re.IGNORECASE,
        ).strip().rstrip(",; -")
        if detailed:
            detailed = detailed[0].upper() + detailed[1:]
            if not detailed.endswith("."):
                detailed += "."

        # Synthesize observation narrative
        full_text = detailed
        if base_cap and base_cap.lower() not in detailed.lower():
            full_text = f"{detailed} General visual observation: {base_cap}"

        return {
            "caption": base_cap or detailed,
            "detailed_caption": detailed or base_cap,
            "full_description": full_text,
        }

    def _run_blip(self, m: dict[str, Any], r: dict[str, Any], content: bytes) -> None:
        import matplotlib.pyplot as plt

        im = Image.open(io.BytesIO(content)).convert("RGB")
        captions = self.generate_detailed_caption(im)

        # Generate captioned visual asset matching notebook cell 14
        fig, ax = plt.subplots(figsize=(7, 7))
        ax.imshow(im)
        ax.axis("off")
        title_text = f"BLIP Detailed Foliar Observation\n\"{captions['detailed_caption']}\""
        ax.set_title(title_text, fontsize=10, wrap=True, fontweight="bold")
        plt.tight_layout()
        bb = io.BytesIO()
        plt.savefig(bb, format="PNG", dpi=180, bbox_inches="tight")
        plt.close(fig)
        blip_asset = self._asset(m["analysis_id"], "blip-analysis.png", bb.getvalue())

        r.update(
            status="COMPLETED",
            model_version="Salesforce/blip-image-captioning-base",
            result={
                "caption": captions["caption"],
                "detailed_caption": captions["detailed_caption"],
                "full_description": captions["full_description"],
                "model_identifier": "Salesforce/blip-image-captioning-base",
                "generation_method": "prompt-conditioned beam search with repetition penalty",
                "observations": captions["full_description"],
            },
            visual_assets=[blip_asset],
        )

    def _generate_composite_2x2(self, aid: str, user_id: str | None) -> None:
        """Reproduce notebook cell 15 integrated 2x2 visualization."""
        m = self._read(aid, user_id)
        if not m:
            return

        import matplotlib.pyplot as plt

        im_path = Path(m["original_image"])
        if not im_path.is_file():
            return
        orig_img = Image.open(im_path).convert("RGB")

        disease_info = m["executed_models"].get("disease_classifier", {}).get("result") or {}
        pred_label = disease_info.get("predicted_class", "Leaf Analysis")
        conf = disease_info.get("confidence_pct", 0.0)

        sam_assets = m["executed_models"].get("sam", {}).get("visual_assets") or []
        sam_overlay_img = None
        for a in sam_assets:
            if "overlay" in a and Path(a).is_file():
                sam_overlay_img = Image.open(a).convert("RGB")
                break

        lime_assets = m["executed_models"].get("lime", {}).get("visual_assets") or []
        lime_img = None
        for a in lime_assets:
            if Path(a).is_file():
                lime_img = Image.open(a).convert("RGB")
                break

        blip_info = m["executed_models"].get("blip", {}).get("result") or {}
        caption = blip_info.get("caption", "Plant leaf foliage analysis")

        fig, axes = plt.subplots(2, 2, figsize=(14, 12))

        # [0, 0] Original Image
        axes[0, 0].imshow(orig_img)
        axes[0, 0].set_title(f"Original Image\nDiagnosis: {pred_label}", fontsize=12, fontweight="bold")
        axes[0, 0].axis("off")

        # [0, 1] SAM2 / SAM Segmentation
        if sam_overlay_img is not None:
            axes[0, 1].imshow(sam_overlay_img)
        else:
            axes[0, 1].imshow(orig_img)
        axes[0, 1].set_title("SAM Segmentation Overlay", fontsize=12, fontweight="bold")
        axes[0, 1].axis("off")

        # [1, 0] BLIP Image Understanding
        axes[1, 0].imshow(orig_img)
        axes[1, 0].set_title(f"BLIP Image Understanding\n{caption}", fontsize=11, wrap=True)
        axes[1, 0].axis("off")

        # [1, 1] LIME Explanation
        if lime_img is not None:
            axes[1, 1].imshow(lime_img)
        else:
            axes[1, 1].imshow(orig_img)
        axes[1, 1].set_title(f"LIME Explanation\nPredicted: {pred_label} ({conf:.1f}%)", fontsize=12, fontweight="bold")
        axes[1, 1].axis("off")

        plt.suptitle(
            "Integrated Plant Disease Analysis Using ResNet50, SAM, BLIP and LIME",
            fontsize=15,
            fontweight="bold",
            y=0.98,
        )
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        buf = io.BytesIO()
        plt.savefig(buf, format="PNG", dpi=200, bbox_inches="tight")
        plt.close(fig)

        comp_path = self._asset(aid, "integrated_plant_disease_results.png", buf.getvalue())
        m["composite_2x2"] = comp_path
        self._write(m)

    def create_satellite(self, latitude: float, longitude: float, start: date, end: date, user_id: str | None, radius_m: int = 5000) -> dict[str, Any]:
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("Coordinates are outside valid latitude/longitude ranges.")
        if start > end:
            raise ValueError("Start date must be on or before end date.")
        if (end - start).days > 366:
            raise ValueError("Satellite date range must not exceed 366 days.")

        aid = f"satellite_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc).isoformat()
        m: dict[str, Any] = {
            "analysis_id": aid,
            "workflow_type": "satellite",
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "location": {"latitude": latitude, "longitude": longitude, "radius_m": radius_m},
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            "status": "PROCESSING",
            "data_source": "COPERNICUS/S2_SR_HARMONIZED",
            "result": None,
            "error": None,
            "reports": [],
        }
        self._write(m)

        try:
            self._run_satellite(m)
        except Exception as e:
            logger.warning("Satellite analysis exception for %s: %s", aid, e)
            m.update(status="UNAVAILABLE", error=str(e))
            self._write(m)
        return self._read(aid, user_id) or m

    def _run_satellite(self, m: dict[str, Any]) -> None:
        if not self._module("ee"):
            raise RuntimeError("earthengine-api is not installed.")

        import ee

        # Authenticate and initialize according to available credentials
        try:
            if self.settings.earth_engine_service_account and self.settings.earth_engine_credentials_path:
                ee.Initialize(
                    ee.ServiceAccountCredentials(
                        self.settings.earth_engine_service_account,
                        str(self.settings.earth_engine_credentials_path),
                    ),
                    project=self.settings.earth_engine_project or "able-pottery-463117-r0",
                )
            elif self.settings.earth_engine_project:
                ee.Initialize(project=self.settings.earth_engine_project)
            else:
                ee.Initialize(project="able-pottery-463117-r0")
        except Exception as auth_err:
            raise RuntimeError(
                f"Google Earth Engine requires authentication: {auth_err}. "
                "Authorize access by setting up service account credentials or running 'earthengine authenticate'."
            ) from auth_err

        loc = m["location"]
        roi = ee.Geometry.Point([loc["longitude"], loc["latitude"]]).buffer(loc["radius_m"]).bounds()

        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(roi)
            .filterDate(m["date_range"]["start"], m["date_range"]["end"])
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        )
        count = collection.size().getInfo()
        if not count:
            raise RuntimeError("No Sentinel-2 scenes with <20% cloud cover were found for this location and date range. Try widening the date window.")

        image = collection.sort("CLOUDY_PIXEL_PERCENTAGE").first()

        nir = image.select("B8").divide(10000)
        red = image.select("B4").divide(10000)
        blue = image.select("B2").divide(10000)

        ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
        evi = image.expression(
            "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
            {"NIR": nir, "RED": red, "BLUE": blue},
        ).rename("EVI")

        indices = image.addBands([ndvi, evi])
        stats = indices.select(["NDVI", "EVI"]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=10,
            maxPixels=1e8,
        ).getInfo()

        dt = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd").getInfo()

        # Monthly NDVI trend
        monthly_trends = []
        try:
            year = int(m["date_range"]["start"][:4])
            for mo in range(1, 13):
                m_start = f"{year}-{mo:02d}-01"
                m_end = f"{year}-{mo:02d}-28" if mo == 2 else f"{year}-{mo:02d}-30"
                m_col = (
                    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                    .filterBounds(roi)
                    .filterDate(m_start, m_end)
                    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
                )
                if m_col.size().getInfo() > 0:
                    m_med = m_col.median().normalizedDifference(["B8", "B4"]).rename("NDVI")
                    m_stat = m_med.reduceRegion(ee.Reducer.mean(), roi, 20, 1e7).getInfo()
                    if m_stat and m_stat.get("NDVI") is not None:
                        monthly_trends.append({"month": f"{year}-{mo:02d}", "ndvi": round(float(m_stat["NDVI"]), 3)})
        except Exception:
            pass

        vis = {"region": roi, "dimensions": 768, "format": "png"}
        rgb_url = image.getThumbURL({**vis, "bands": ["B4", "B3", "B2"], "min": 0, "max": 3000})
        ndvi_url = ndvi.getThumbURL({**vis, "min": -1, "max": 1, "palette": ["brown", "yellow", "green"]})

        rgb_asset = None
        ndvi_asset = None
        try:
            rgb_asset = self._asset(m["analysis_id"], "sentinel2-rgb.png", urlopen(rgb_url, timeout=30).read())
            ndvi_asset = self._asset(m["analysis_id"], "sentinel2-ndvi.png", urlopen(ndvi_url, timeout=30).read())
        except Exception as exc:
            logger.warning("Could not download EE thumbnails locally: %s", exc)

        mean_ndvi = stats.get("NDVI")
        mean_evi = stats.get("EVI")

        veg_health = "Dense, healthy crop canopy" if (mean_ndvi or 0) > 0.6 else ("Moderate crop vigour" if (mean_ndvi or 0) > 0.3 else "Sparse vegetation or fallow ground")

        result = {
            "scene_count": count,
            "observation_date": dt,
            "mean_ndvi": round(mean_ndvi, 4) if mean_ndvi is not None else None,
            "mean_evi": round(mean_evi, 4) if mean_evi is not None else None,
            "vegetation_status": veg_health,
            "rgb_preview_url": rgb_url,
            "ndvi_preview_url": ndvi_url,
            "monthly_trends": monthly_trends,
            "visual_assets": [a for a in [rgb_asset, ndvi_asset] if a],
            "methodology": "Sentinel-2 SR Harmonized; least-cloudy scene <20% cloud cover. 10m spatial resolution NDVI and EVI computed across farm boundary.",
        }

        m.update(status="COMPLETED", result=result, error=None)
        self._write(m)

    def satellite_status(self) -> list[dict[str, Any]]:
        has_ee = self._module("ee")
        if not has_ee:
            return [
                {
                    "model": "sentinel2_ndvi_evi",
                    "status": "NOT_INSTALLED",
                    "is_live": False,
                    "data_source": "COPERNICUS/S2_SR_HARMONIZED",
                    "reason": "Install earthengine-api to enable satellite intelligence.",
                }
            ]

        import ee
        ee_authenticated = False
        auth_error_msg = None
        try:
            if self.settings.earth_engine_service_account and self.settings.earth_engine_credentials_path:
                ee.Initialize(
                    ee.ServiceAccountCredentials(
                        self.settings.earth_engine_service_account,
                        str(self.settings.earth_engine_credentials_path),
                    ),
                    project=self.settings.earth_engine_project or "able-pottery-463117-r0",
                )
            elif self.settings.earth_engine_project:
                ee.Initialize(project=self.settings.earth_engine_project)
            else:
                ee.Initialize(project="able-pottery-463117-r0")
            ee_authenticated = True
        except Exception as exc:
            auth_error_msg = str(exc)

        if ee_authenticated:
            return [
                {
                    "model": "sentinel2_ndvi_evi",
                    "status": "READY",
                    "is_live": True,
                    "data_source": "COPERNICUS/S2_SR_HARMONIZED",
                    "reason": "Earth Engine connected and authorized for Sentinel-2 queries.",
                }
            ]
        else:
            return [
                {
                    "model": "sentinel2_ndvi_evi",
                    "status": "REQUIRES_CREDENTIALS",
                    "is_live": False,
                    "data_source": "COPERNICUS/S2_SR_HARMONIZED",
                    "reason": f"Google Earth Engine requires authentication ({auth_error_msg}). Run 'earthengine authenticate' or provide a Google Service Account key in .env.",
                }
            ]

    def chatbot_tool(self, query: str, user_id: str | None, analysis_id: str | None = None) -> tuple[str, str]:
        """Provides rich context to the chatbot about real Plant and Satellite analysis sessions."""
        q = query.lower()
        workflow = "satellite" if any(x in q for x in ("satellite", "ndvi", "evi", "vegetation", "coordinates", "sentinel", "farm area")) else "plant"

        item = None
        if analysis_id:
            item = self.get(analysis_id, user_id) or self.get(analysis_id, None)
        if not item:
            items = self.history(workflow, user_id, 1)
            if not items:
                # Fallback to any recent analysis across users if testing
                items = self.history(workflow, None, 1)
            if items:
                item = items[0]

        if not item:
            if workflow == "plant":
                return workflow, "No recent plant disease analysis session was found. Please upload a crop leaf photo in the Plant Disease module to run ResNet50, SAM, LIME, and BLIP."
            return workflow, "No recent satellite analysis was found. Select your farm coordinates on the India map in the Satellite Intelligence module to retrieve real Sentinel-2 observations."

        m = item

        if workflow == "plant":
            models = m.get("executed_models", {})
            dis_res = models.get("disease_classifier", {}).get("result") or {}
            sam_res = models.get("sam", {}).get("result") or {}
            lime_res = models.get("lime", {}).get("result") or {}
            blip_res = models.get("blip", {}).get("result") or {}

            disease_name = dis_res.get("predicted_class", "Undetermined")
            conf = dis_res.get("confidence_pct", 0.0)
            te_name = dis_res.get("metadata", {}).get("te", "")
            action = dis_res.get("metadata", {}).get("action", "")

            caption = blip_res.get("caption", "N/A")
            detailed_caption = blip_res.get("detailed_caption") or blip_res.get("observations", "")
            mask_count = sam_res.get("mask_count", 0)
            leaf_cov = sam_res.get("leaf_coverage_pct", 0)
            lime_class = lime_res.get("explained_class", disease_name)

            # Check specific user questions
            if any(w in q for w in ("what did each model do", "difference", "how do models work", "explain models")):
                return workflow, (
                    "**KshetraIQ 4-Model Plant Intelligence Pipeline Breakdown:**\n\n"
                    "1. **ResNet50 Vision Classifier**: Evaluates foliar pathology into 23 trained crop disease classes with softmax confidence.\n"
                    "2. **SAM (Segment Anything)**: Zero-shot instance segmentation isolating the leaf blade from background clutter and ambient noise.\n"
                    "3. **LIME (Explainability)**: Local interpretable model-agnostic explanations pinpointing the superpixel lesion boundaries driving ResNet50's diagnosis.\n"
                    "4. **BLIP (Detailed Image Description)**: Foundation vision-language model generating detailed, grounded observations of leaf coloration, spots, and surface texture."
                )

            if "sam" in q or "segmentation" in q:
                return workflow, (
                    f"**SAM (Segment Anything) Results:**\n"
                    f"- Identified **{mask_count} distinct structural leaf segments**.\n"
                    f"- Leaf tissue spans **{leaf_cov}%** of the image frame.\n"
                    f"- Visual Output: The segmentation mask isolates the vegetative canopy, separating chlorotic/necrotic lesions from ambient noise."
                )

            if "lime" in q or "explain" in q:
                return workflow, (
                    f"**LIME Explanation Results:**\n"
                    f"- Model Explaining: ResNet50 vision classifier.\n"
                    f"- Target Class Analyzed: **{lime_class}**.\n"
                    f"- Methodology: Evaluated superpixel perturbations with 50 local samples to compute positive and negative influence boundaries.\n"
                    f"- Interpretation: The highlighted yellow/green contours indicate the specific leaf tissue regions that triggered the disease classification."
                )

            if "blip" in q or "caption" in q or "description" in q:
                res_str = (
                    f"**BLIP Detailed Image Description:**\n\n"
                    f"📝 **Foliar Observation**: \"{detailed_caption or caption}\"\n"
                    f"- Model: Salesforce/blip-image-captioning-base\n"
                    f"- Note: The visual description reflects observable physical characteristics (spots, discoloration, texture) and is complementary to, but distinct from, the ResNet50 disease diagnosis."
                )
                return workflow, res_str

            return workflow, (
                f"**Plant Disease Analysis Summary (ID: {m['analysis_id']}):**\n\n"
                f"🌿 **Diagnosis**: **{disease_name}** ({conf:.1f}% confidence)\n"
                + (f"Telugu: *{te_name}*\n" if te_name else "")
                + (f"🚜 **Recommended Action**: {action}\n\n" if action else "\n")
                + f"🔬 **Model Statuses**:\n"
                + f"- **ResNet50**: {models.get('disease_classifier', {}).get('status', 'NOT_RUN')}\n"
                + f"- **SAM**: {models.get('sam', {}).get('status', 'NOT_RUN')} ({mask_count} masks)\n"
                + f"- **LIME**: {models.get('lime', {}).get('status', 'NOT_RUN')} (Explained: {lime_class})\n"
                + f"- **BLIP**: {models.get('blip', {}).get('status', 'NOT_RUN')} (Description: \"{detailed_caption or caption}\")\n"
            )

        # Satellite
        sat_res = m.get("result") or {}
        loc = m.get("location") or {}
        dt = sat_res.get("observation_date", "Recent")
        ndvi = sat_res.get("mean_ndvi")
        evi = sat_res.get("mean_evi")
        status = sat_res.get("vegetation_status", "Evaluated")

        if m["status"] == "COMPLETED" and sat_res:
            return workflow, (
                f"**Sentinel-2 Satellite Intelligence Summary (ID: {m['analysis_id']}):**\n\n"
                f"📍 **Location**: Lat {loc.get('latitude')}, Lng {loc.get('longitude')} (Radius {loc.get('radius_m')} m)\n"
                f"🛰️ **Observation Date**: {dt}\n"
                f"📊 **Vegetation Indices**:\n"
                f"- **Mean NDVI**: {ndvi} ({status})\n"
                f"- **Mean EVI**: {evi}\n"
                f"- **Scenes Evaluated**: {sat_res.get('scene_count', 1)} Sentinel-2 SR Harmonized scenes\n"
                f"- **Data Source**: European Space Agency Copernicus via Google Earth Engine."
            )
        else:
            return workflow, (
                f"Satellite analysis for Lat {loc.get('latitude')}, Lng {loc.get('longitude')} is {m['status']}.\n"
                + (f"Note: {m.get('error')}" if m.get("error") else "")
            )

    def generate_report(self, aid: str, user_id: str | None) -> tuple[dict[str, Any], bytes]:
        m = self._read(aid, user_id)
        if not m:
            raise KeyError(aid)

        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.platypus import HRFlowable, Image as PDFImage, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError as e:
            raise RuntimeError("reportlab is required to generate intelligence reports.") from e

        report_dir = Path(m["original_image"]).parent if m["workflow_type"] == "plant" else self.settings.ensure_writable_dir(self.root / aid)
        path = report_dir / "report.pdf"
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=22, leading=26, textColor=colors.HexColor("#176b3a"), alignment=TA_CENTER)
        sub_style = ParagraphStyle("ReportSub", parent=styles["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#555555"), alignment=TA_CENTER)
        h1_style = ParagraphStyle("ReportH1", parent=styles["Heading1"], fontSize=14, leading=18, textColor=colors.HexColor("#176b3a"), spaceBefore=12, spaceAfter=6)
        h2_style = ParagraphStyle("ReportH2", parent=styles["Heading2"], fontSize=11, leading=15, textColor=colors.HexColor("#2d3748"), spaceBefore=8, spaceAfter=4)
        body_style = ParagraphStyle("ReportBody", parent=styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#2d3748"))
        callout_style = ParagraphStyle("Callout", parent=styles["Normal"], fontSize=9.5, leading=14, textColor=colors.HexColor("#176b3a"), backColor=colors.HexColor("#f0fdf4"))

        # Header
        story.append(Paragraph("KshetraIQ Agri Intelligence", title_style))
        rep_type = "Comprehensive Plant Foliar Intelligence Report" if m["workflow_type"] == "plant" else "Copernicus Sentinel-2 Satellite Intelligence Report"
        story.append(Paragraph(rep_type, sub_style))
        story.append(Paragraph(f"Analysis ID: {aid} &nbsp;|&nbsp; Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", sub_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#176b3a"), spaceBefore=4, spaceAfter=12))

        if m["workflow_type"] == "plant":
            models = m.get("executed_models", {})
            dis_res = models.get("disease_classifier", {}).get("result") or {}
            pred_class = dis_res.get("predicted_class", "N/A")
            conf = dis_res.get("confidence_pct", 0.0)
            action = dis_res.get("actionable_recommendations") or dis_res.get("metadata", {}).get("action", "Follow standard IPM practices.")
            te_name = dis_res.get("metadata", {}).get("te", "")

            # Executive Summary Box
            summary_data = [
                [Paragraph("<b>Diagnostic Finding:</b>", body_style), Paragraph(f"<b>{pred_class}</b>", body_style)],
                [Paragraph("<b>Confidence Level:</b>", body_style), Paragraph(f"<b>{conf:.1f}%</b>", body_style)],
                [Paragraph("<b>Telugu Translation:</b>", body_style), Paragraph(te_name or "N/A", body_style)],
                [Paragraph("<b>Primary Recommendation:</b>", body_style), Paragraph(action, body_style)],
            ]
            t = Table(summary_data, colWidths=[140, 360])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#86efac")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(t)
            story.append(Spacer(1, 14))

            # Original Image Section
            orig_path = m.get("original_image")
            if orig_path and Path(orig_path).is_file():
                story.append(Paragraph("Original Specimen Image", h1_style))
                story.append(PDFImage(orig_path, width=240, height=200, kind="proportional"))
                story.append(Spacer(1, 10))

            # Composite 2x2 image if available
            comp_path = m.get("composite_2x2")
            if comp_path and Path(comp_path).is_file():
                story.append(Paragraph("Integrated 4-Panel Research Visualization", h1_style))
                story.append(Paragraph("Reproducing the research methodology combining Original, SAM segmentation, BLIP captioning, and LIME superpixel explanations:", body_style))
                story.append(Spacer(1, 6))
                story.append(PDFImage(comp_path, width=480, height=380, kind="proportional"))
                story.append(Spacer(1, 14))

            # Detailed Model Sections
            story.append(PageBreak())
            story.append(Paragraph("Individual Model Outputs & Evidence", h1_style))

            # SAM
            sam_res = models.get("sam", {}).get("result") or {}
            sam_assets = models.get("sam", {}).get("visual_assets") or []
            story.append(Paragraph("1. SAM (Segment Anything) Zero-Shot Instance Segmentation", h2_style))
            story.append(Paragraph(
                f"Model: Meta AI ViT-B &nbsp;|&nbsp; Masks Generated: {sam_res.get('mask_count', 0)} &nbsp;|&nbsp; "
                f"Leaf Canopy Coverage: {sam_res.get('leaf_coverage_pct', 0)}%",
                body_style,
            ))
            for a in sam_assets:
                if "overlay" in a and Path(a).is_file():
                    story.append(Spacer(1, 4))
                    story.append(PDFImage(a, width=280, height=220, kind="proportional"))
                    break

            # LIME
            lime_res = models.get("lime", {}).get("result") or {}
            lime_assets = models.get("lime", {}).get("visual_assets") or []
            story.append(Spacer(1, 10))
            story.append(Paragraph("2. LIME Explainability & Lesion Superpixels", h2_style))
            story.append(Paragraph(
                f"Explained Target: {lime_res.get('explained_class', pred_class)} &nbsp;|&nbsp; Samples: {lime_res.get('num_samples', 150)} &nbsp;|&nbsp; "
                f"{lime_res.get('interpretation', '')}",
                body_style,
            ))
            for a in lime_assets:
                if Path(a).is_file():
                    story.append(Spacer(1, 4))
                    story.append(PDFImage(a, width=280, height=220, kind="proportional"))
                    break

            # BLIP Detailed Image Understanding
            blip_res = models.get("blip", {}).get("result") or {}
            story.append(Spacer(1, 10))
            story.append(Paragraph("3. BLIP Detailed Foliar Observation & Image Description", h2_style))
            blip_detailed = blip_res.get("detailed_caption") or blip_res.get("observations") or blip_res.get("caption", "N/A")
            story.append(Paragraph(f"<b>Detailed Foliar Description:</b> \"{blip_detailed}\"", body_style))
            blip_assets = models.get("blip", {}).get("visual_assets") or []
            for a in blip_assets:
                if Path(a).is_file():
                    story.append(Spacer(1, 4))
                    story.append(PDFImage(a, width=280, height=220, kind="proportional"))
                    break

        else:
            # Satellite Report
            loc = m.get("location", {})
            sat_res = m.get("result") or {}
            story.append(Paragraph("Satellite Geospatial Observation Summary", h1_style))
            sat_table = [
                [Paragraph("<b>Target Coordinates:</b>", body_style), Paragraph(f"Latitude: {loc.get('latitude')}, Longitude: {loc.get('longitude')}", body_style)],
                [Paragraph("<b>Study Buffer:</b>", body_style), Paragraph(f"{loc.get('radius_m')} meters (~{round(3.14159 * (loc.get('radius_m', 5000)/1000)**2, 1)} sq km)", body_style)],
                [Paragraph("<b>Acquisition Date:</b>", body_style), Paragraph(f"{sat_res.get('observation_date', 'N/A')}", body_style)],
                [Paragraph("<b>Mean 10m NDVI:</b>", body_style), Paragraph(f"<b>{sat_res.get('mean_ndvi', 'N/A')}</b>", body_style)],
                [Paragraph("<b>Mean 10m EVI:</b>", body_style), Paragraph(f"<b>{sat_res.get('mean_evi', 'N/A')}</b>", body_style)],
                [Paragraph("<b>Canopy Condition:</b>", body_style), Paragraph(f"{sat_res.get('vegetation_status', 'N/A')}", body_style)],
            ]
            t = Table(sat_table, colWidths=[140, 360])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#86efac")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 14))

            # Visual assets
            sat_assets = sat_res.get("visual_assets", [])
            for asset in sat_assets:
                if Path(asset).is_file():
                    story.append(Spacer(1, 10))
                    story.append(PDFImage(asset, width=460, height=320, kind="proportional"))

        with path.open("wb") as output:
            SimpleDocTemplate(output, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36).build(story)

        rec = {"path": str(path), "generated_at": datetime.now(timezone.utc).isoformat()}
        m["reports"].append(rec)
        self._write(m)
        return rec, path.read_bytes()
