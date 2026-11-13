"""Agent runs: timed spans from the loop, stored per plan version, shown in the
case page's drawer; and live progress for a background review. Fake model only."""
import time

import pytest

from merchant import agent, agent_loop
from merchant.policy import ACCEPT, CHALLENGE
from records import progress
from records import state as st
from tests.fake_dynamodb import FakeTable
from tests.test_agent_loop import GOOD_SCRIPT, ROWS, FakeModel, plan_turn, wired  # noqa: F401
from web import service, view


def run_with(script, on_span=None):
    return agent_loop.run_agent(None, {}, [dict(r) for r in ROWS], llm=FakeModel(script), on_span=on_span)


# ---------------- spans from the loop ----------------

def test_run_records_a_timed_span_tree():
    seen = []
    run = run_with(GOOD_SCRIPT + [plan_turn(ACCEPT)], on_span=seen.append)
    root, rest = run.spans[0], run.spans[1:]
    assert (root["kind"], root["depth"], root["start_s"]) == ("invoke_agent", 0, 0.0)
    assert {s["kind"] for s in rest} == {"chat", "execute_tool"} and all(s["depth"] == 1 for s in rest)
    assert [s["id"] for s in run.spans] == [f"s{i}" for i in range(1, len(run.spans) + 1)]
    assert all(s["dur_s"] >= 0 and s["start_s"] >= 0 for s in run.spans)
    assert run.started_at and run.duration_s >= 0 and run.model
    tools_ = [s for s in rest if s["kind"] == "execute_tool"]
    assert tools_[0]["name"] == "list_open_disputes" and tools_[-1]["name"] == "submit_plan"
    assert tools_[1]["case"] == "A" and tools_[1]["input"] == {"case": "A"} and tools_[1]["output"]
    assert seen[-1] is root and len(seen) == len(run.spans)          # every span, root last
    assert root["output"]["finished"] and root["output"]["stop"] == "plan submitted"


def test_long_outputs_are_cut():
    assert agent_loop._clip({"x": "y" * 5000}).endswith("…[cut]")
    assert agent_loop._clip({"x": 1}) == {"x": 1}


def test_a_broken_progress_callback_never_breaks_the_review():
    def boom(span):
        raise RuntimeError("display down")
    assert run_with(GOOD_SCRIPT + [plan_turn(ACCEPT)], on_span=boom).finished


def test_run_info_carries_everything_the_drawer_needs(wired):  # noqa: F811
    items, info = agent.plan_with_run(None, wired, llm=FakeModel(GOOD_SCRIPT + [plan_turn(CHALLENGE)]))
    assert info["id"].startswith("run_") and info["trigger"] == "Dispute opened"
    assert info["outcomes"] == {"A": CHALLENGE, "B": ACCEPT, "C": "ESCALATE"}
    b = next(it for it in info["plan_items"] if it["case"] == "B")
    assert (b["action"], b["policy_action"], b["agrees"]) == (CHALLENGE, ACCEPT, False)
    assert info["spans"][0]["kind"] == "invoke_agent"


def test_trigger_names_the_bank_rejection(wired):  # noqa: F811
    wired["rejections"] = {"A": {"at": "now"}}
    _, info = agent.plan_with_run(None, wired, "Rejected.", llm=FakeModel(GOOD_SCRIPT + [plan_turn(ACCEPT)]))
    assert info["trigger"] == "Bank rejected evidence"


# ---------------- what the drawer shows for one case ----------------

def drawer_run(wired_state, b_action=CHALLENGE):
    _, info = agent.plan_with_run(None, wired_state, llm=FakeModel(GOOD_SCRIPT + [plan_turn(b_action)]))
    return {**info, "at": "2026-11-12T09:14:00+00:00"}


def test_case_sees_its_own_spans_plus_the_shared_ones(wired):  # noqa: F811
    run = drawer_run(wired)
    a = view.agent_run(run, "A")
    cases = {s["case"] for s in a["spans"]}
    assert cases == {None, "A"}
    names = [s["name"] for s in a["spans"]]
    assert "list_open_disputes" in names and "submit_plan" in names and "dispute_agent" in names
    assert a["steps"] == len(a["spans"]) and a["outcome"] == "Challenge"
    assert all(0 <= s["bar_left"] <= 100 and 0 < s["bar_width"] <= 100 for s in a["spans"])
    assert a["spans"][0]["input"].startswith("{")                       # pretty JSON


def test_disagreement_has_two_sides_and_the_resolution(wired):  # noqa: F811
    run = drawer_run(wired)
    assert view.agent_run(run, "A")["disagreements"] == []
    (d,) = view.agent_run(run, "B")["disagreements"]
    assert d["a"] == "Agent proposed" and d["av"].startswith("Challenge. Small amount")
    assert d["b"] == "Policy (code)" and d["bv"].startswith("Accept")
    assert "person must approve" in d["res"]


def test_runs_are_kept_per_plan_version():
    w = {"plans": {"A": [{"dispute_id": "d", "run_id": "run_1"}, {"dispute_id": "d", "run_id": "run_2"}]}}
    for i in range(1, 8):
        service.record_run(w, {"id": f"run_{i}", "outcomes": {"A": "ACCEPT"}, "spans": [], "trace": [1]},
                           f"2026-11-12T09:1{i}:00+00:00")
    ids = [r["id"] for r in w["runs"]]
    assert "run_1" in ids and "run_2" in ids                     # linked to v1 / v2
    assert ids[-service.RUNS_KEPT:] == [f"run_{i}" for i in range(4, 8)]
    assert all("trace" not in r for r in w["runs"])
    tabs = view.run_tabs(w["runs"], w["plans"]["A"], "A")
    assert tabs[0]["label"].startswith("Run v1") and tabs[1]["label"].startswith("Run v2")


# ---------------- the drawer route ----------------

@pytest.fixture
def app_client(tmp_path, monkeypatch, wired):  # noqa: F811
    from fastapi.testclient import TestClient

    from web.main import app
    monkeypatch.setattr(st, "BACKEND", "file")
    monkeypatch.setattr(st, "STATE_PATH", tmp_path / "state.json")
    run = drawer_run(wired)
    st.save({"request_ids": {}, "payments": {}, "disputes": {},
             "web": {"runs": [run], "plans": {"A": [{"dispute_id": "dst_a", "run_id": run["id"]}]}}})
    return TestClient(app), run


def test_drawer_route_renders_the_run(app_client):
    client, run = app_client
    html = client.get(f"/cases/A/runs/{run['id']}").text
    assert 'class="rundrawer"' in html and "Run v1" in html and "Plan summary" in html
    assert "C first: 2 days left." in html and "submit_plan" in html
    assert html.count('aria-pressed="true"') == 1                   # first span selected
    assert html.count("data-span-detail=") == html.count('data-span="')


def test_drawer_route_refuses_unknown_runs(app_client):
    client, _ = app_client
    assert client.get("/cases/A/runs/run_nope").status_code == 404


# ---------------- live progress for a background review ----------------

@pytest.mark.parametrize("backend", ["file", "dynamodb"])
def test_progress_store(monkeypatch, backend):
    monkeypatch.setattr(st, "BACKEND", backend)
    monkeypatch.setattr(st, "_table", FakeTable())
    progress._mem.clear()
    job = progress.start()
    assert progress.running() == job
    progress.add(job, {"label": "Case A · Read the evidence"})
    progress.finish(job)
    got = progress.get(job)
    assert got["status"] == "done" and got["steps"][0]["label"] == "Case A · Read the evidence"
    assert progress.running() is None


def test_review_runs_in_the_background_and_reports_real_steps(monkeypatch):
    from fastapi.testclient import TestClient

    from web.main import app
    monkeypatch.setattr(st, "BACKEND", "file")
    progress._mem.clear()

    def fake_review(on_step=None):
        on_step(service.progress_step({"kind": "execute_tool", "name": "get_evidence", "case": "A",
                                       "summary": "Read the evidence (10 characters)", "dur_s": .1}))
    monkeypatch.setattr(service, "review", fake_review)
    client = TestClient(app)
    r = client.post("/review")
    assert r.status_code == 202
    job = r.json()["id"]
    for _ in range(50):
        p = client.get(f"/review/{job}/progress").json()
        if p["status"] != "running":
            break
        time.sleep(.02)
    assert p["status"] == "done"
    assert p["steps"] == [{"label": "Case A · Read the evidence (10 characters)", "kind": "execute_tool",
                           "error": False, "dur_s": .1}]
