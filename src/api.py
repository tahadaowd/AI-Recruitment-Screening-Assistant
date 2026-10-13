"""
Module: src/api.py
FastAPI Backend Application for AI Recruitment Screening Assistant.
Exposes endpoints for job configuration, CV screening, candidate ranking, and HR review.
"""

import os
import shutil
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.storage import (
    get_job_config,
    save_job_config,
    load_all_candidates,
    get_candidate_by_id,
    update_candidate_status,
    migrate_existing_results,
    VALID_STATUSES
)
from src.ranker import rank_and_filter_candidates
from src.ai_extractor import extract_information
from src.screener import process_cv_file, run_gmail_screening_pipeline, CV_STORAGE_DIR
from src.cv_processor import SUPPORTED_EXTENSIONS

app = FastAPI(
    title="AI Recruitment Screening Assistant API",
    description="Backend API for automated CV screening, evaluation, and candidate ranking.",
    version="2.0.0"
)

# Enable CORS for Streamlit and Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# Pydantic Schemas for Request Validation
# -------------------------------------------------------------
class RequirementsCategory(BaseModel):
    skills: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)

class JobConfigSchema(BaseModel):
    title: str = "AI Developer"
    must_have: RequirementsCategory
    nice_to_have: RequirementsCategory

class ExtractJobRequest(BaseModel):
    job_description_text: str

class StatusUpdateRequest(BaseModel):
    status: str
    notes: Optional[str] = ""

# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    # Automatically migrate existing results from Week 1 if available
    migrate_existing_results("results.json")

@app.get("/")
def root():
    return {
        "status": "online",
        "app": "AI Recruitment Screening Assistant API",
        "docs_url": "/docs"
    }

# 1. Job Description & Requirements Endpoints
@app.get("/api/job", response_model=Dict[str, Any])
def get_current_job():
    """Retrieve the current job configuration and requirements."""
    return get_job_config()

@app.post("/api/job")
def update_job(config: JobConfigSchema):
    """Save updated Must-Have and Nice-to-Have criteria chosen by HR."""
    success = save_job_config(config.dict())
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save job configuration")
    return {"message": "Job configuration updated successfully", "job": config.dict()}

@app.post("/api/job/extract")
def extract_job_requirements(payload: ExtractJobRequest):
    """Use AI to parse a raw job description and categorize requirements."""
    text = payload.job_description_text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Job description text cannot be empty.")
    
    extracted = extract_information(text, target_type="Job Description")
    return {"extracted_requirements": extracted}

# 2. CV Screening Endpoints
@app.post("/api/screen/gmail")
def trigger_gmail_screening(max_emails: int = Query(15, ge=1, le=50)):
    """Trigger background check for application emails and screen new CVs."""
    try:
        stats = run_gmail_screening_pipeline(max_emails=max_emails)
        return {"status": "success", "summary": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/screen/upload")
async def upload_and_screen_cv(
    file: UploadFile = File(...),
    candidate_name: Optional[str] = "Uploaded Candidate"
):
    """Upload a single CV file (PDF or DOCX) and screen it directly."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Please upload {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    os.makedirs(CV_STORAGE_DIR, exist_ok=True)
    destination_path = os.path.join(CV_STORAGE_DIR, file.filename)

    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    record = process_cv_file(
        file_path=destination_path,
        candidate_name=candidate_name or "Uploaded Candidate",
        email_subject="Manual Upload",
        sender_email="manual@upload.local"
    )

    if not record:
        raise HTTPException(status_code=500, detail="Could not process or read the uploaded CV file.")

    return {"message": "CV screened successfully", "candidate": record}

# 3. Candidates, Ranking & Shortlist Endpoints
@app.get("/api/candidates")
def list_candidates(
    filter_type: str = Query("all", regex="^(all|qualified|non_qualified|shortlist)$"),
    status: Optional[str] = Query(None),
    top_n: int = Query(20, ge=1, le=100)
):
    """
    Get ranked list of candidates with filtering:
    - filter_type: 'all', 'qualified', 'non_qualified', 'shortlist'
    - status: 'New', 'Shortlist', 'Review Later', 'Reject'
    """
    candidates = load_all_candidates()
    ranked_data = rank_and_filter_candidates(candidates, top_n=top_n)

    if filter_type == "qualified":
        selected_list = ranked_data["qualified"]
    elif filter_type == "non_qualified":
        selected_list = ranked_data["non_qualified"]
    elif filter_type == "shortlist":
        selected_list = ranked_data["shortlist"]
    else:
        selected_list = ranked_data["qualified"] + ranked_data["non_qualified"]

    if status and status in VALID_STATUSES:
        selected_list = [c for c in selected_list if c.get("hr_status") == status]

    return {
        "total_screened": ranked_data["total_screened"],
        "total_qualified": ranked_data["total_qualified"],
        "total_non_qualified": ranked_data["total_non_qualified"],
        "count": len(selected_list),
        "candidates": selected_list
    }

@app.get("/api/candidates/{candidate_id}")
def get_candidate(candidate_id: str):
    """Retrieve full candidate details, match results, and AI evidence."""
    candidate = get_candidate_by_id(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@app.patch("/api/candidates/{candidate_id}/status")
def update_status(candidate_id: str, payload: StatusUpdateRequest):
    """Update HR screening decision: Shortlist, Review Later, or Reject."""
    if payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status '{payload.status}'. Allowed: {VALID_STATUSES}"
        )

    updated = update_candidate_status(
        candidate_id=candidate_id, 
        new_status=payload.status, 
        notes=payload.notes
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return {
        "message": f"Candidate status successfully updated to {payload.status}",
        "candidate_id": candidate_id,
        "new_status": payload.status
    }

# 4. System Statistics
@app.get("/api/stats")
def get_dashboard_stats():
    """Returns overview counts for the HR dashboard."""
    candidates = load_all_candidates()
    ranked_data = rank_and_filter_candidates(candidates)

    status_counts = {s: 0 for s in VALID_STATUSES}
    for c in candidates:
        st = c.get("hr_status", "New")
        if st in status_counts:
            status_counts[st] += 1

    return {
        "total_screened": len(candidates),
        "qualified": ranked_data["total_qualified"],
        "non_qualified": ranked_data["total_non_qualified"],
        "statuses": status_counts
    }
