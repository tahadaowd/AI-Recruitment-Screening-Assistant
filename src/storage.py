"""
Module: src/storage.py
Handles persistent storage for candidates, evaluation results, 
HR status updates (Shortlist, Review Later, Reject), and Job configurations.
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional
from src.job_description import get_structured_job_requirements

DATA_DIR = "data"
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
JOB_CONFIG_FILE = os.path.join(DATA_DIR, "job_config.json")

VALID_STATUSES = ["New", "Shortlist", "Review Later", "Reject"]

def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def get_job_config() -> Dict[str, Any]:

    """
    Returns the active job requirements.
    Loads from job_config.json if exists, otherwise initializes from job_description.py.
    """
    _ensure_data_dir()
    if os.path.exists(JOB_CONFIG_FILE):
        try:
            with open(JOB_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to read job_config.json: {e}")

    default_config = get_structured_job_requirements()
    save_job_config(default_config)
    return default_config

def save_job_config(config_data: Dict[str, Any]) -> bool:
    """
    Saves updated job configuration (Must-Haves & Nice-to-Haves) chosen by HR.
    """
    _ensure_data_dir()
    try:
        with open(JOB_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Error] Failed to save job configuration: {e}")
        return False


def load_all_candidates() -> List[Dict[str, Any]]:
    """
    Loads all candidates from the JSON database.
    """
    _ensure_data_dir()
    if not os.path.exists(CANDIDATES_FILE):
        return []
    try:
        with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[Error] Failed to load candidates: {e}")
        return []

def save_candidate_record(candidate_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Saves or updates a candidate record avoiding duplicates based on message_id or CV file.
    """
    _ensure_data_dir()
    candidates = load_all_candidates()



    cand_id = candidate_data.get("id") or str(uuid.uuid4())[:8]
    candidate_data["id"] = cand_id



    if "hr_status" not in candidate_data or candidate_data["hr_status"] not in VALID_STATUSES:
        candidate_data["hr_status"] = "New"

    if "hr_notes" not in candidate_data:
        candidate_data["hr_notes"] = ""



    msg_id = candidate_data.get("message_id")
    cv_filename = candidate_data.get("cv_filename")

    existing_idx = None
    for idx, c in enumerate(candidates):
        if (msg_id and c.get("message_id") == msg_id) or (cv_filename and c.get("cv_filename") == cv_filename):
            existing_idx = idx
            candidate_data["id"] = c.get("id", cand_id)
            if "hr_status" in c and candidate_data.get("hr_status") == "New":
                candidate_data["hr_status"] = c["hr_status"]
            if "hr_notes" in c and not candidate_data.get("hr_notes"):
                candidate_data["hr_notes"] = c.get("hr_notes", "")
            break

    if existing_idx is not None:
        candidates[existing_idx] = candidate_data
    else:
        candidates.append(candidate_data)

    with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)

    return candidate_data

def get_candidate_by_id(candidate_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single candidate by their ID.
    """
    candidates = load_all_candidates()
    for c in candidates:
        if str(c.get("id")) == str(candidate_id):
            return c
    return None

def update_candidate_status(candidate_id: str, new_status: str, notes: Optional[str] = None) -> bool:
    """
    Updates HR decision: Shortlist, Review Later, or Reject.
    """
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {VALID_STATUSES}")

    candidates = load_all_candidates()
    found = False

    for c in candidates:
        if str(c.get("id")) == str(candidate_id):
            c["hr_status"] = new_status
            if notes is not None:
                c["hr_notes"] = notes
            found = True
            break

    if found:
        with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
            json.dump(candidates, f, indent=2, ensure_ascii=False)
        return True
    return False



def migrate_existing_results(results_path: str = "results.json") -> int:
    """
    Migrates already-screened CVs from results.json into candidates.json
    using the new Must-Have / Nice-to-Have ranking logic without needing to re-extract.
    """
    from src.ranker import evaluate_candidate_detailed

    if not os.path.exists(results_path):
        return 0

    try:
        with open(results_path, "r", encoding="utf-8") as f:
            old_results = json.load(f)
    except Exception:
        return 0

    job_cfg = get_job_config()
    must_have = job_cfg.get("must_have", {})
    nice_to_have = job_cfg.get("nice_to_have", {})

    migrated_count = 0
    for old in old_results:
        cand_info = old.get("candidate_qualifications", {})
        eval_result = evaluate_candidate_detailed(
            candidate_info=cand_info,
            must_have_reqs=must_have,
            nice_to_have_reqs=nice_to_have,
            cv_text=""
        )

        record = {
            "id": old.get("message_id")[:8] if old.get("message_id") else str(uuid.uuid4())[:8],
            "candidate_name": old.get("candidate_name", "Unknown"),
            "sender_email": old.get("sender_email", ""),
            "email_subject": old.get("email_subject", ""),
            "email_date": old.get("email_date", ""),
            "message_id": old.get("message_id", ""),
            "cv_filename": old.get("cv_filename", ""),
            "cv_path": os.path.join("data", "cvs", old.get("cv_filename", "")),
            "hr_status": "New",
            "hr_notes": "",
            "candidate_qualifications": cand_info,
            "evaluation": eval_result
        }
        save_candidate_record(record)
        migrated_count += 1

    return migrated_count

