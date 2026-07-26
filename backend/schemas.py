"""
Pydantic schemas used for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime


# ---------- Auth ----------
class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Resume ----------
class ResumeOut(BaseModel):
    id: int
    original_filename: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class ResumeCompareItem(BaseModel):
    id: int
    original_filename: str
    uploaded_at: datetime
    ats_score: Optional[float] = None
    analysis_id: Optional[int] = None


class ResumeDiffLine(BaseModel):
    line_number: int
    before: str
    after: str
    status: str


class ResumeCompareOut(BaseModel):
    before_resume: ResumeCompareItem
    after_resume: ResumeCompareItem
    score_delta: Optional[float] = None
    diff: List[ResumeDiffLine]


# ---------- Analysis ----------
class JobMatchRequest(BaseModel):
    resume_id: int
    job_description: str = Field(min_length=20)


class AnalysisOut(BaseModel):
    id: int
    resume_id: int
    ats_score: float
    job_match_score: Optional[float] = None
    job_description: Optional[str] = None

    technical_skills: List[str] = []
    soft_skills: List[str] = []
    certifications: List[str] = []
    education: List[str] = []
    experience: List[str] = []
    projects: List[str] = []

    ats_strengths: List[str] = []
    ats_weaknesses: List[str] = []

    matching_skills: List[str] = []
    missing_skills: List[str] = []
    recommended_skills: List[str] = []

    suggestions: List[str] = []

    created_at: datetime

    class Config:
        from_attributes = True
