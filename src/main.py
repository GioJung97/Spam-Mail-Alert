from __future__ import annotations
import os, json, pathlib
from typing import Optional, Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# For read-only first; we’ll upgrade to modify soon.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOKEN_PATH = ROOT / "token.json"
CREDS_PATH = ROOT / "credentials.json"
STATE_PATH = ROOT / "state.json"

def get_service():
    creds: Optional[Credentials] = None
    # print(f"DEBUG: Project root: {ROOT}")
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            if not CREDS_PATH.exists():
                raise FileNotFoundError("credentials.json not found in project root.")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def get_subject(headers: list[dict[str, str]]) -> str:
    for h in headers:
        if h.get("name") == "Subject":
            return h.get("value", "")
    return ""

def bootstrap_history_id(service) -> int:
    """Set a baseline historyId from current messages (largest seen)."""
    resp = service.users().messages().list(userId="me", maxResults=10, q="").execute()
    ids = [m["id"] for m in resp.get("messages", [])]
    max_hid = 0
    for mid in ids:
        msg = service.users().messages().get(userId="me", id=mid, format="metadata", metadataHeaders=["Subject"]).execute()
        hid = int(msg.get("historyId", 0))
        if hid > max_hid:
            max_hid = hid
    if max_hid == 0:
        # No mail yet; get profile historyId as a fallback
        prof = service.users().getProfile(userId="me").execute()
        max_hid = int(prof.get("historyId", 1))
    STATE_PATH.write_text(json.dumps({"last_history_id": max_hid}, indent=2))
    return max_hid

def main():
    service = get_service()
    print("✅ Auth succeeded")

    # List a few unread messages as a smoke test
    resp = service.users().messages().list(userId="me", q="is:unread", maxResults=5).execute()
    msgs = resp.get("messages", [])
    if not msgs:
        print("No unread messages found.")
    else:
        print(f"Found {len(msgs)} unread:")
        for m in msgs:
            msg = service.users().messages().get(userId="me", id=m["id"], format="metadata",
                                                 metadataHeaders=["From", "Subject"]).execute()
            headers = msg.get("payload", {}).get("headers", [])
            subject = get_subject(headers)
            snippet = msg.get("snippet", "")
            print(f"- {subject[:80]} | {snippet[:80]}")

    # Save a baseline historyId for next step (polling)
    if STATE_PATH.exists():
        data = json.loads(STATE_PATH.read_text())
        print(f"Existing baseline historyId: {data.get('last_history_id')}")
    else:
        hid = bootstrap_history_id(service)
        print(f"Initialized baseline historyId: {hid}")

if __name__ == "__main__":
    main()
