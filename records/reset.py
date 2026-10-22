"""Start a fresh demo run.

Archives records/state.json to records/archive/state-<time>.json and starts a
new, empty state. Keeps only the model's cached evidence readings (the evidence
text hasn't changed, so there's no need to pay for the same reading twice).
"""
from datetime import datetime

from records import state as st


def reset() -> None:
    old = st.load()
    if st.STATE_PATH.exists():
        st.ARCHIVE_DIR.mkdir(exist_ok=True)
        target = st.ARCHIVE_DIR / f"state-{datetime.now():%Y%m%d-%H%M%S}.json"
        target.write_text(st.STATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Archived previous run -> {target.name}")

    st.save({
        "request_ids": {},
        "payments": {},
        "disputes": {},
        "evidence_reads": old.get("evidence_reads", {}),
    })
    print("Fresh state ready. Next: pay 3 new links, then run merchant.record_payments.")


if __name__ == "__main__":
    reset()