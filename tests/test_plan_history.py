"""Plan history: the initial plan survives the bank's rejection, so the case page
can show it next to the revised plan. Pure data; no Airwallex, no model."""
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("AWX_CLIENT_ID", "test")
os.environ.setdefault("AWX_API_KEY", "test")

from merchant.policy import Dispute, EvidenceFlags, decide  # noqa: E402
from web import service, view  # noqa: E402

DUE = (datetime.now(timezone.utc) + timedelta(days=6)).isoformat(timespec="seconds")
FLAGS = EvidenceFlags(prior_undisputed_matches=3, signed_delivery=True, delivery_scanned=True)
T1, T_BANK, T2 = "2026-11-11T12:00:00+00:00", "2026-11-12T09:12:00+00:00", "2026-11-12T09:14:00+00:00"
REJECTION = {"stage": "CHARGEBACK", "status": "REQUIRES_RESPONSE", "from_stage": "RFI", "at": T_BANK}


def item(stage: str, rejected: bool, dispute_id: str = "dst_a") -> dict:
    d = decide(Dispute("A", 1240.0, "USD", "FRAUDULENT", stage, "REQUIRES_RESPONSE", DUE,
                       rejected_before=rejected), FLAGS)
    row = {"case": "A", "id": dispute_id, "amount": 1240.0, "currency": "USD", "stage": stage}
    return {"decision": d, "row": row, "flags": FLAGS,
            "note": {"explanation": f"why at {stage}", "agent": {"proposed": "CHALLENGE",
                                                                  "disagrees": rejected}}}


def history_after_rejection() -> list[dict]:
    w = {}
    service.record_plans(w, [item("RFI", False)], T1, {})
    service.record_plans(w, [item("CHARGEBACK", True)], T2, {"A": REJECTION})
    return w["plans"]["A"]


def test_initial_plan_survives_and_revision_is_added():
    h = history_after_rejection()
    assert [s["action"] for s in h] == ["CHALLENGE", "ACCEPT"]
    assert [s["stage"] for s in h] == ["RFI", "CHARGEBACK"]
    assert h[1]["rejected_before"] and h[1]["disagrees"]


def test_reviewing_again_without_news_adds_no_version():
    w = {}
    service.record_plans(w, [item("RFI", False)], T1, {})
    service.record_plans(w, [item("RFI", False)], "2026-11-11T13:00:00+00:00", {})
    assert len(w["plans"]["A"]) == 1


def test_a_new_dispute_starts_a_new_history():
    w = {}
    service.record_plans(w, [item("RFI", False, "dst_old")], T1, {})
    service.record_plans(w, [item("RFI", False, "dst_new")], T2, {})
    assert [s["dispute_id"] for s in w["plans"]["A"]] == ["dst_new"]


def test_revision_shows_both_plans_with_their_numbers():
    rev = view.revision(history_after_rejection(), REJECTION)
    assert rev["changed"]
    assert (rev["v1"]["action"], rev["v1"]["version"]) == ("CHALLENGE", 1)
    assert (rev["v2"]["action"], rev["v2"]["version"]) == ("ACCEPT", 2)
    assert rev["v1"]["line"] == "85% win chance; expected cost 211.00 vs 1,240.00 to accept."
    assert rev["v2"]["line"] == ("Evidence rejected, now at Chargeback. Win chance 34%, under the "
                                 "50% minimum; challenging is expected to cost 1,318.40 vs 1,240.00 "
                                 "to accept.")
    assert (rev["who"], rev["who_why"]) == ("You", "Over USD 50")
    assert rev["bank"] == {"at": T_BANK, "time": "09:12", "date": "12 Nov 2026, 09:12",
                           "from_stage": "RFI", "stage": "Chargeback"}
    assert rev["v2"]["at"] == "12 Nov, 09:14" and rev["agent_time"] == "09:14"


def test_no_revision_without_news_or_without_a_second_plan():
    h = history_after_rejection()
    assert view.revision(h, None) is None
    assert view.revision(h[:1], REJECTION) is None
    assert view.revision(h, {"stage": "CHARGEBACK"}) is None          # old record: no time
    assert view.revision(h, {**REJECTION, "at": "2026-11-13T00:00:00+00:00"}) is None  # not reviewed since


def test_new_timeline_entries():
    rev = view.revision(history_after_rejection(), REJECTION)
    bank, agent = view.revised_nodes(rev, FLAGS)
    assert bank["new"] and bank["weight"] == "against" and bank["when"] == "09:12"
    assert bank["text"] == "Rejected our evidence and moved the case to Chargeback."
    facts = dict(agent["facts"])
    assert agent["new"] and agent["when"] == "Read everything again · 09:14"
    assert facts["Matching earlier orders"] == "3" and facts["Signed delivery"] == "yes"
    assert facts["Bank decision"] == "evidence rejected" and facts["Stage"] == "Chargeback"
    assert facts["Win chance"] == "34% (was 85%)" and facts["Refund issued"] == "no"
    assert list(facts)[-1] == "Refund issued"
