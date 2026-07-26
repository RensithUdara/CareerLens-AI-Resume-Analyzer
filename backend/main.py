"""
CareerLens - entry point.
Wires together the database, API routers, and the server-rendered
Jinja2 frontend pages.

Run with:  uvicorn main:app --reload
"""
import os
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models
from auth import get_current_user_optional
from routers import auth_router, resume_router, analysis_router

# Create tables on startup (fine for SQLite / small projects; use Alembic
# migrations if you move to Postgres in production).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CareerLens", description="AI Resume Analyzer & Career Assistant")

BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(FRONTEND_DIR, "templates"))

app.include_router(auth_router.router)
app.include_router(resume_router.router)
app.include_router(analysis_router.router)


# ---------------- Page routes (server-rendered) ----------------
@app.get("/")
def home(request: Request, user: models.User = Depends(get_current_user_optional)):
    return templates.TemplateResponse("landing.html", {"request": request, "user": user})


@app.get("/register")
def register_page(request: Request, user: models.User = Depends(get_current_user_optional)):
    return templates.TemplateResponse("register.html", {"request": request, "user": user})


@app.get("/login")
def login_page(request: Request, user: models.User = Depends(get_current_user_optional)):
    return templates.TemplateResponse("login.html", {"request": request, "user": user})


@app.get("/dashboard")
def dashboard(request: Request, user: models.User = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    resumes = []
    if user:
        resumes = (
            db.query(models.Resume)
            .filter(models.Resume.user_id == user.id)
            .order_by(models.Resume.uploaded_at.desc())
            .all()
        )
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "resumes": resumes, "active": "dashboard"})


@app.get("/upload")
def upload_page(request: Request, user: models.User = Depends(get_current_user_optional)):
    return templates.TemplateResponse("upload.html", {"request": request, "user": user, "active": "upload"})


@app.get("/compare")
def compare_page(request: Request, user: models.User = Depends(get_current_user_optional)):
    return templates.TemplateResponse("compare.html", {"request": request, "user": user, "active": "compare"})


@app.get("/analysis/{resume_id}")
def analysis_page(resume_id: int, request: Request, user: models.User = Depends(get_current_user_optional)):
    return templates.TemplateResponse("analysis.html", {"request": request, "user": user, "resume_id": resume_id, "active": "analysis"})


@app.get("/tracker")
def tracker_page(request: Request, user: models.User = Depends(get_current_user_optional)):
    return templates.TemplateResponse("tracker.html", {"request": request, "user": user, "active": "tracker"})
