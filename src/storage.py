from __future__ import annotations
import sqlite3, pathlib, time
from typing import Optional, Dict, Any

DB_PATH = pathlib.Path(__file__).resolve().parents[1] / "state.db"

DDL = """
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_id TEXT NOT NULL,
  predicted REAL NOT NULL,         -- model spam probability
  label TEXT NOT NULL,             -- "spam"|"ham"|"suspicious"|"none"
  reasons TEXT NOT NULL,           -- short JSON/text blob
  created_at INTEGER NOT NULL
);
"""

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute(DDL)
    return c

def log_decision(message_id: str, predicted: float, label: str, reasons: str) -> None:
    ts = int(time.time())
    with _conn() as c:
        c.execute(
            "INSERT INTO decisions (message_id, predicted, label, reasons, created_at) VALUES (?,?,?,?,?)",
            (message_id, predicted, label, reasons, ts),
        )

def fetch_labeled_data(limit: Optional[int] = None) -> list[dict[str, Any]]:
    q = "SELECT message_id, predicted, label, reasons, created_at FROM decisions ORDER BY id DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    with _conn() as c:
        cur = c.execute(q)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
