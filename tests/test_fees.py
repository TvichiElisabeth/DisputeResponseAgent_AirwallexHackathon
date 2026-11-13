"""Fees paid and avoided: counted only from actions Airwallex accepted."""
import os
import re

os.environ.setdefault("AWX_CLIENT_ID", "test")
os.environ.setdefault("AWX_API_KEY", "test")

from merchant.policy import ARBITRATION_FEE, DISPUTE_FEE  # noqa: E402
from web import service  # noqa: E402

ROWS = [{"case": "A", "id": "dst_a", "amount": 1240.0, "currency": "USD"},
        {"case": "B", "id": "dst_b", "amount": 18.0, "currency": "USD"},
        {"case": "C", "id": "dst_c", "amount": 340.0, "currency": "USD"}]


def sandbox_state() -> dict:
    """The demo after A was challenged, rejected and accepted, B auto-accepted,
    and C escalated to a person."""
    return {"actions": {"challenge_A_dst_a_RFI": {}, "accept_A_dst_a": {}, "accept_B_dst_b": {}},
            "rejections": {"A": {"at": "2026-11-12T09:12:00+00:00"}},
            "human_queue": {"C": {}},
            "web": {"plans": {"A": [{"dispute_id": "dst_a", "rejected_before": False},
                                    {"dispute_id": "dst_a", "rejected_before": True}],
                              "B": [{"dispute_id": "dst_b", "rejected_before": False}]}}}


def lines(f: dict) -> dict:
    return {a["case"]: a for a in f["avoided_lines"]}


def test_sandbox_totals():
    f = service.fees_summary(sandbox_state(), ROWS)
    assert f["avoided_total"] == 525.00 and f["paid_total"] == 25.00 and f["at_stake"] == 550.00
    by = lines(f)
    assert (by["A"]["fee_name"], by["A"]["amount"]) == ("Arbitration fee", ARBITRATION_FEE)
    assert (by["B"]["fee_name"], by["B"]["amount"]) == ("Dispute fee", DISPUTE_FEE)
    assert "more than the USD 18.00" in by["B"]["reason"]
    assert f["paid_lines"] == [{"case": "A", "fee_name": "Dispute fee", "amount": DISPUTE_FEE,
                                "reason": "Evidence submitted at RFI", "counted": True,
                                "share": DISPUTE_FEE / 550}]


def test_an_accepted_case_counts_its_fee():
    s = {"actions": {"accept_B_dst_b": {}}}
    assert lines(service.fees_summary(s, ROWS))["B"]["amount"] == DISPUTE_FEE


def test_a_planned_accept_that_was_not_sent_counts_nothing():
    s = sandbox_state()
    del s["actions"]["accept_A_dst_a"]          # planned and approved on screen, never sent
    a = lines(service.fees_summary(s, ROWS))["A"]
    assert not a["counted"] and a["amount"] == 0 and a["reason"] == "Open, no decision sent yet"


def test_an_escalated_case_counts_nothing_until_a_person_accepts():
    s = sandbox_state()
    c = lines(service.fees_summary(s, ROWS))["C"]
    assert not c["counted"] and c["reason"] == "Escalated, still with a person"
    s["actions"]["accept_C_dst_c"] = {}
    s["human_queue"] = {}
    s["resolved_escalations"] = {"C": {}}
    c = lines(service.fees_summary(s, ROWS))["C"]
    assert c["counted"] and c["amount"] == DISPUTE_FEE and c["reason"] == "Accepted by a person after escalation"


def test_fee_depends_on_an_earlier_rejection():
    s = {"actions": {"accept_A_dst_a": {}}, "web": {"plans": {"A": [{"dispute_id": "dst_a",
                                                                     "rejected_before": True}]}}}
    assert lines(service.fees_summary(s, ROWS))["A"]["amount"] == ARBITRATION_FEE
    s["web"]["plans"]["A"][0]["rejected_before"] = False
    assert lines(service.fees_summary(s, ROWS))["A"]["amount"] == DISPUTE_FEE


def test_a_rejection_of_an_older_dispute_does_not_count():
    s = {"actions": {"accept_A_dst_a": {}}, "web": {"plans": {"A": [{"dispute_id": "dst_old",
                                                                     "rejected_before": True}]}}}
    assert lines(service.fees_summary(s, ROWS))["A"]["amount"] == DISPUTE_FEE


def test_rings_draw_the_amounts():
    r = service.fee_rings(service.fees_summary(sandbox_state(), ROWS))
    av = r["avoided"]
    assert av["total"] == 525
    assert [round(s["dash"] + s["rest"], 2) for s in av["slices"]] == [525, 525]
    assert sum(s["dash"] for s in av["slices"]) < 525                  # gaps between slices
    assert {c["tile"] for c in av["callouts"]} == {"A", "B", "C"}
    c = next(c for c in av["callouts"] if c["tile"] == "C")
    assert c["dot"] is None and c["path"] is None and c["muted"]
    for side in (1, -1):                                                 # labels never overlap
        col = sorted((c for c in av["callouts"] if c["side"] == side), key=lambda c: c["ly"])
        assert all(b["ly"] - 17 >= a["ly"] - 17 + a["height"] for a, b in zip(col, col[1:]))
    for c in av["callouts"]:                                             # leaders end at the label column
        if c["path"]:
            xs = [float(n) for n in re.findall(r"[MLH](-?[\d.]+)", c["path"])]
            assert all((x <= xs[-1]) if c["side"] > 0 else (x >= xs[-1]) for x in xs)
    assert "USD 500.00" in av["aria"] and "USD 25.00" in av["aria"] and "Case C not counted" in av["aria"]
    assert (r["paid_total"], r["paid_sub"]) == ("USD 25.00", "Case A · evidence submitted at RFI")


def test_no_fees_yet_still_draws_an_empty_ring():
    r = service.fee_rings(service.fees_summary({}, ROWS))
    assert r["avoided"]["slices"] == []
    assert r["avoided_total"] == "USD 0.00" and r["paid_sub"] == "No evidence submitted yet"
