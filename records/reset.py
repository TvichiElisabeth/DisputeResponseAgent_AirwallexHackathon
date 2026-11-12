"""Start a fresh demo run.

Archives the current state to records/archive/state-<time>.json and starts a
new, empty state. Keeps only the model's cached evidence readings (the evidence
text hasn't changed, so there's no need to pay for the same reading twice).
Works with either state backend (file or dynamodb).
"""
import json
from datetime import datetime

from records import state as st


def reset() -> None:
    old = st.load()
    content = {k: v for k, v in old.items() if k != st.VERSION_KEY}
    if content.get("payments") or content.get("disputes"):
        st.ARCHIVE_DIR.mkdir(exist_ok=True)
        target = st.ARCHIVE_DIR / f"state-{datetime.now():%Y%m%d-%H%M%S}.json"
        target.write_text(json.dumps(content, indent=2), encoding="utf-8")
        print(f"Archived previous run -> {target.name}")

    fresh = {
        "request_ids": {},
        "payments": {},
        "disputes": {},
        "evidence_reads": old.get("evidence_reads", {}),
    }
    if st.VERSION_KEY in old:              # dynamodb: replace the version we just read
        fresh[st.VERSION_KEY] = old[st.VERSION_KEY]
    st.save(fresh)
    print("Fresh state ready. Next: pay 3 new links, then run merchant.record_payments.")


if __name__ == "__main__":
    reset()
