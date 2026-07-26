"""
Generates a downloadable PDF summary of one analysis using ReportLab.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

NAVY = colors.HexColor("#1B3A6B")
LIGHT_BLUE = colors.HexColor("#EAF2FB")
ACCENT = colors.HexColor("#3E7CB1")


def build_report(analysis, resume_filename: str, output_path: str) -> str:
    """analysis is a models.Analysis SQLAlchemy object."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleBlue", parent=styles["Title"], textColor=NAVY)
    heading_style = ParagraphStyle("HeadingBlue", parent=styles["Heading2"], textColor=ACCENT, spaceBefore=14)
    body_style = styles["BodyText"]

    story = []
    story.append(Paragraph("CareerLens Analysis Report", title_style))
    story.append(Paragraph(f"Resume file: {resume_filename}", body_style))
    story.append(Spacer(1, 12))

    # --- ATS score table ---
    story.append(Paragraph("ATS Compatibility Score", heading_style))
    score_table = Table(
        [["ATS Score", f"{analysis.ats_score:.0f}%"]],
        colWidths=[8 * cm, 4 * cm],
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, ACCENT),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 10))

    def bullet_list(items):
        return ListFlowable(
            [ListItem(Paragraph(item, body_style)) for item in items] or
            [ListItem(Paragraph("None detected", body_style))],
            bulletType="bullet",
        )

    story.append(Paragraph("Strengths", heading_style))
    story.append(bullet_list(analysis.ats_strengths or []))

    story.append(Paragraph("Needs Improvement", heading_style))
    story.append(bullet_list(analysis.ats_weaknesses or []))

    if analysis.job_match_score is not None:
        story.append(Paragraph("Job Description Match", heading_style))
        story.append(Paragraph(f"Similarity: {analysis.job_match_score:.0f}%", body_style))
        story.append(Paragraph("Missing skills for this job:", body_style))
        story.append(bullet_list(analysis.missing_skills or []))

    story.append(Paragraph("Skill Gap Analysis", heading_style))
    story.append(Paragraph("Current skills:", body_style))
    story.append(bullet_list(analysis.technical_skills or []))
    story.append(Paragraph("Recommended skills to learn:", body_style))
    story.append(bullet_list(analysis.recommended_skills or []))

    story.append(Paragraph("AI Suggestions", heading_style))
    story.append(bullet_list(analysis.suggestions or []))

    doc.build(story)
    return output_path
