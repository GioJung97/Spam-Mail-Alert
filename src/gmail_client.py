from __future__ import annotations
import json, pathlib, time
from typing import Optional, List, Dict, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOKEN_PATH = ROOT / "token.json"
CREDS_PATH = ROOT / "credentials.json"
STATE_PATH = ROOT / "state.json"

# For read-only while we build the pipeline.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def _load_state() -> Dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}

def _save_state(d: Dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(d, indent=2))

def get_service():
    creds: Optional[Credentials] = None
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

def _get_header(headers: List[Dict[str, str]], name: str) -> str:
    name = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name:
            return h.get("value", "")
    return ""

def bootstrap_history_id(service) -> int:
    """Pick a safe starting point so we only react to *new* mail going forward."""
    resp = service.users().messages().list(userId="me", maxResults=10).execute()
    ids = [m["id"] for m in resp.get("messages", [])]
    max_hid = 0
    for mid in ids:
        msg = service.users().messages().get(
            userId="me", id=mid, format="metadata", metadataHeaders=["Subject"]
        ).execute()
        hid = int(msg.get("historyId", 0))
        max_hid = max(max_hid, hid)
    if max_hid == 0:
        prof = service.users().getProfile(userId="me").execute()
        max_hid = int(prof.get("historyId", 1))
    st = _load_state()
    st["last_history_id"] = max_hid
    _save_state(st)
    return max_hid

def _fetch_changes_since(service, start_history_id: int) -> Dict[str, Any]:
    """Return (new_history_id, list_of_new_message_ids)."""
    new_message_ids: List[str] = []
    page_token = None
    latest_hid = start_history_id

    while True:
        req = service.users().history().list(
            userId="me",
            startHistoryId=str(start_history_id),
            historyTypes=["messageAdded"],
            pageToken=page_token,
            labelId="INBOX",  # helps focus on inbox changes
            maxResults=100,
        )
        resp = req.execute()
        for h in resp.get("history", []):
            latest_hid = max(latest_hid, int(h.get("id", start_history_id)))
            for added in h.get("messagesAdded", []):
                m = added.get("message", {})
                # Only consider new messages that are actually in INBOX
                lbls = set(m.get("labelIds", []))
                if "INBOX" in lbls:
                    new_message_ids.append(m.get("id"))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    # If there were no history entries returned, Gmail may still give a 'historyId'
    # from profile that advances; we’ll grab a fresh one to keep moving forward.
    if latest_hid == start_history_id:
        prof = service.users().getProfile(userId="me").execute()
        latest_hid = max(latest_hid, int(prof.get("historyId", start_history_id)))
    return {"latest_history_id": latest_hid, "new_message_ids": list(dict.fromkeys(new_message_ids))}

def poll_once(service) -> List[Dict[str, str]]:
    """
    Returns a list of dicts with keys: id, from, subject, snippet
    for *new* messages since last poll. Updates last_history_id.
    """
    st = _load_state()
    if "last_history_id" not in st:
        hid = bootstrap_history_id(service)
        print(f"[init] Baseline historyId: {hid}")
        st = _load_state()

    start_hid = int(st["last_history_id"])
    try:
        result = _fetch_changes_since(service, start_hid)
    except HttpError as e:
        # If startHistoryId is too old or invalid, reset baseline gracefully.
        if e.resp.status in (404, 400):
            print("[warn] startHistoryId invalid/expired; re-baselining.")
            hid = bootstrap_history_id(service)
            return []
        raise

    latest_hid = int(result["latest_history_id"])
    new_ids = result["new_message_ids"]

    if latest_hid != start_hid:
        st["last_history_id"] = latest_hid
        _save_state(st)

    new_msgs: List[Dict[str, str]] = []
    for mid in new_ids:
        msg = service.users().messages().get(
            userId="me",
            id=mid,
            format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers = msg.get("payload", {}).get("headers", [])
        new_msgs.append({
            "id": mid,
            "threadId": msg.get("threadId"),
            "from": _get_header(headers, "From"),
            "subject": _get_header(headers, "Subject"),
            "snippet": msg.get("snippet", ""),
        })
    return new_msgs

# --- Label & modify helpers ---

def _get_or_create_label(service, name: str) -> str:
    """Return the labelId for a given label name; create it if it doesn't exist."""
    labels_resp = service.users().labels().list(userId="me").execute()
    for lab in labels_resp.get("labels", []):
        if lab.get("name") == name:
            return lab["id"]
    # Create label
    body = {
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId="me", body=body).execute()
    return created["id"]

def mark_as_spam(service, message_id: str) -> None:
    """Move a message to Gmail's Spam (system) label and remove from INBOX."""
    body = {
        "addLabelIds": ["SPAM"],    # system label
        "removeLabelIds": ["INBOX"]
    }
    service.users().messages().modify(userId="me", id=message_id, body=body).execute()

def unmark_spam_to_inbox(service, message_id: str) -> None:
    """Remove SPAM label and restore to INBOX."""
    body = {
        "addLabelIds": ["INBOX"],
        "removeLabelIds": ["SPAM"]
    }
    service.users().messages().modify(userId="me", id=message_id, body=body).execute()

def add_label(service, message_id: str, label_name: str) -> None:
    lab_id = _get_or_create_label(service, label_name)
    body = {"addLabelIds": [lab_id], "removeLabelIds": []}
    service.users().messages().modify(userId="me", id=message_id, body=body).execute()
