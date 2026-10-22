"""Local memory of what we've already done, in records/state.json.

Stops reruns from duplicating payments or disputes, and keeps request_ids
so a retry of the same operation reuses the same id.
"""
import json
from pathlib import Path

from core.client import new_request_id

STATE_PATH = Path(__file__).parent / "state.json"   # always records/state.json


def load() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"request_ids": {}, "payments": {}, "disputes": {}}


def save(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)  # write-then-swap: never leaves a half-written file


def request_id_for(state: dict, operation: str) -> str:
    """One request_id per named operation, created once, reused on retries."""
    ids = state.setdefault("request_ids", {})
    if operation not in ids:
        ids[operation] = new_request_id()
        save(state)
    return ids[operation]

ARCHIVE_DIR = STATE_PATH.parent / "archive"


def used_payment_ids() -> set[str]:
    """Every payment intent used in earlier runs (from archived state files)."""
    ids: set[str] = set()
    if not ARCHIVE_DIR.exists():
        return ids
    for f in ARCHIVE_DIR.glob("state-*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        ids |= {p["id"] for p in data.get("payments", {}).values()}
        ids |= {d["payment_intent_id"] for d in data.get("disputes", {}).values()
                if "payment_intent_id" in d}
        ids |= {p["id"] for p in data.get("abandoned_payments", [])}
    return ids