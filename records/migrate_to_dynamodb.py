"""Copy records/state.json into the DynamoDB table.

Run from the project root:
  python -m records.migrate_to_dynamodb            first copy; refuses if the table has a state
  python -m records.migrate_to_dynamodb --replace  overwrite the cloud state with state.json;
                                                   the old cloud state is archived first

--replace is for switching back to the cloud after developing on the local file:
the table then holds exactly what state.json holds.
"""
import json
import sys
from datetime import datetime

from records import state as st


def _read_file() -> dict:
    if not st.STATE_PATH.exists():
        raise SystemExit(f"Nothing to copy: {st.STATE_PATH} does not exist.")
    data = json.loads(st.STATE_PATH.read_text(encoding="utf-8"))
    data.pop(st.VERSION_KEY, None)
    return data


def migrate() -> None:
    data = _read_file()                     # no version: only creates, never overwrites
    try:
        st._dynamo_save(data)
    except st.StateConflict:
        raise SystemExit(f"Refused: table {st.TABLE_NAME} already has a state item. "
                         "Use --replace to overwrite it with state.json.")
    print(f"Copied {len(json.dumps(data)) // 1000} KB of state into {st.TABLE_NAME} (version 1).")


def replace() -> None:
    data = _read_file()
    cloud = st._dynamo_load()
    version = cloud.pop(st.VERSION_KEY, None)
    if version is not None:                 # keep the old cloud state, just in case
        st.ARCHIVE_DIR.mkdir(exist_ok=True)
        target = st.ARCHIVE_DIR / f"state-cloud-{datetime.now():%Y%m%d-%H%M%S}.json"
        target.write_text(json.dumps(cloud, indent=2), encoding="utf-8")
        print(f"Archived the cloud state (version {version}) -> {target.name}")
        data[st.VERSION_KEY] = version      # conditional: refused if anyone saved meanwhile
    try:
        st._dynamo_save(data)
    except st.StateConflict:
        raise SystemExit("Refused: the cloud state changed while copying (is the app running?). "
                         "Stop it and try again.")
    print(f"Replaced the cloud state with state.json (now version {data[st.VERSION_KEY]}).")


if __name__ == "__main__":
    replace() if "--replace" in sys.argv[1:] else migrate()
