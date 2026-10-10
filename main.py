import os
import json
from dotenv import load_dotenv
from src.gmail import get_gmail_service
from src.email_processor import (
    process_email,
    is_email_processed,
    mark_email_as_processed
)
from src.cv_processor import (
    save_attachment,
    extract_text,
    package_candidate_profile,
    SUPPORTED_EXTENSIONS
)
from src.job_description import get_job_description
from src.ai_extractor import extract_information
from src.matcher import match_candidate

load_dotenv()

GMAIL_SEARCH_QUERY = os.getenv(
    "GMAIL_SEARCH_QUERY",
    "has:attachment (filename:pdf OR filename:docx)"
)
CV_STORAGE_DIR = os.getenv("CV_STORAGE_DIR", "data/cvs")
PROCESSED_FILE = os.getenv("PROCESSED_EMAILS_FILE", "data/processed_emails.json")
RESULTS_FILE = os.getenv("RESULTS_FILE", "results.json")

def load_results(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_results(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    print("=" * 70)
    print("   AI Recruitment Screening Assistant - Week 1 Workflow")
    print("=" * 70)

    print("\n[1/5] Connecting to Gmail API...")
    try:
        service = get_gmail_service()
        print("  Connected to Gmail successfully.")
    except Exception as e:
        print(f"  Failed to connect to Gmail: {e}")
        return

    print("\n[2/5] Loading and analyzing Job Description...")
    job_description_raw = get_job_description()
    print("  Extracting requirements with AI...")
    job_info = extract_information(job_description_raw, target_type="Job Description")
    
    print("\n--- Extracted Job Requirements ---")
    for category, items in job_info.items():
        print(f"  • {category.title()}: {', '.join(items) if items else 'None specified'}")

    print(f"\n[3/5] Searching Gmail with query: '{GMAIL_SEARCH_QUERY}'...")
    try:
        result = service.users().messages().list(
            userId="me",
            q=GMAIL_SEARCH_QUERY
        ).execute()
    except Exception as e:
        print(f"  Failed to fetch messages: {e}")
        return

    messages = result.get("messages", [])
    print(f"  Found {len(messages)} matching email(s).")

    if not messages:
        print("  No application emails found with attachments.")
        return

    all_results = load_results(RESULTS_FILE)

    print("\n[4/5] Processing application emails and evaluating CVs...")
    candidates_count = 0
    skipped_count = 0

    for idx, item in enumerate(messages, start=1):
        msg_id = item["id"]
        print(f"\n" + "-" * 70)
        print(f"Processing Email [{idx}/{len(messages)}] (ID: {msg_id})")

        if is_email_processed(msg_id, PROCESSED_FILE):
            print(f"   Skipping: Email ID {msg_id} was already processed previously.")
            skipped_count += 1
            continue

        try:
            full_message = service.users().messages().get(
                userId="me",
                id=msg_id,
                format="full"
            ).execute()
        except Exception as e:
            print(f"   Error retrieving message details: {e}")
            continue

        email_data = process_email(full_message)
        print(f"  Sender : {email_data['sender']}")
        print(f"  Subject: {email_data['subject']}")
        print(f"  Date   : {email_data['date']}")

        attachments = email_data.get("attachments", [])
        if not attachments:
            print("  No attachments found in this email. Skipping.")
            mark_email_as_processed(msg_id, PROCESSED_FILE)
            continue

        has_valid_cv = False

        for attachment in attachments:
            filename = attachment.get("filename", "")
            ext = os.path.splitext(filename)[1].lower()

            if ext not in SUPPORTED_EXTENSIONS:
                print(f"  Ignoring unsupported file: {filename}")
                continue

            print(f"\n  [CV Found] Downloading '{filename}'...")
            saved_path = save_attachment(service, msg_id, attachment, CV_STORAGE_DIR)
            if not saved_path:
                print(f"   Failed to save attachment: {filename}")
                continue

            print(f"  Extracting text from: {saved_path}")
            cv_text = extract_text(saved_path)

            if not cv_text or len(cv_text.strip()) < 20:
                print(f"   Warning: CV text is empty or unreadable.")
                continue

            has_valid_cv = True
            candidates_count += 1

            candidate_profile = package_candidate_profile(email_data, saved_path, cv_text)

            print(f"  Analyzing candidate qualifications with AI...")
            candidate_info = extract_information(cv_text, target_type="CV")

            print(f"  Running initial CV-to-Job matching...")
            match_results = match_candidate(job_info, candidate_info, cv_text)

            print("\n" + "=" * 50)
            print(f" SCREENING REPORT: {candidate_profile['candidate_name']}")
            print("=" * 50)
            print(f" Email File: {candidate_profile['cv_filename']}")

            meets_count = sum(1 for m in match_results if m['result'] == 'Meets')
            partial_count = sum(1 for m in match_results if m['result'] == 'Partially Meets')
            not_meets_count = sum(1 for m in match_results if m['result'] == 'Does Not Meet')

            print(f" Summary: {meets_count} Meets | {partial_count} Partially Meets | {not_meets_count} Does Not Meet\n")
            print(f" {'Category':<15} | {'Requirement':<25} | {'Result':<16} | {'Sim':<5} | Evidence")
            print(" " + "-" * 85)

            for m in match_results:
                req_disp = (m['requirement'][:22] + "...") if len(m['requirement']) > 25 else m['requirement']
                print(f" {m['category'].title():<15} | {req_disp:<25} | {m['result']:<16} | {m['similarity_score']:<5} | {m['evidence']}")

            print("=" * 50)

            candidate_entry = {
                "candidate_name": candidate_profile["candidate_name"],
                "sender_email": candidate_profile["sender_email"],
                "email_subject": candidate_profile["email_subject"],
                "email_date": candidate_profile["email_date"],
                "message_id": candidate_profile["message_id"],
                "cv_filename": candidate_profile["cv_filename"],
                "summary": {
                    "meets": meets_count,
                    "partially_meets": partial_count,
                    "does_not_meet": not_meets_count
                },
                "candidate_qualifications": candidate_info,
                "match_results": match_results
            }
            all_results.append(candidate_entry)
            save_results(all_results, RESULTS_FILE)

        mark_email_as_processed(msg_id, PROCESSED_FILE)

    print("\n[5/5] Screening Completed.")
    print(f"  Total emails evaluated : {len(messages)}")
    print(f"  Previously processed   : {skipped_count}")
    print(f"  New CVs screened       : {candidates_count}")
    print(f"  Results saved to       : {RESULTS_FILE}")
    print("=" * 70)

if __name__ == "__main__":
    main()