"""The state backends: file (default) and DynamoDB with optimistic locking."""
import json

import pytest

from records import reset as reset_mod
from records import state as st
from tests.fake_dynamodb import FakeTable


@pytest.fixture
def dynamo(monkeypatch):
    table = FakeTable()
    monkeypatch.setattr(st, "BACKEND", "dynamodb")
    monkeypatch.setattr(st, "_table", table)
    return table


def test_file_backend_is_the_default_and_unchanged(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "STATE_PATH", tmp_path / "state.json")
    assert st.BACKEND == "file"
    st.save({"payments": {"A": {"id": "pi_1"}}})
    loaded = st.load()
    assert loaded == {"payments": {"A": {"id": "pi_1"}}}
    assert st.VERSION_KEY not in loaded


def test_empty_table_gives_an_empty_state(dynamo):
    assert st.load() == {"request_ids": {}, "payments": {}, "disputes": {}}


def test_round_trip_and_version_goes_up(dynamo):
    state = st.load()
    state["payments"]["A"] = {"id": "pi_1", "amount": 1000.5}
    st.save(state)
    assert state[st.VERSION_KEY] == 1
    st.save(state)                                   # same dict, saved again
    assert state[st.VERSION_KEY] == 2

    loaded = st.load()
    assert loaded[st.VERSION_KEY] == 2
    assert loaded["payments"]["A"] == {"id": "pi_1", "amount": 1000.5}
    stored = dynamo.items["state"]
    assert stored["version"] == 2
    assert st.VERSION_KEY not in json.loads(stored["data"])   # the version lives beside the data


def test_a_save_from_an_old_copy_is_refused(dynamo):
    st.save(st.load())                               # version 1
    first, second = st.load(), st.load()             # two containers read version 1
    first["disputes"]["B"] = {"status": "REFUNDED"}
    st.save(first)                                   # version 2
    second["human_queue"] = {"C": {}}
    with pytest.raises(st.StateConflict):
        st.save(second)                              # would erase B's refund record
    assert st.load()["disputes"]["B"] == {"status": "REFUNDED"}   # nothing was lost


def test_a_new_state_never_overwrites_an_existing_one(dynamo):
    st.save({"payments": {"A": {}}})                 # creates the item
    with pytest.raises(st.StateConflict):
        st.save({"payments": {}})                    # a blind write without a version
    assert st.load()["payments"] == {"A": {}}


def test_request_id_survives_a_reload(dynamo, monkeypatch):
    state = st.load()
    rid = st.request_id_for(state, "refund_B")
    assert st.request_id_for(st.load(), "refund_B") == rid


def test_large_state_warns(dynamo, monkeypatch, capsys):
    monkeypatch.setattr(st, "WARN_BYTES", 100)
    st.save({"activity": ["x" * 200]})
    assert "400 KB" in capsys.readouterr().err


def test_reset_works_with_dynamodb(dynamo, monkeypatch, tmp_path):
    monkeypatch.setattr(st, "ARCHIVE_DIR", tmp_path / "archive")
    state = st.load()
    state["payments"]["A"] = {"id": "pi_1"}
    state["evidence_reads"] = {"A": "cached"}
    st.save(state)
    reset_mod.reset()
    fresh = st.load()
    assert fresh["payments"] == {} and fresh["evidence_reads"] == {"A": "cached"}
    assert len(list((tmp_path / "archive").glob("state-*.json"))) == 1


def test_migration_copies_once_and_then_refuses(dynamo, monkeypatch, tmp_path):
    from records import migrate_to_dynamodb as mig
    monkeypatch.setattr(st, "STATE_PATH", tmp_path / "state.json")
    st.STATE_PATH.write_text(json.dumps({"payments": {"A": {"id": "pi_1"}}}), encoding="utf-8")
    mig.migrate()
    assert st.load()["payments"] == {"A": {"id": "pi_1"}}
    with pytest.raises(SystemExit, match="Refused"):
        mig.migrate()


def test_replace_overwrites_the_cloud_and_archives_the_old_one(dynamo, monkeypatch, tmp_path):
    from records import migrate_to_dynamodb as mig
    monkeypatch.setattr(st, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(st, "ARCHIVE_DIR", tmp_path / "archive")
    st.save({"payments": {"OLD": {}}})                       # cloud state, version 1
    st.STATE_PATH.write_text(json.dumps({"payments": {"NEW": {}}}), encoding="utf-8")

    mig.replace()
    loaded = st.load()
    assert loaded["payments"] == {"NEW": {}} and loaded[st.VERSION_KEY] == 2
    archived = list((tmp_path / "archive").glob("state-cloud-*.json"))
    assert len(archived) == 1 and json.loads(archived[0].read_text())["payments"] == {"OLD": {}}


def test_replace_on_an_empty_table_just_creates(dynamo, monkeypatch, tmp_path):
    from records import migrate_to_dynamodb as mig
    monkeypatch.setattr(st, "STATE_PATH", tmp_path / "state.json")
    st.STATE_PATH.write_text(json.dumps({"payments": {"NEW": {}}}), encoding="utf-8")
    mig.replace()
    assert st.load()[st.VERSION_KEY] == 1
