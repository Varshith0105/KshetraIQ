"""KshetraIQ Soil Report Extraction Service.

Parses digital PDF Soil Health Cards and laboratory test reports, extracting
Nitrogen (N), Phosphorus (P), Potassium (K), pH, EC, Organic Carbon, soil texture,
and testing laboratory metadata with transparent confidence flags.
"""

from __future__ import annotations

import io
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class SoilReportParser:
    """Extracts agronomic soil parameters from uploaded documents."""

    def extract_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Extract candidate soil chemistry measurements from file content."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""

        if ext == "pdf" or (content_type and "pdf" in content_type):
            return self._parse_pdf(file_bytes, filename)

        if ext in ("jpg", "jpeg", "png", "webp"):
            return self._handle_image(file_bytes, filename)

        return {
            "status": "unsupported_format",
            "message": f"Unsupported file extension '.{ext}'. Please upload a digital PDF Soil Health Card or laboratory report.",
            "parameters": {},
            "raw_text_snippet": None,
        }

    def _parse_pdf(self, pdf_bytes: bytes, filename: str) -> dict[str, Any]:
        """Extract text from PDF pages and regex-match soil chemistry indicators."""
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(pdf_bytes))
            text_pages: list[str] = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_pages.append(page_text)

            full_text = "\n".join(text_pages).strip()
            if not full_text:
                return {
                    "status": "scanned_pdf_needs_ocr",
                    "message": "The uploaded PDF appears to be a scanned image without selectable text. Please enter values manually or upload a digital PDF.",
                    "parameters": {},
                    "raw_text_snippet": None,
                }

            params = self._extract_parameters_from_text(full_text)
            has_any = any(v is not None for v in params.values())

            snippet = full_text[:400].replace("\n", " ").strip()

            return {
                "status": "extracted" if has_any else "no_parameters_found",
                "source": "uploaded_report",
                "filename": filename,
                "parameters": params,
                "raw_text_snippet": snippet if snippet else None,
                "message": (
                    "Soil parameters extracted from digital report. Please review and confirm the values before applying to your assessment."
                    if has_any
                    else "Could not locate standard NPK or pH test indicators in this PDF document. Please verify the report format or enter values manually."
                ),
            }

        except Exception as e:
            logger.exception("PDF extraction failed: %s", e)
            return {
                "status": "extraction_error",
                "message": f"Failed to parse PDF document: {str(e)}",
                "parameters": {},
                "raw_text_snippet": None,
            }

    def _handle_image(self, image_bytes: bytes, filename: str) -> dict[str, Any]:
        """Explain that raw leaf/dirt photographs cannot measure chemical NPK/pH without lab test."""
        return {
            "status": "requires_certified_report",
            "message": (
                "Field photographs and soil surface images cannot provide scientifically valid NPK or pH measurements without chemical laboratory reagents. "
                "Please upload a certified Soil Health Card (PDF / Lab Certificate) or enter your soil laboratory measurements manually."
            ),
            "parameters": {},
            "raw_text_snippet": None,
        }

    def _extract_parameters_from_text(self, text: str) -> dict[str, Any]:
        """Regex-based parameter extraction from text."""
        result: dict[str, Any] = {
            "nitrogen": None,
            "phosphorus": None,
            "potassium": None,
            "ph": None,
            "ec": None,
            "organic_carbon": None,
            "soil_type": None,
            "lab_name": None,
            "report_date": None,
        }

        # 1. Nitrogen (N)
        # 1. Nitrogen (N)
        # Matches patterns like: Nitrogen: 85.5 kg/ha, Available Nitrogen (N): 140, Available N: 90, N = 80
        n_match = re.search(
            r"(?:Available\s+)?(?:Nitrogen(?:\s*\([nN]\))?|Available\s+N|\bN\b)\s*[:=–-]?\s*([0-9]{1,4}(?:\.[0-9]+)?)\s*(?:kg\/ha|kg\/acre|ppm)?",
            text,
            re.IGNORECASE,
        )
        if n_match:
            try:
                val = float(n_match.group(1))
                if 0.0 <= val <= 1000.0:
                    result["nitrogen"] = {
                        "value": val,
                        "unit": "kg/ha",
                        "confidence": 0.95,
                        "needs_confirmation": False,
                    }
            except ValueError:
                pass

        # 2. Phosphorus (P)
        p_match = re.search(
            r"(?:Available\s+)?(?:Phosphorus(?:\s*\([pP]\))?|Available\s+P|P2O5|\bP\b)\s*[:=–-]?\s*([0-9]{1,3}(?:\.[0-9]+)?)\s*(?:kg\/ha|kg\/acre|ppm)?",
            text,
            re.IGNORECASE,
        )
        if p_match:
            try:
                val = float(p_match.group(1))
                if 0.0 <= val <= 500.0:
                    result["phosphorus"] = {
                        "value": val,
                        "unit": "kg/ha",
                        "confidence": 0.95,
                        "needs_confirmation": False,
                    }
            except ValueError:
                pass

        # 3. Potassium (K)
        k_match = re.search(
            r"(?:Available\s+)?(?:Potassium(?:\s*\([kK]\))?|Available\s+K|K2O|\bK\b)\s*[:=–-]?\s*([0-9]{1,4}(?:\.[0-9]+)?)\s*(?:kg\/ha|kg\/acre|ppm)?",
            text,
            re.IGNORECASE,
        )
        if k_match:
            try:
                val = float(k_match.group(1))
                if 0.0 <= val <= 1000.0:
                    result["potassium"] = {
                        "value": val,
                        "unit": "kg/ha",
                        "confidence": 0.95,
                        "needs_confirmation": False,
                    }
            except ValueError:
                pass

        # 4. pH
        ph_match = re.search(
            r"(?:Soil\s+)?(?:pH|Reaction(?:\s*\([pP][hH]\))?)\s*[:=–-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            text,
            re.IGNORECASE,
        )
        if ph_match:
            try:
                val = float(ph_match.group(1))
                if 2.0 <= val <= 12.0:
                    result["ph"] = {
                        "value": val,
                        "unit": "pH scale",
                        "confidence": 0.98,
                        "needs_confirmation": False,
                    }
            except ValueError:
                pass

        # 5. Electrical Conductivity (EC)
        ec_match = re.search(
            r"(?:Electrical\s+Conductivity(?:\s*\([eE][cC]\))?|\bEC\b)\s*[:=–-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:dS\/m|mmhos\/cm)?",
            text,
            re.IGNORECASE,
        )
        if ec_match:
            try:
                val = float(ec_match.group(1))
                if 0.0 <= val <= 20.0:
                    result["ec"] = {
                        "value": val,
                        "unit": "dS/m",
                        "confidence": 0.92,
                        "needs_confirmation": False,
                    }
            except ValueError:
                pass

        # 6. Organic Carbon (OC)
        oc_match = re.search(
            r"(?:Organic\s+Carbon(?:\s*\([oO][cC]\))?|\bOC\b)\s*[:=–-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent)?",
            text,
            re.IGNORECASE,
        )
        if oc_match:
            try:
                val = float(oc_match.group(1))
                if 0.0 <= val <= 15.0:
                    result["organic_carbon"] = {
                        "value": val,
                        "unit": "%",
                        "confidence": 0.90,
                        "needs_confirmation": False,
                    }
            except ValueError:
                pass

        # 7. Soil Type / Texture
        texture_match = re.search(
            r"(?:Soil\s+Type|Soil\s+Texture|Texture)\s*[:=–-]?\s*([A-Za-z\s]{3,25})",
            text,
            re.IGNORECASE,
        )
        if texture_match:
            t_raw = texture_match.group(1).strip()
            # Common soil types in Indian agriculture
            for st in ("Clay Loam", "Sandy Loam", "Silt Loam", "Clay", "Loam", "Black Soil", "Red Soil", "Alluvial", "Sandy"):
                if st.lower() in t_raw.lower():
                    result["soil_type"] = {
                        "value": st,
                        "confidence": 0.88,
                        "needs_confirmation": True,
                    }
                    break

        # 8. Lab Name
        lab_match = re.search(
            r"(?:Testing\s+Laboratory|Soil\s+Testing\s+Lab|STC|Lab(?:\s+Name)?)\s*[:=–-]?\s*([A-Za-z0-9\s,\.\-]{4,60})",
            text,
            re.IGNORECASE,
        )
        if lab_match:
            result["lab_name"] = lab_match.group(1).strip()

        # 9. Report Date
        date_match = re.search(
            r"(?:Sample\s+Date|Analysis\s+Date|Issue\s+Date|Date)\s*[:=–-]?\s*([0-9]{1,4}[/\-\.][0-9]{1,2}[/\-\.][0-9]{1,4})",
            text,
            re.IGNORECASE,
        )
        if date_match:
            result["report_date"] = date_match.group(1).strip()

        return result


soil_report_parser = SoilReportParser()
