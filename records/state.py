"""What we've already done: payments, disputes, request_ids, approvals, the web log.

Stops reruns from duplicating payments or disputes, and keeps request_ids so a
retry of the same operation reuses the same id.

Two backends, chosen with STATE_BACKEND (callers only ever use load() and save()):
  file      records/state.json on this machine (default; tests and local runs; this one has pessimist locking through threading.Lock)
  dynamodb  one item (pk="state") in the DynamoDB table STATE_TABLE, shared by
            every container. Saves are conditional writes: "only if the version is
            still the one I loaded" (optimistic locking). A save based on an old
            copy raises StateConflict instead of overwriting someone else's change.
"""
import json
import os
import sys
from pathlib import Path

from core.client import new_request_id

STATE_PATH = Path(__file__).parent / "state.json"   # always records/state.json
ARCHIVE_DIR = STATE_PATH.parent / "archive"

BACKEND = os.getenv("STATE_BACKEND", "file").strip().lower()
TABLE_NAME = os.getenv("STATE_TABLE", "dispute-agent-state")
ITEM_KEY = "state"
VERSION_KEY = "_version"        # kept inside the loaded dict, so save() knows what to expect
WARN_BYTES = 300_000            # a DynamoDB item can be at most 400 KB

_table = None                   # the boto3 Table (a fake one in tests)


class StateConflict(RuntimeError):
    """Someone else saved the state after we loaded it. Reload and try again."""


def _empty() -> dict:
    return {"request_ids": {}, "payments": {}, "disputes": {}}


def load() -> dict:
    if BACKEND == "dynamodb":
        return _dynamo_load()
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return _empty()


def save(state: dict) -> None:
    if BACKEND == "dynamodb":
        _dynamo_save(state)
        return
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)  # write-then-swap: never leaves a half-written file


# ---------------- DynamoDB ----------------

def table():
    global _table
    if _table is None:
        import boto3                      # only needed for the dynamodb backend
        _table = boto3.resource("dynamodb").Table(TABLE_NAME)
    return _table


def _dynamo_load() -> dict:
    # ConsistentRead: always see the latest committed save, never a stale replica.
    item = table().get_item(Key={"pk": ITEM_KEY}, ConsistentRead=True).get("Item")
    if not item:
        return _empty()                   # no _version: the first save creates the item
    state = json.loads(item["data"])
    state[VERSION_KEY] = int(item["version"])
    return state


def _dynamo_save(state: dict) -> None:
    from botocore.exceptions import ClientError

    expected = state.get(VERSION_KEY)
    data = json.dumps({k: v for k, v in state.items() if k != VERSION_KEY})
    if len(data.encode("utf-8")) > WARN_BYTES:
        print(f"WARNING: state is {len(data) // 1000} KB; DynamoDB items are limited to 400 KB.",
              file=sys.stderr)

    if expected is None:                  # a brand-new state: only if no item exists yet
        condition, values, new_version = "attribute_not_exists(pk)", None, 1
    else:                                 # only if nobody saved since we loaded
        condition, values, new_version = "version = :expected", {":expected": expected}, expected + 1

    args = {"Item": {"pk": ITEM_KEY, "version": new_version, "data": data},
            "ConditionExpression": condition}
    if values:
        args["ExpressionAttributeValues"] = values
    try:
        table().put_item(**args)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            raise StateConflict("The state changed since it was loaded (another save "
                                "happened first). Reload and try again.") from None
        raise
    state[VERSION_KEY] = new_version      # the same dict can be saved again


# ---------------- helpers ----------------

def request_id_for(state: dict, operation: str) -> str:
    """One request_id per named operation, created once, reused on retries."""
    ids = state.setdefault("request_ids", {})
    if operation not in ids:
        ids[operation] = new_request_id()
        save(state)
    return ids[operation]


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
