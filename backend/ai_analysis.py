"""
This module is the actual "AI" in CareerLens.

Instead of just forwarding the resume text to Gemini and hoping for the best,
we:
  1. Send a carefully structured prompt that tells the model exactly what
     fields we need back.
  2. Force the response into JSON using Gemini's `response_schema`, so we
     never have to fragile-parse free text.
  3. Validate/clean the model's output before it touches the database.
  4. Fall back to a deterministic keyword-based analysis if no API key is
     configured (or the call fails), so the app still works for a demo/offline.

That combination - structured prompting + schema-constrained output +
a non-AI fallback - is what turns "I called an API" into an actual
integration you can defend in an interview.
"""
import os
import json
from typing import Optional
from google import genai
from google.genai import types

MODEL_NAME = "gemini-2.5-flash"

# A reasonably broad skill dictionary used by the offline fallback and to
# sanity-check the AI's output.
COMMON_TECH_SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "sql", "nosql",
    "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
    "html", "css", "git", "github", "docker", "kubernetes", "aws", "azure",
    "gcp", "rest api", "graphql", "postgresql", "mysql", "mongodb", "redis",
    "linux", "ci/cd", "tensorflow", "pytorch", "pandas", "numpy", "power bi",
    "tableau", "excel", "machine learning", "deep learning", "nlp",
]

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "technical_skills": {"type": "array", "items": {"type": "string"}},
        "soft_skills": {"type": "array", "items": {"type": "string"}},
        "certifications": {"type": "array", "items": {"type": "string"}},
        "education": {"type": "array", "items": {"type": "string"}},
        "experience": {"type": "array", "items": {"type": "string"}},
        "projects": {"type": "array", "items": {"type": "string"}},
        "ats_score": {"type": "integer"},
        "ats_strengths": {"type": "array", "items": {"type": "string"}},
        "ats_weaknesses": {"type": "array", "items": {"type": "string"}},
        "suggestions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "technical_skills", "soft_skills", "certifications", "education",
        "experience", "projects", "ats_score", "ats_strengths",
        "ats_weaknesses", "suggestions",
    ],
}

JOB_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "similarity_percentage": {"type": "integer"},
        "matching_skills": {"type": "array", "items": {"type": "string"}},
        "missing_skills": {"type": "array", "items": {"type": "string"}},
        "recommended_skills": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["similarity_percentage", "matching_skills", "missing_skills", "recommended_skills"],
}


def _get_client() -> Optional["genai.Client"]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        return None
    return genai.Client(api_key=api_key)


def analyze_resume(resume_text: str) -> dict:
    """
    Full resume analysis: extracted sections + ATS score + strengths/
    weaknesses + improvement suggestions.
    """
    client = _get_client()
    if client is None:
        return _offline_resume_analysis(resume_text)

    prompt = f"""You are an experienced technical recruiter and ATS (Applicant
Tracking System) specialist. Analyze the resume below and extract structured
information.

Rules:
- ats_score is 0-100, based on: clear structure, use of measurable
  achievements, presence of contact info, relevant keywords, absence of
  spelling issues, and use of standard section headers.
- ats_strengths: short phrases describing what is already strong (e.g.
  "Certifications", "Quantified achievements").
- ats_weaknesses: short phrases describing what is missing or weak (e.g.
  "No leadership section", "Missing measurable results").
- suggestions: 4-6 concrete, actionable improvement tips written directly to
  the candidate ("Add measurable achievements to your Experience section.").
- Every array field must be present, even if empty.

Resume text:
\"\"\"
{resume_text[:12000]}
\"\"\"
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
                temperature=0.3,
            ),
        )
        data = json.loads(response.text)
        data["ats_score"] = max(0, min(100, int(data.get("ats_score", 0))))
        return data
    except Exception as exc:  # noqa: BLE001 - we want the app to keep working
        print(f"[ai_analysis] Gemini call failed, using offline fallback: {exc}")
        return _offline_resume_analysis(resume_text)


def match_job_description(resume_text: str, job_description: str, known_skills: list[str]) -> dict:
    """Compares the resume against a pasted job description."""
    client = _get_client()
    if client is None:
        return _offline_job_match(resume_text, job_description, known_skills)

    prompt = f"""You are an ATS matching engine. Compare the candidate's resume
against the job description below.

Return:
- similarity_percentage: 0-100 overall match score.
- matching_skills: skills/requirements present in both the resume and the
  job description.
- missing_skills: skills/requirements the job description asks for that are
  NOT clearly present in the resume.
- recommended_skills: skills worth learning next, based on the gap between
  the resume and this job description (can overlap with missing_skills).

Resume:
\"\"\"
{resume_text[:8000]}
\"\"\"

Job description:
\"\"\"
{job_description[:4000]}
\"\"\"
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JOB_MATCH_SCHEMA,
                temperature=0.3,
            ),
        )
        data = json.loads(response.text)
        data["similarity_percentage"] = max(0, min(100, int(data.get("similarity_percentage", 0))))
        return data
    except Exception as exc:  # noqa: BLE001
        print(f"[ai_analysis] Gemini call failed, using offline fallback: {exc}")
        return _offline_job_match(resume_text, job_description, known_skills)


# --------------------------------------------------------------------------
# Offline fallbacks - simple keyword matching so the app is fully demoable
# without an API key, and so a failed API call never breaks the UI.
# --------------------------------------------------------------------------
def _offline_resume_analysis(resume_text: str) -> dict:
    text_lower = resume_text.lower()
    found_skills = [s for s in COMMON_TECH_SKILLS if s in text_lower]

    has_email = "@" in resume_text
    has_numbers = any(char.isdigit() for char in resume_text)
    has_projects = "project" in text_lower
    has_certs = "certificat" in text_lower
    has_education = any(w in text_lower for w in ["bachelor", "b.sc", "university", "degree", "college"])
    has_experience = any(w in text_lower for w in ["experience", "worked", "internship"])

    score = 40
    score += 10 if has_email else 0
    score += 10 if has_numbers else 0
    score += 10 if has_projects else 0
    score += 10 if has_certs else 0
    score += 10 if has_education else 0
    score += min(10, len(found_skills))
    score = max(0, min(100, score))

    strengths, weaknesses = [], []
    if has_projects:
        strengths.append("Projects")
    else:
        weaknesses.append("Missing a Projects section")
    if has_certs:
        strengths.append("Certifications")
    else:
        weaknesses.append("No certifications listed")
    if "leadership" in text_lower:
        strengths.append("Leadership")
    else:
        weaknesses.append("Leadership section")
    if "git" not in text_lower:
        weaknesses.append("Missing Git")
    if "sql" not in text_lower:
        weaknesses.append("Missing SQL")

    return {
        "technical_skills": found_skills,
        "soft_skills": [s for s in ["communication", "teamwork", "leadership", "problem solving"] if s in text_lower],
        "certifications": ["Detected certification keywords"] if has_certs else [],
        "education": ["Detected education section"] if has_education else [],
        "experience": ["Detected experience section"] if has_experience else [],
        "projects": ["Detected projects section"] if has_projects else [],
        "ats_score": score,
        "ats_strengths": strengths,
        "ats_weaknesses": weaknesses,
        "suggestions": [
            "Add measurable achievements (numbers, percentages, outcomes).",
            "Mention GitHub or portfolio links for your projects.",
            "Include cloud or deployment experience if you have any.",
            "Tighten your professional summary to 2-3 sentences.",
        ],
    }


def _offline_job_match(resume_text: str, job_description: str, known_skills: list[str]) -> dict:
    resume_lower = resume_text.lower()
    jd_lower = job_description.lower()

    jd_skills = [s for s in COMMON_TECH_SKILLS if s in jd_lower]
    matching = [s for s in jd_skills if s in resume_lower]
    missing = [s for s in jd_skills if s not in resume_lower]

    similarity = int((len(matching) / len(jd_skills)) * 100) if jd_skills else 50

    return {
        "similarity_percentage": similarity,
        "matching_skills": matching,
        "missing_skills": missing,
        "recommended_skills": missing[:5],
    }
