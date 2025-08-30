from __future__ import annotations
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

# Reuse your app code
from gmail_client import get_service
from gmail_client import mark_as_spam as gmail_mark_as_spam
from gmail_client import unmark_spam_to_inbox as gmail_unmark_spam
from classify.baseline import load_or_init, predict, _heuristics, combine_scores, explain
from storage import fetch_labeled_data

mcp = FastMCP("spam-notifier-mcp")

# Lazy singletons
_gmail = None
_model = None

def _lazy_init():
    global _gmail, _model
    if _gmail is None:
        _gmail = get_service()
    if _model is None:
        _model = load_or_init()

def _gmail_list_unread(limit: int = 10) -> List[Dict[str, Any]]:
    svc = _gmail
    resp = svc.users().messages().list(userId="me", q="is:unread in:inbox", maxResults=int(limit)).execute()
    rows: List[Dict[str, Any]] = []
    for m in resp.get("messages", []):
        msg = svc.users().messages().get(
            userId="me", id=m["id"],
            format="metadata", metadataHeaders=["From","Subject"]
        ).execute()
        headers = msg.get("payload", {}).get("headers", [])
        def _get(hs, name):
            for h in hs:
                if h.get("name","").lower() == name.lower():
                    return h.get("value","")
            return ""
        rows.append({
            "id": msg["id"],
            "threadId": msg.get("threadId"),
            "from": _get(headers, "From"),
            "subject": _get(headers, "Subject"),
            "snippet": msg.get("snippet",""),
        })
    return rows

def _classify_one(message: Dict[str, Any]) -> Dict[str, Any]:
    subj = (message.get("subject") or "").strip()
    text = f"{subj}\n{message.get('snippet','')}"
    ms = float(predict(_model, [text])[0])     # model score (0..1)
    heur, reasons_list = _heuristics(subj, message.get("snippet",""), message.get("from",""))
    score = combine_scores(heur, ms)
    reasons = explain(reasons_list, ms)
    return {"score": score, "reasons": reasons}

@mcp.tool()
def list_unread_emails(limit: int = 10) -> str:
    """
    List unread INBOX emails (id | from | subject).
    Args:
        limit: max number of messages to list (default 10)
    """
    _lazy_init()
    rows = _gmail_list_unread(limit)
    if not rows:
        return "(no unread)"
    return "\n".join(f"{r['id']} | {r['from']} | {r['subject']}" for r in rows)

@mcp.tool()
def classify_message(message_id: str) -> str:
    """
    Classify a single Gmail message by id.
    Returns score/reasons + basic headers.
    """
    _lazy_init()
    msg = _gmail.users().messages().get(
        userId="me", id=message_id,
        format="metadata", metadataHeaders=["From","Subject"]
    ).execute()
    headers = msg.get("payload", {}).get("headers", [])
    def _get(hs, name):
        for h in hs:
            if h.get("name","").lower() == name.lower():
                return h.get("value","")
        return ""
    m = {
        "id": message_id,
        "from": _get(headers, "From"),
        "subject": _get(headers, "Subject"),
        "snippet": msg.get("snippet",""),
    }
    res = _classify_one(m)
    return (
        f"score={res['score']:.2f}\n"
        f"reasons={res['reasons']}\n"
        f"from={m['from']}\n"
        f"subject={m['subject']}"
    )

@mcp.tool()
def mark_as_spam(message_id: str) -> str:
    """Move a message to Spam."""
    _lazy_init()
    gmail_mark_as_spam(_gmail, message_id)
    return f"ok: moved {message_id} to Spam"

@mcp.tool()
def explain_decision(message_id: str) -> str:
    """
    Return the last stored decision (if any) for this message_id
    from the local SQLite log.
    """
    _lazy_init()
    rows = fetch_labeled_data(limit=200)
    for r in rows:
        if r["message_id"] == message_id:
            return (
                f"label={r['label']} predicted={r['predicted']:.2f}\n"
                f"reasons={r['reasons']}\n"
                f"created_at={r['created_at']}"
            )
    return "(no prior decision logged)"

if __name__ == "__main__":
    # IMPORTANT: do not print to stdout here; FastMCP handles stdio transport
    mcp.run(transport="stdio")
