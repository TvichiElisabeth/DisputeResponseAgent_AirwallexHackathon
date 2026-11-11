"""The agent's tools and loop. No real model or Airwallex calls: the model is a
scripted fake, so these tests prove what code allows, refuses and decides."""
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

os.environ.setdefault("AWX_CLIENT_ID", "test")
os.environ.setdefault("AWX_API_KEY", "test")

import pytest  # noqa: E402

from merchant import agent, agent_loop, tools  # noqa: E402
from merchant.policy import ACCEPT, CHALLENGE, ESCALATE  # noqa: E402

DUE = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(timespec="seconds")
DUE_C = (datetime.now(timezone.utc) + timedelta(days=2, hours=12)).isoformat(timespec="seconds")
ROWS = [
    {"case": "A", "id": "dst_a", "amount": 1240.0, "currency": "USD", "reason_code": "10.4",
     "reason_type": "FRAUDULENT", "stage": "RFI", "status": "REQUIRES_RESPONSE", "due_at": DUE,
     "payment_intent_id": "int_a"},
    {"case": "B", "id": "dst_b", "amount": 18.0, "currency": "USD", "reason_code": "13.1",
     "reason_type": "PRODUCT_NOT_RECEIVED", "stage": "RFI", "status": "REQUIRES_RESPONSE",
     "due_at": DUE, "payment_intent_id": "int_b"},
    {"case": "C", "id": "dst_c", "amount": 340.0, "currency": "USD", "reason_code": "13.6",
     "reason_type": "CREDIT_NOT_PROCESSED", "stage": "CHARGEBACK", "status": "REQUIRES_RESPONSE",
     "due_at": DUE_C, "payment_intent_id": "int_c"},
]
A_ORDERS = ["ORD-7781 2026-03-02 $ 89.00 fp_8c21e9 82.77.14.203 no",
            "ORD-8112 2026-05-17 $ 214.50 fp_8c21e9 82.77.14.203 no",
            "ORD-8840 2026-07-29 $ 56.20 fp_8c21e9 82.77.14.203 no"]
A_SIGNED = "Delivered. Signed by: J. MARIN."
C_EMAILS = ["Please refund.", "It's been a week and still no refund."]


def ctx(rows=ROWS, state=None):
    return tools.ToolContext(client=None, state=state or {}, rows={r["case"]: dict(r) for r in rows})


# ---------------- record_facts: code checks every quote ----------------

def test_verified_quotes_are_accepted():
    c = ctx()
    r = tools.record_facts(c, "A", [
        {"field": "prior_undisputed_matches", "value": 3, "quotes": A_ORDERS},
        {"field": "signed_delivery", "value": True, "quotes": [A_SIGNED]}])
    assert r["accepted"] == ["prior_undisputed_matches", "signed_delivery"] and not r["rejected"]


def test_invented_quote_is_rejected():
    c = ctx()
    r = tools.record_facts(c, "A", [{"field": "signed_delivery", "value": True,
                                     "quotes": ["Signed by J. MARIN, ID checked by courier"]}])
    assert r["accepted"] == [] and "not found" in r["rejected"][0]["reason"]
    assert tools.flags_for(c, "A").signed_delivery is False          # stays at the safe default


def test_a_count_needs_one_quote_per_item():
    c = ctx()
    r = tools.record_facts(c, "A", [{"field": "prior_undisputed_matches", "value": 3,
                                     "quotes": A_ORDERS[:1]}])
    assert r["rejected"] and tools.flags_for(c, "A").prior_undisputed_matches == 0
    r = tools.record_facts(c, "A", [{"field": "prior_undisputed_matches", "value": 3,
                                     "quotes": [A_ORDERS[0]] * 3}])   # the same line three times
    assert r["rejected"]


def test_bad_types_unknown_fields_and_short_quotes_are_rejected():
    c = ctx()
    r = tools.record_facts(c, "A", [
        {"field": "signed_delivery", "value": "yes", "quotes": [A_SIGNED]},
        {"field": "prior_undisputed_matches", "value": True, "quotes": A_ORDERS},
        {"field": "amount", "value": 5, "quotes": []},
        {"field": "delivery_scanned", "value": True, "quotes": ["Deliv"]}])
    assert r["accepted"] == [] and len(r["rejected"]) == 4


def test_negative_facts_need_no_quote():
    c = ctx()
    r = tools.record_facts(c, "B", [{"field": "signed_delivery", "value": False, "quotes": []}])
    assert r["accepted"] == ["signed_delivery"]


def test_unknown_or_closed_case_is_an_error():
    result, is_error = tools.dispatch(ctx(), "get_evidence", {"case": "Z"})
    assert is_error and "Unknown" in result["error"]


# ---------------- evaluate_policy and submit_plan ----------------

def test_policy_runs_on_verified_facts_only():
    c = ctx()
    assert tools.evaluate_policy(c, "A")["policy_action"] == ACCEPT       # nothing verified yet
    tools.record_facts(c, "A", [
        {"field": "prior_undisputed_matches", "value": 3, "quotes": A_ORDERS},
        {"field": "signed_delivery", "value": True, "quotes": [A_SIGNED]}])
    assert tools.evaluate_policy(c, "A")["policy_action"] == CHALLENGE


def test_plan_must_cover_every_case_after_evaluation():
    c = ctx()
    items = [{"case": k, "action": ACCEPT, "reason": "r"} for k in "ABC"]
    with pytest.raises(tools.ToolError, match="evaluate_policy"):
        tools.submit_plan(c, items, "s")
    for k in "ABC":
        tools.evaluate_policy(c, k)
    with pytest.raises(tools.ToolError, match="Missing"):
        tools.submit_plan(c, items[:2], "s")
    with pytest.raises(tools.ToolError, match="action"):
        tools.submit_plan(c, [{"case": "A", "action": "REFUND", "reason": "r"}] + items[1:], "s")


def test_disagreement_is_recorded_not_obeyed():
    c = ctx()
    for k in "ABC":
        tools.evaluate_policy(c, k)
    items = [{"case": "A", "action": ACCEPT, "reason": "r"},
             {"case": "B", "action": CHALLENGE, "reason": "I think we can win"},   # policy: accept
             {"case": "C", "action": ACCEPT, "reason": "r"}]
    out = tools.submit_plan(c, items, "s")
    assert out["disagreements"] == ["B"]
    assert c.plan["items"][1]["policy_action"] == ACCEPT


def test_no_tool_can_move_money_or_simulate_the_bank():
    assert tools.TOOL_NAMES == {"list_open_disputes", "get_evidence", "get_refunds",
                                "record_facts", "evaluate_policy", "submit_plan"}
    assert {s["name"] for s in tools.TOOL_SPECS} == tools.TOOL_NAMES
    for banned in ("accept", "challenge", "refund_", "create", "escalate", "resolve", "simulat"):
        assert not any(banned in name for name in tools.TOOL_NAMES if name != "get_refunds")


# ---------------- the loop, with a scripted fake model ----------------

def use(name, **inp):
    return NS(type="tool_use", id=f"tu_{name}_{id(inp)}", name=name, input=inp)


class FakeModel:
    """Plays back a script of assistant turns; each turn is a list of blocks."""
    def __init__(self, turns):
        self.turns, self.calls = list(turns), 0
        self.messages = self

    def create(self, **kw):
        self.calls += 1
        blocks = self.turns.pop(0) if self.turns else [NS(type="text", text="Done.")]
        stop = "tool_use" if any(b.type == "tool_use" for b in blocks) else "end_turn"
        return NS(content=blocks, stop_reason=stop)


GOOD_SCRIPT = [
    [use("list_open_disputes")],
    [use("get_evidence", case="A"), use("get_evidence", case="B"), use("get_evidence", case="C")],
    [use("record_facts", case="A", facts=[
        {"field": "prior_undisputed_matches", "value": 3, "quotes": A_ORDERS},
        {"field": "signed_delivery", "value": True, "quotes": [A_SIGNED]}]),
     use("record_facts", case="B", facts=[{"field": "delivery_scanned", "value": True,
                                           "quotes": ["Delivered - left at front door."]}]),
     use("record_facts", case="C", facts=[{"field": "unanswered_contacts", "value": 2,
                                           "quotes": C_EMAILS}])],
    [use("evaluate_policy", case="A"), use("evaluate_policy", case="B"),
     use("evaluate_policy", case="C")],
]


def plan_turn(b_action):
    return [use("submit_plan", summary="C first: 2 days left.", items=[
        {"case": "A", "action": CHALLENGE, "reason": "Strong device and IP history."},
        {"case": "B", "action": b_action, "reason": "Small amount."},
        {"case": "C", "action": ESCALATE, "reason": "Customer ignored twice."}])]


def test_loop_finishes_with_a_plan_and_a_trace():
    run = agent_loop.run_agent(None, {}, [dict(r) for r in ROWS], llm=FakeModel(GOOD_SCRIPT + [plan_turn(ACCEPT)]))
    assert run.finished and run.stop == "plan submitted" and run.ctx.plan["disagreements"] == []
    tools_called = [t["tool"] for t in run.trace if t["kind"] == "tool"]
    assert tools_called[0] == "list_open_disputes" and tools_called[-1] == "submit_plan"


def test_model_that_never_submits_stops_after_one_nudge():
    model = FakeModel([[use("list_open_disputes")]])      # then only text
    run = agent_loop.run_agent(None, {}, [dict(r) for r in ROWS], llm=model)
    assert not run.finished and "without a plan" in run.stop and model.calls == 3


@pytest.fixture
def wired(monkeypatch):
    monkeypatch.setattr(agent, "open_cases", lambda c, s: [dict(r) for r in ROWS])
    monkeypatch.setattr(agent, "explain", lambda d, f, s, new_information=None:
                        {"explanation": d.rule, "what_to_check": []})
    monkeypatch.setattr(agent, "read_evidence", lambda s, case, rt: (tools.EvidenceFlags(), "fallback"))
    return {"disputes": {r["case"]: {"payment_intent_id": r["payment_intent_id"]} for r in ROWS}}


def test_agreeing_plan_keeps_the_policy_and_its_approval_rules(wired):
    items, info = agent.plan_with_run(None, wired, llm=FakeModel(GOOD_SCRIPT + [plan_turn(ACCEPT)]))
    by = {it["row"]["case"]: it for it in items}
    assert info["finished"] and info["summary"] == "C first: 2 days left."
    assert by["A"]["decision"].action == CHALLENGE and by["A"]["decision"].needs_human
    assert by["B"]["decision"].action == ACCEPT and not by["B"]["decision"].needs_human   # still automatic
    assert by["C"]["decision"].action == ESCALATE
    assert by["A"]["note"]["agent"]["quotes"]["signed_delivery"] == [A_SIGNED]


def test_disagreement_applies_the_policy_and_adds_a_person(wired):
    items, info = agent.plan_with_run(None, wired, llm=FakeModel(GOOD_SCRIPT + [plan_turn(CHALLENGE)]))
    b = next(it for it in items if it["row"]["case"] == "B")
    assert info["disagreements"] == ["B"]
    assert b["decision"].action == ACCEPT                 # the policy, not the model
    assert b["decision"].needs_human                      # scrutiny raised
    assert b["note"]["agent"]["disagrees"]


def test_failed_run_falls_back_and_needs_a_person_everywhere(wired):
    items, info = agent.plan_with_run(None, wired, llm=FakeModel([[NS(type="text", text="no")]]))
    assert not info["finished"]
    assert all(it["decision"].needs_human for it in items)
    assert all(it["note"]["agent"]["source"] == "reader (fallback)" for it in items)


# ---------------- new information reaches the agent only when it's true ----------------

class RecordingModel(FakeModel):
    def create(self, **kw):
        self.first_message = getattr(self, "first_message", kw["messages"][0]["content"])
        return super().create(**kw)


NOTICE = "The issuing bank rejected our evidence and moved the case to CHARGEBACK."


def test_no_rejection_means_no_rejection_notice(wired):
    model = RecordingModel(GOOD_SCRIPT + [plan_turn(ACCEPT)])
    items, info = agent.plan_with_run(None, wired, NOTICE, llm=model)
    assert "New information" not in model.first_message
    assert all("rejected" not in (it["note"]["explanation"] or "") for it in items)


def test_a_real_rejection_reaches_the_agent(wired):
    wired["rejections"] = {"A": {"at": "now"}}
    model = RecordingModel([[use("list_open_disputes")]])
    agent.plan_with_run(None, wired, NOTICE, llm=model)
    assert NOTICE in model.first_message
