"""
The core "AI analysis" endpoints: run analysis, match a job description,
track improvement over time, and download the PDF report.
"""
import csv
import io
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from auth import get_current_user
import ai_analysis
from pdf_report import build_report

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


def _get_owned_resume(resume_id: int, current_user: models.User, db: Session) -> models.Resume:
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.id == resume_id, models.Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return resume


@router.post("/{resume_id}", response_model=schemas.AnalysisOut)
def run_analysis(resume_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = _get_owned_resume(resume_id, current_user, db)

    result = ai_analysis.analyze_resume(resume.raw_text)

    analysis = models.Analysis(
        resume_id=resume.id,
        user_id=current_user.id,
        ats_score=result["ats_score"],
        technical_skills=result["technical_skills"],
        soft_skills=result["soft_skills"],
        certifications=result["certifications"],
        education=result["education"],
        experience=result["experience"],
        projects=result["projects"],
        ats_strengths=result["ats_strengths"],
        ats_weaknesses=result["ats_weaknesses"],
        suggestions=result["suggestions"],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.post("/{resume_id}/job-match", response_model=schemas.AnalysisOut)
def job_match(
    resume_id: int,
    payload: schemas.JobMatchRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = _get_owned_resume(resume_id, current_user, db)

    # Reuse the most recent analysis for this resume if one exists, otherwise create one.
    analysis = (
        db.query(models.Analysis)
        .filter(models.Analysis.resume_id == resume.id)
        .order_by(models.Analysis.created_at.desc())
        .first()
    )
    if not analysis:
        base = ai_analysis.analyze_resume(resume.raw_text)
        analysis = models.Analysis(resume_id=resume.id, user_id=current_user.id, ats_score=base["ats_score"],
                                    technical_skills=base["technical_skills"], soft_skills=base["soft_skills"],
                                    certifications=base["certifications"], education=base["education"],
                                    experience=base["experience"], projects=base["projects"],
                                    ats_strengths=base["ats_strengths"], ats_weaknesses=base["ats_weaknesses"],
                                    suggestions=base["suggestions"])
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

    match = ai_analysis.match_job_description(resume.raw_text, payload.job_description, analysis.technical_skills or [])

    analysis.job_description = payload.job_description
    analysis.job_match_score = match["similarity_percentage"]
    analysis.matching_skills = match["matching_skills"]
    analysis.missing_skills = match["missing_skills"]
    analysis.recommended_skills = match["recommended_skills"]
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get("/history/export.csv")
def export_analysis_history_csv(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = (
        db.query(models.Analysis)
        .join(models.Resume, models.Resume.id == models.Analysis.resume_id)
        .filter(models.Analysis.user_id == current_user.id)
        .order_by(models.Analysis.created_at.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "analysis_id",
        "resume_id",
        "resume_filename",
        "analysis_created_at",
        "ats_score",
        "job_match_score",
        "technical_skills",
        "soft_skills",
        "missing_skills",
        "recommended_skills",
        "suggestions",
    ])

    def join_items(items):
        return "; ".join(str(item) for item in (items or []))

    for analysis in analyses:
        writer.writerow([
            analysis.id,
            analysis.resume_id,
            analysis.resume.original_filename if analysis.resume else "",
            analysis.created_at.isoformat() if analysis.created_at else "",
            round(analysis.ats_score or 0, 2),
            round(analysis.job_match_score, 2) if analysis.job_match_score is not None else "",
            join_items(analysis.technical_skills),
            join_items(analysis.soft_skills),
            join_items(analysis.missing_skills),
            join_items(analysis.recommended_skills),
            join_items(analysis.suggestions),
        ])

    output.seek(0)
    headers = {"Content-Disposition": "attachment; filename=careerlens_analysis_history.csv"}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)


@router.get("/history/{resume_id}", response_model=list[schemas.AnalysisOut])
def analysis_history(resume_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_owned_resume(resume_id, current_user, db)
    return (
        db.query(models.Analysis)
        .filter(models.Analysis.resume_id == resume_id)
        .order_by(models.Analysis.created_at.desc())
        .all()
    )


@router.get("/tracker/all")
def improvement_tracker(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns every analysis for this user ordered oldest -> newest so the
    frontend can plot ATS score improvement over time across resume versions.
    """
    analyses = (
        db.query(models.Analysis)
        .filter(models.Analysis.user_id == current_user.id)
        .order_by(models.Analysis.created_at.asc())
        .all()
    )
    return [
        {
            "id": a.id,
            "resume_id": a.resume_id,
            "ats_score": a.ats_score,
            "created_at": a.created_at,
        }
        for a in analyses
    ]


@router.get("/{analysis_id}/report")
def download_report(analysis_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = (
        db.query(models.Analysis)
        .filter(models.Analysis.id == analysis_id, models.Analysis.user_id == current_user.id)
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    resume = db.query(models.Resume).filter(models.Resume.id == analysis.resume_id).first()

    os.makedirs(REPORTS_DIR, exist_ok=True)
    output_path = os.path.join(REPORTS_DIR, f"careerlens_report_{analysis.id}.pdf")
    build_report(analysis, resume.original_filename, output_path)

    return FileResponse(output_path, media_type="application/pdf", filename=f"CareerLens_Report_{analysis.id}.pdf")
