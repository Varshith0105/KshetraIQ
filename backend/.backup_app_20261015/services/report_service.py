import io
import logging
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.assessment import AssessmentResponse, ReportPreview

logger = logging.getLogger(__name__)


class ReportService:
    """Generates official verified PDF reports for completed farm assessments."""

    def create_preview(self, assessment: AssessmentResponse) -> ReportPreview:
        crop_model = next((r for r in assessment.results if r.model_id == "crop-recommendation-v1"), None)
        pred = crop_model.prediction if crop_model else None

        return ReportPreview(
            assessment_id=assessment.assessment_id,
            farm_name=assessment.input.farm_name,
            location=f"{assessment.input.district}, {assessment.input.state}",
            acreage=assessment.input.acreage,
            season=assessment.input.season,
            soil={
                "N (kg/ha)": assessment.input.soil.nitrogen_kg_ha,
                "P (kg/ha)": assessment.input.soil.phosphorus_kg_ha,
                "K (kg/ha)": assessment.input.soil.potassium_kg_ha,
                "pH": assessment.input.soil.ph,
            },
            weather={
                "Temperature (°C)": assessment.input.weather.temperature_c if assessment.input.weather else None,
                "Humidity (%)": assessment.input.weather.humidity_percent if assessment.input.weather else None,
                "Rainfall (mm)": assessment.input.weather.rainfall_mm if assessment.input.weather else None,
            },
            recommended_crop=pred.recommended_crop.upper() if pred else "Needs Verified Inputs",
            confidence=round(pred.confidence * 100, 1) if pred else None,
            model_id="crop-recommendation-v1",
            confirmation_prompt=(
                f"Confirm generating the formal PDF report for {assessment.input.farm_name}? "
                "This will compile verified soil analysis, weather observations, and model predictions."
            ),
            confirmation_prompt_te=(
                f"{assessment.input.farm_name} కొరకు అధికారిక PDF నివేదికను రూపొందించడానికి నిర్ధారించాలా? "
                "ఇది నేల విశ్లేషణ, వాతావరణం మరియు AI సిఫార్సులతో నివేదికను తయారుచేస్తుంది."
            ),
            disclaimer="The generated PDF includes traceable model versions and explicit agronomic assumptions.",
        )

    def generate_pdf(self, assessment: AssessmentResponse) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1b4332"),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#495057"),
            spaceAfter=12,
        )
        section_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#2d6a4f"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#212529"),
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Italic"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#6c757d"),
        )

        story = []

        # 1. Header
        story.append(Paragraph("KshetraIQ — Agricultural Assessment & Crop Advisory Report", title_style))
        story.append(
            Paragraph(
                f"Reference ID: <b>{assessment.assessment_id}</b> | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                subtitle_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2d6a4f"), spaceAfter=12))

        # 2. Farm Profile Table
        story.append(Paragraph("1. Farm & Location Profile", section_style))
        farm_data = [
            [
                Paragraph("<b>Farm Name:</b>", body_style),
                Paragraph(assessment.input.farm_name, body_style),
                Paragraph("<b>Land Area:</b>", body_style),
                Paragraph(f"{assessment.input.acreage} Acres", body_style),
            ],
            [
                Paragraph("<b>District:</b>", body_style),
                Paragraph(assessment.input.district, body_style),
                Paragraph("<b>State:</b>", body_style),
                Paragraph(assessment.input.state, body_style),
            ],
            [
                Paragraph("<b>Season:</b>", body_style),
                Paragraph(assessment.input.season, body_style),
                Paragraph("<b>Irrigation Type:</b>", body_style),
                Paragraph(f"{assessment.input.irrigation_type} ({assessment.input.water_availability})", body_style),
            ],
        ]
        t_farm = Table(farm_data, colWidths=[100, 160, 100, 180])
        t_farm.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(t_farm)
        story.append(Spacer(1, 10))

        # 3. Verified Soil Measurements & Weather
        story.append(Paragraph("2. Soil Analysis & Sourced Weather Observations", section_style))
        soil = assessment.input.soil
        weather = assessment.input.weather
        env_data = [
            [
                Paragraph("<b>Parameter</b>", body_style),
                Paragraph("<b>Reported / Sourced Value</b>", body_style),
                Paragraph("<b>Unit / Context</b>", body_style),
                Paragraph("<b>Status / Source</b>", body_style),
            ],
            [
                Paragraph("Nitrogen (N)", body_style),
                Paragraph(str(soil.nitrogen_kg_ha) if soil.nitrogen_kg_ha is not None else "N/A", body_style),
                Paragraph("kg/ha", body_style),
                Paragraph("Soil lab test", body_style),
            ],
            [
                Paragraph("Phosphorus (P)", body_style),
                Paragraph(str(soil.phosphorus_kg_ha) if soil.phosphorus_kg_ha is not None else "N/A", body_style),
                Paragraph("kg/ha", body_style),
                Paragraph("Soil lab test", body_style),
            ],
            [
                Paragraph("Potassium (K)", body_style),
                Paragraph(str(soil.potassium_kg_ha) if soil.potassium_kg_ha is not None else "N/A", body_style),
                Paragraph("kg/ha", body_style),
                Paragraph("Soil lab test", body_style),
            ],
            [
                Paragraph("Soil pH", body_style),
                Paragraph(str(soil.ph) if soil.ph is not None else "N/A", body_style),
                Paragraph("scale 0 - 14", body_style),
                Paragraph("Soil lab test", body_style),
            ],
            [
                Paragraph("Temperature", body_style),
                Paragraph(f"{weather.temperature_c} °C" if weather and weather.temperature_c is not None else "N/A", body_style),
                Paragraph("Celsius", body_style),
                Paragraph(assessment.weather_source, body_style),
            ],
            [
                Paragraph("Relative Humidity", body_style),
                Paragraph(f"{weather.humidity_percent} %" if weather and weather.humidity_percent is not None else "N/A", body_style),
                Paragraph("Percentage", body_style),
                Paragraph(assessment.weather_source, body_style),
            ],
            [
                Paragraph("Seasonal Rainfall", body_style),
                Paragraph(f"{weather.rainfall_mm} mm" if weather and weather.rainfall_mm is not None else "N/A", body_style),
                Paragraph("Millimeters", body_style),
                Paragraph(assessment.weather_source, body_style),
            ],
        ]
        t_env = Table(env_data, colWidths=[130, 140, 110, 160])
        t_env.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9ecef")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ced4da")),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t_env)
        story.append(Spacer(1, 10))

        # 4. Verified Crop Recommendation
        story.append(Paragraph("3. Verified Model Prediction (Crop Recommendation)", section_style))
        crop_model = next((r for r in assessment.results if r.model_id == "crop-recommendation-v1"), None)
        pred = crop_model.prediction if crop_model else None

        if pred:
            rec_text = f"<b>Recommended Crop:</b> <font size=12 color='#1b4332'><b>{pred.recommended_crop.upper()}</b></font> ({pred.recommended_crop_te})"
            conf_text = f"<b>Model Confidence:</b> {round(pred.confidence * 100, 1)}% | <b>Model ID:</b> {pred.model_id} ({pred.algorithm})"
            alts = ", ".join([f"{c.crop.capitalize()} ({round(c.confidence*100, 1)}%)" for c in pred.top_candidates[1:4]])
            alt_text = f"<b>Alternative Suitable Crops:</b> {alts if alts else 'None identified within threshold'}"

            pred_data = [
                [Paragraph(rec_text, body_style)],
                [Paragraph(conf_text, body_style)],
                [Paragraph(alt_text, body_style)],
            ]
        else:
            pred_data = [
                [Paragraph("<b>Status:</b> Prediction pending verified inputs.", body_style)],
                [Paragraph(f"<b>Notice:</b> {crop_model.message if crop_model else 'Artifact not loaded.'}", body_style)],
            ]

        t_pred = Table(pred_data, colWidths=[540])
        t_pred.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#d8f3dc")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#52b788")),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(t_pred)
        story.append(Spacer(1, 10))

        # 5. Agronomic Advisor Guidance
        if assessment.advisor:
            adv = assessment.advisor
            story.append(Paragraph(f"4. Agricultural Advisory ({adv.provider_note})", section_style))
            adv_text = [
                Paragraph(f"<b>Summary:</b> {adv.summary}", body_style),
                Spacer(1, 4),
                Paragraph(f"<b>Soil Assessment:</b> {adv.soil_health_assessment.get('ph_note', '')}", body_style),
                Spacer(1, 4),
                Paragraph(f"<b>Crop Guidance:</b> {adv.crop_guidance.get('best_practices', '')}", body_style),
                Spacer(1, 4),
                Paragraph(f"<b>Irrigation Protocol:</b> {adv.water_and_irrigation.get('recommendation', '')}", body_style),
            ]
            t_adv = Table([[adv_text]], colWidths=[540])
            t_adv.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#ced4da")),
                        ("PADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(t_adv)
            story.append(Spacer(1, 10))

        # 6. Model Registry Transparency Status
        story.append(Paragraph("5. AI System Registry Status & Integrity Audit", section_style))
        reg_rows = [
            [
                Paragraph("<b>Module Name</b>", body_style),
                Paragraph("<b>Status</b>", body_style),
                Paragraph("<b>Audit Note</b>", body_style),
            ]
        ]
        for res in assessment.results:
            reg_rows.append(
                [
                    Paragraph(res.model_id, body_style),
                    Paragraph(f"<b>{res.status.upper()}</b>", body_style),
                    Paragraph(res.message, body_style),
                ]
            )
        t_reg = Table(reg_rows, colWidths=[150, 100, 290])
        t_reg.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9ecef")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t_reg)
        story.append(Spacer(1, 12))

        # 7. Assumptions & Disclaimer
        story.append(
            Paragraph(
                "<b>Notice & Legal Disclaimer:</b> KshetraIQ never infers laboratory soil values from photos. "
                "All predictions represent statistical inferences based on the verified Random Forest model trained on verified agricultural parameters. "
                "Always verify advice with your local Agricultural Officer / KVK before purchasing inputs.",
                disclaimer_style,
            )
        )

        doc.build(story)
        return buffer.getvalue()
