"""
Module: src/screener.py
Integrates the complete screening pipeline into reusable functions:
\- Processing a single CV file (from local upload or email)
\- Batch processing CVs from Gmail
"""

import os
import uuid
from typing import Dict, Any, Optional

from src.cv_processor import (
    extract_text,
    package_candidate_profile,
    save_attachment,
    SUPPORTED_EXTENSIONS
)
from src.ai_extractor import extract_information
from src.ranker import evaluate_candidate_detailed
from src.storage import (
    get_job_config,
    save_candidate_record
)
from src.gmail import get_gmail_service
from src.email_processor import (
    process_email,
    is_email_processed,
    mark_email_as_processed
)

CV_STORAGE_DIR = os.getenv("CV_STORAGE_DIR", "data/cvs")
PROCESSED_FILE = os.getenv("PROCESSED_EMAILS_FILE", "data/processed_emails.json")
GMAIL_SEARCH_QUERY = os.getenv("GMAIL_SEARCH_QUERY", "has:attachment (filename:pdf OR filename:docx)")


def process_cv_file(
    file_path: str,
    candidate_name: str = "Candidate",
    sender_email: str = "",
    email_subject: str = "Direct Application",
    email_date: str = "",
    message_id: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Extracts text from a CV file, analyzes it with AI, evaluates it against
    active job requirements (Must-Have & Nice-to-Have), and saves the candidate record.
    """
    if not os.path.exists(file_path):
        print(f"[Error] File not found: {file_path}")
        return None



    cv_text = extract_text(file_path)
    if not cv_text or len(cv_text.strip()) < 20:
        print(f"[Warning] CV text is unreadable or empty: {file_path}")
        return None



    candidate_qualifications = extract_information(cv_text, target_type="CV")



    job_cfg = get_job_config()
    must_have = job_cfg.get("must_have", {})
    nice_to_have = job_cfg.get("nice_to_have", {})



    evaluation = evaluate_candidate_detailed(
        candidate_info=candidate_qualifications,
        must_have_reqs=must_have,
        nice_to_have_reqs=nice_to_have,
        cv_text=cv_text
    )



    cand_id = message_id[:8] if message_id else str(uuid.uuid4())[:8]
    record = {
        "id": cand_id,
        "candidate_name": candidate_name,
        "sender_email": sender_email,
        "email_subject": email_subject,
        "email_date": email_date,
        "message_id": message_id,
        "cv_filename": os.path.basename(file_path),
        "cv_path": file_path,
        "hr_status": "New",
        "hr_notes": "",
        "candidate_qualifications": candidate_qualifications,
        "evaluation": evaluation
    }



    saved_record = save_candidate_record(record)
    return saved_record


def run_gmail_screening_pipeline(max_emails: int = 15) -> Dict[str, Any]:
    """
    Connects to Gmail, scans incoming application emails with CV attachments,
    processes unread applications, and saves results.
    """
    service = get_gmail_service()
    if not service:
        raise RuntimeError("Failed to authenticate with Gmail API.")

    result = service.users().messages().list(
        userId="me",
        q=GMAIL_SEARCH_QUERY,
        maxResults=max_emails
    ).execute()

    messages = result.get("messages", [])
    if not messages:
        return {"total_found": 0, "processed": 0, "skipped": 0, "new_cvs": 0}

    processed_count = 0
    skipped_count = 0
    new_cvs_count = 0

    for item in messages:
        msg_id = item["id"]

        if is_email_processed(msg_id, PROCESSED_FILE):
            skipped_count += 1
            continue

        try:
            full_msg = service.users().messages().get(
                userId="me",
                id=msg_id,
                format="full"
            ).execute()
        except Exception as e:
            print(f"[Warning] Could not fetch email {msg_id}: {e}")
            continue

        email_data = process_email(full_msg)
        attachments = email_data.get("attachments", [])

        if not attachments:
            mark_email_as_processed(msg_id, PROCESSED_FILE)
            continue

        for att in attachments:
            filename = att.get("filename", "")
            ext = os.path.splitext(filename)[1].lower()

            if ext not in SUPPORTED_EXTENSIONS:
                continue

            saved_path = save_attachment(service, msg_id, att, CV_STORAGE_DIR)
            if not saved_path:
                continue

            profile = package_candidate_profile(email_data, saved_path, "")

            cand_record = process_cv_file(
                file_path=saved_path,
                candidate_name=profile["candidate_name"],
                sender_email=profile["sender_email"],
                email_subject=profile["email_subject"],
                email_date=profile["email_date"],
                message_id=msg_id
            )

            if cand_record:
                new_cvs_count += 1

        mark_email_as_processed(msg_id, PROCESSED_FILE)
        processed_count += 1

    return {
        "total_found": len(messages),
        "processed": processed_count,
        "skipped": skipped_count,
        "new_cvs": new_cvs_count
    }
    
    