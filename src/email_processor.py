import os
import json
import base64

def get_message_body(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

            if "parts" in part:
                body = get_message_body(part)
                if body:
                    return body

    data = payload.get("body", {}).get("data")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return ""

def get_header(headers, name):
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""

def get_attachments(payload):
    attachments = []

    def extract_parts(parts):
        for part in parts:
            filename = part.get("filename", "")
            body = part.get("body", {})

            if filename:
                attachments.append({
                    "filename": filename,
                    "attachment_id": body.get("attachmentId"),
                    "data": body.get("data"),
                    "mime_type": part.get("mimeType", ""),
                    "size": body.get("size", 0)
                })

            if "parts" in part:
                extract_parts(part["parts"])

    extract_parts(payload.get("parts", []))
    return attachments

def process_email(message):
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    return {
        "id": message.get("id", ""),
        "thread_id": message.get("threadId", ""),
        "sender": get_header(headers, "From"),
        "subject": get_header(headers, "Subject"),
        "date": get_header(headers, "Date"),
        "body": get_message_body(payload),
        "attachments": get_attachments(payload)
    }

def load_processed_ids(storage_file="data/processed_emails.json"):
    if os.path.exists(storage_file):
        try:
            with open(storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except Exception as e:
            print(f"[Warning] Could not read processed IDs file: {e}")
            return set()
    return set()

def mark_email_as_processed(message_id, storage_file="data/processed_emails.json"):
    os.makedirs(os.path.dirname(storage_file), exist_ok=True)
    processed = load_processed_ids(storage_file)
    processed.add(message_id)
    with open(storage_file, "w", encoding="utf-8") as f:
        json.dump(list(processed), f, indent=2)

def is_email_processed(message_id, storage_file="data/processed_emails.json"):
    processed = load_processed_ids(storage_file)
    return message_id in processed