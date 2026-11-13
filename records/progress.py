"""Live progress of a background review: the steps the agent finished so far.

The review runs in a background thread; the browser polls for these steps.
Stored next to the state, so it works the same locally and on Fargate:
- file backend (local, one process): in memory
- dynamodb backend: one small item per review, pk="progress#<id>", so whichever
  web task behind the load balancer answers the poll sees the same steps.
Items expire after a day (DynamoDB TTL on "expires"). Display only: nothing here
decides anything, and losing it never affects money or state.
"""
import json
import threading
import time
import uuid

from records import state as st

CURRENT = "progress#current"     # which review is running now (one at a time)
STALE_S = 15 * 60                # a "running" review older than this is treated as dead
TTL_S = 24 * 3600

_mem: dict[str, dict] = {}
_lock = threading.Lock()


def _get(key: str) -> dict | None:
    if st.BACKEND == "dynamodb":
        item = st.table().get_item(Key={"pk": key}, ConsistentRead=True).get("Item")
        return json.loads(item["data"]) if item else None
    with _lock:
        v = _mem.get(key)
        return json.loads(json.dumps(v)) if v is not None else None


def _put(key: str, value: dict) -> None:
    if st.BACKEND == "dynamodb":
        st.table().put_item(Item={"pk": key, "data": json.dumps(value),
                                  "expires": int(time.time()) + TTL_S})
        return
    with _lock:
        _mem[key] = json.loads(json.dumps(value))


def running() -> str | None:
    """The id of the review that is running now, if any (ignoring dead ones)."""
    cur = _get(CURRENT)
    if not cur:
        return None
    job = _get(f"progress#{cur['id']}")
    if job and job["status"] == "running" and time.time() - job["started"] < STALE_S:
        return job["id"]
    return None


def start() -> str:
    job_id = uuid.uuid4().hex[:12]
    _put(f"progress#{job_id}", {"id": job_id, "status": "running", "started": time.time(),
                                "steps": [], "error": ""})
    _put(CURRENT, {"id": job_id})
    return job_id


def get(job_id: str) -> dict | None:
    return _get(f"progress#{job_id}")


def add(job_id: str, step: dict) -> None:
    """Append one finished step. Only the review's own thread writes, so no conflicts."""
    job = get(job_id)
    if job is None:
        return
    job["steps"].append(step)
    _put(f"progress#{job_id}", job)


def finish(job_id: str, error: str = "") -> None:
    job = get(job_id) or {"id": job_id, "started": time.time(), "steps": []}
    job.update(status="error" if error else "done", error=error)
    _put(f"progress#{job_id}", job)
