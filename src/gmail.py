import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

def get_gmail_service():
    creds = None

    try:
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"[Warning] Failed to refresh token: {e}. Re-authenticating...")
                    creds = None

            if not creds:
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Missing '{CREDENTIALS_FILE}'. Please download your OAuth 2.0 "
                        f"credentials from Google Cloud Console and place it in the project root."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(TOKEN_FILE, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())

        service = build("gmail", "v1", credentials=creds)
        return service

    except FileNotFoundError as fnf_error:
        print(f"[Auth Error] {fnf_error}")
        raise
    except HttpError as http_error:
        print(f"[Gmail API Error] HTTP Error occurred during connection: {http_error}")
        raise
    except Exception as e:
        print(f"[Auth Error] Unexpected error while connecting to Gmail: {e}")
        raise