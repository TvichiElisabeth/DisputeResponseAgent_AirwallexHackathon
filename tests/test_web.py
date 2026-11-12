"""The web layer's safety checks. Airwallex and the agent's actions are stubbed:
these tests prove what the server refuses, not what Airwallex does."""
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("AWX_CLIENT_ID", "test")
os.environ.setdefault("AWX_API_KEY", "test")

import pytest  # noqa: E402

from merchant.approvals import verify_approval  # noqa: E402
from merchant.policy import Dispute, EvidenceFlags, decide  # noqa: E402
from records import state as st  # noqa: E402
from web import service  # noqa: E402

DUE = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(timespec="seconds")
FLAGS = EvidenceFlags(prior_undisputed_matches=3, signed_delivery=True, delivery_scanned=True)
ROW = {"case": "A", "id": "dst_a", "amount": 1240.0, "currency": "USD", "reason_code": "10.4",
       "reason_type": "FRAUDULENT", "stage": "CHARGEBACK", "status": "REQUIRES_RESPONSE",
       "due_at": DUE, "payment_intent_id": "int_a"}
# A after the rejection: ACCEPT, needs approval.
DECISION = decide(Dispute("A", 1240.0, "USD", "FRAUDULENT", "CHARGEBACK", "REQUIRES_RESPONSE",
                          DUE, rejected_before=True), FLAGS)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(st, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(service, "client", lambda: object())
    live = {"rows": [dict(ROW)]}
    monkeypatch.setattr(service, "read_queue", lambda c, s: [dict(r) for r in live["rows"]])
    calls = []
    monkeypatch.setattr(service.agent, "act", lambda c, s, it, ask: calls.append(ask("?")))
    monkeypatch.setattr(service.agent, "resolve_escalation",
                        lambda *a, **k: calls.append("resolved"))
    it = {"row": dict(ROW), "decision": DECISION, "flags": FLAGS,
          "note": {"explanation": "x", "what_to_check": []}}
    st.save({"web": {"review": {"at": "now", "items": [service._serialize(it)]}}})
    return {"live": live, "calls": calls, "item": it}


def _shown_fingerprint(it):
    return service.approval_for(st.load(), it)[1]


def test_stored_plan_survives_the_round_trip(env):
    back = service._deserialize(service._serialize(env["item"]))
    assert back["decision"] == DECISION and back["flags"] == FLAGS


def test_screen_fingerprint_is_the_one_verify_approval_checks(env):
    it = env["item"]
    terms_fp = _shown_fingerprint(it)
    state = {}
    from merchant.approvals import request_approval
    request_approval(state, it["row"], DECISION, "OTHERS", None, ask=lambda _: "y", save=lambda s: None)
    assert state["approvals"][next(iter(state["approvals"]))]["terms_sha256"] == terms_fp
    verify_approval(state, it["row"], DECISION, "OTHERS", None)


def test_matching_fingerprint_acts(env):
    service.decide_approval("A", _shown_fingerprint(env["item"]), approve=True)
    assert env["calls"] == ["y"]


def test_changed_live_amount_refuses_the_old_screen(env):
    fp = _shown_fingerprint(env["item"])
    env["live"]["rows"][0]["amount"] = 2000.0             # changed after the person looked
    service.decide_approval("A", fp, approve=True)
    assert env["calls"] == []
    outcome = next(iter(st.load()["web"]["outcomes"].values()))
    assert outcome["kind"] == "error" and "changed" in outcome["text"]


def test_moved_stage_refuses(env):
    fp = _shown_fingerprint(env["item"])
    env["live"]["rows"][0]["stage"] = "PRE_ARBITRATION"
    service.decide_approval("A", fp, approve=True)
    assert env["calls"] == []


def test_resolve_requires_every_check_on_the_server(env):
    state = st.load()
    state["human_queue"] = {"C": {"amount": 340.0, "what_to_check": ["a", "b", "c"],
                                  "package": {"stage": "CHARGEBACK"}}}
    st.save(state)
    body = "Hello, the USD 340.00 was already returned to your card through your bank."
    service.resolve("C", "Your order", body, ["0", "1"])        # one check missing
    assert env["calls"] == []
    service.resolve("C", "Your order", body, ["0", "1", "7"])   # an index that doesn't exist
    assert env["calls"] == []
    service.resolve("C", "Your order", body, ["0", "1", "2"])
    assert env["calls"] == ["resolved"]


def test_a_conflicting_save_reruns_the_step_once(env, monkeypatch):
    """Another container saved first: the step reruns on fresh state, and on the
    rerun the approval is checked again (here it still matches, so it completes once)."""
    real_act, attempts = service.agent.act, []

    def act_conflicting_once(c, s, it, ask):
        attempts.append(1)
        if len(attempts) == 1:
            raise st.StateConflict("someone saved first")
        real_act(c, s, it, ask)
    monkeypatch.setattr(service.agent, "act", act_conflicting_once)

    service.decide_approval("A", _shown_fingerprint(env["item"]), approve=True)
    assert len(attempts) == 2 and env["calls"] == ["y"]


def test_two_conflicts_in_a_row_ask_the_person_to_reload(env, monkeypatch):
    def always_conflicts(c, s, it, ask):
        raise st.StateConflict("someone saved first")
    monkeypatch.setattr(service.agent, "act", always_conflicts)

    service.decide_approval("A", _shown_fingerprint(env["item"]), approve=True)
    assert "Reload the page" in st.load()["web"]["notice"]["text"]
