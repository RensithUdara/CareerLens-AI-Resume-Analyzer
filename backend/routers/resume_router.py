"""
Resume upload + history and comparison endpoints.
"""
import difflib
import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from auth import get_current_user
from resume_parser import extract_text

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE_MB = 5


@router.post("/upload", response_model=schemas.ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large (max {MAX_FILE_SIZE_MB}MB).")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as f:
        f.write(contents)

    try:
        raw_text = extract_text(stored_path)
    except Exception as exc:
        os.remove(stored_path)
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")

    if not raw_text or len(raw_text.strip()) < 30:
        os.remove(stored_path)
        raise HTTPException(status_code=400, detail="Couldn't extract meaningful text from this file. "
                                                      "Try exporting it as a standard PDF/DOCX (not a scanned image).")

    resume = models.Resume(
        user_id=current_user.id,
        original_filename=file.filename,
        stored_path=stored_path,
        raw_text=raw_text,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/history", response_model=list[schemas.ResumeOut])
def resume_history(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(models.Resume)
        .filter(models.Resume.user_id == current_user.id)
        .order_by(models.Resume.uploaded_at.desc())
        .all()
    )


def _latest_analysis(resume_id: int, user_id: int, db: Session) -> models.Analysis | None:
    return (
        db.query(models.Analysis)
        .filter(models.Analysis.resume_id == resume_id, models.Analysis.user_id == user_id)
        .order_by(models.Analysis.created_at.desc())
        .first()
    )


def _resume_compare_item(resume: models.Resume, analysis: models.Analysis | None) -> dict:
    return {
        "id": resume.id,
        "original_filename": resume.original_filename,
        "uploaded_at": resume.uploaded_at,
        "ats_score": analysis.ats_score if analysis else None,
        "analysis_id": analysis.id if analysis else None,
    }


@router.get("/compare", response_model=schemas.ResumeCompareOut)
def compare_resumes(
    before_id: int = Query(..., gt=0),
    after_id: int = Query(..., gt=0),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if before_id == after_id:
        raise HTTPException(status_code=400, detail="Choose two different resume versions to compare.")

    resumes = (
        db.query(models.Resume)
        .filter(
            models.Resume.user_id == current_user.id,
            models.Resume.id.in_([before_id, after_id]),
        )
        .all()
    )
    by_id = {resume.id: resume for resume in resumes}
    before_resume = by_id.get(before_id)
    after_resume = by_id.get(after_id)
    if not before_resume or not after_resume:
        raise HTTPException(status_code=404, detail="One or both resume versions were not found.")

    before_lines = (before_resume.raw_text or "").splitlines()
    after_lines = (after_resume.raw_text or "").splitlines()
    diff_lines = []
    before_line_number = 0
    after_line_number = 0

    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, before_lines, after_lines).get_opcodes():
        if tag == "equal":
            for before_text, after_text in zip(before_lines[i1:i2], after_lines[j1:j2]):
                before_line_number += 1
                after_line_number += 1
                diff_lines.append({
                    "line_number": after_line_number,
                    "before": before_text,
                    "after": after_text,
                    "status": "same",
                })
        elif tag == "replace":
            before_chunk = before_lines[i1:i2]
            after_chunk = after_lines[j1:j2]
            max_len = max(len(before_chunk), len(after_chunk))
            for index in range(max_len):
                before_text = before_chunk[index] if index < len(before_chunk) else ""
                after_text = after_chunk[index] if index < len(after_chunk) else ""
                if before_text:
                    before_line_number += 1
                if after_text:
                    after_line_number += 1
                diff_lines.append({
                    "line_number": after_line_number or before_line_number,
                    "before": before_text,
                    "after": after_text,
                    "status": "changed",
                })
        elif tag == "delete":
            for before_text in before_lines[i1:i2]:
                before_line_number += 1
                diff_lines.append({
                    "line_number": before_line_number,
                    "before": before_text,
                    "after": "",
                    "status": "removed",
                })
        elif tag == "insert":
            for after_text in after_lines[j1:j2]:
                after_line_number += 1
                diff_lines.append({
                    "line_number": after_line_number,
                    "before": "",
                    "after": after_text,
                    "status": "added",
                })

    before_analysis = _latest_analysis(before_resume.id, current_user.id, db)
    after_analysis = _latest_analysis(after_resume.id, current_user.id, db)
    score_delta = None
    if before_analysis and after_analysis:
        score_delta = after_analysis.ats_score - before_analysis.ats_score

    return {
        "before_resume": _resume_compare_item(before_resume, before_analysis),
        "after_resume": _resume_compare_item(after_resume, after_analysis),
        "score_delta": score_delta,
        "diff": diff_lines,
    }
