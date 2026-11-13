"""The shared case header: one component, driven by each case's data."""
import os
import re
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("AWX_CLIENT_ID", "test")
os.environ.setdefault("AWX_API_KEY", "test")

from merchant.policy import URGENT_DAYS  # noqa: E402
from records.evidence_text import BANK_CLAIM_SOURCE, BANK_CLAIMS, ORDERS  # noqa: E402
from web import view  # noqa: E402


def due(days: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")


ROWS = {
    "A": {"case": "A", "id": "dst_a", "amount": 1240.0, "currency": "USD", "reason_code": "10.4",
          "reason_type": "FRAUDULENT", "stage": "CHARGEBACK", "status": "REQUIRES_RESPONSE",
          "due_at": due(6.2), "payment_intent_id": "int_a"},
    "B": {"case": "B", "id": "dst_b", "amount": 18.0, "currency": "USD", "reason_code": "13.1",
          "reason_type": "PRODUCT_NOT_RECEIVED", "stage": "RFI", "status": "REQUIRES_RESPONSE",
          "due_at": due(4.5), "payment_intent_id": "int_b"},
    "C": {"case": "C", "id": "dst_c", "amount": 340.0, "currency": "USD", "reason_code": "13.6",
          "reason_type": "CREDIT_NOT_PROCESSED", "stage": "CHARGEBACK", "status": "REQUIRES_RESPONSE",
          "due_at": due(1.5), "payment_intent_id": "int_c"},
}


def header(case: str, open_: bool = True, **row) -> dict:
    return view.case_header({**ROWS[case], **row}, ORDERS[case], BANK_CLAIMS, BANK_CLAIM_SOURCE, open_)


def test_initials():
    assert view.initials("j.marin@example.com") == "JM"
    assert view.initials("a_popescu@example.com") == "AP"
    assert view.initials("sam@example.com") == "SA"


def test_case_a_maps_onto_the_header():
    h = header("A")
    assert (h["letter"], h["stage"], h["currency"], h["amount"]) == ("A", "Chargeback", "USD", "1,240.00")
    assert h["claim"] == {"text": "The cardholder says they did not make this purchase.",
                          "source": BANK_CLAIM_SOURCE}
    assert h["customer"] == {"email": "j.marin@example.com", "initials": "JM"}
    assert h["order"] == {"id": "ORD-9902", "product": "Laptop"}
    assert h["reason"] == {"type": "FRAUDULENT", "network": "Visa", "code": "10.4"}
    assert h["deadline"]["num"] == "6d" and not h["deadline"]["urgent"]


def test_each_case_gets_its_own_claim_from_its_visa_code():
    assert "never arrived" in header("B")["claim"]["text"]
    assert "never refunded" in header("C")["claim"]["text"]


def test_no_claim_text_means_no_claim_line():
    assert header("A", reason_code="99.9")["claim"] is None


def test_red_follows_the_policy_threshold():
    assert header("C")["deadline"]["urgent"]                       # 1.5 days
    assert header("A", due_at=due(URGENT_DAYS - 0.5))["deadline"]["urgent"]
    assert not header("A", due_at=due(URGENT_DAYS + 0.5))["deadline"]["urgent"]
    assert header("A", due_at=due(0.2))["deadline"]["num"].endswith("h")


def test_closed_case_shows_no_countdown():
    assert header("B", open_=False)["deadline"] == {"open": False}


# ---------------- the rendered page ----------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from records import state as st
    from web import service
    from web.main import app
    monkeypatch.setattr(st, "BACKEND", "file")
    monkeypatch.setattr(st, "STATE_PATH", tmp_path / "state.json")
    st.save({"request_ids": {}, "payments": {c: {"id": r["payment_intent_id"]} for c, r in ROWS.items()},
             "disputes": {c: {"id": r["id"], "stage": r["stage"]} for c, r in ROWS.items()},
             "actions": {}, "web": {}})
    monkeypatch.setattr(service, "client", lambda: object())
    monkeypatch.setattr(service, "read_queue", lambda c, s: [dict(r) for r in ROWS.values()])
    monkeypatch.setattr(service.refunds, "refunded_amount", lambda c, pid: 0)
    return TestClient(app)


@pytest.mark.parametrize("case", ["A", "B", "C"])
def test_unreviewed_case_has_no_empty_explanation_card(client, case):
    html = client.get(f"/cases/{case}").text
    assert "Why, in plain words" not in html and "Agent’s explanation" not in html


@pytest.mark.parametrize("case", ["A", "B"])
def test_reviewed_case_shows_the_agents_explanation(client, case):
    from merchant.policy import Dispute, EvidenceFlags, decide
    from records import state as st
    from web import service
    r = ROWS[case]
    flags = EvidenceFlags(prior_undisputed_matches=3, signed_delivery=True, delivery_scanned=True)
    d = decide(Dispute(case, r["amount"], r["currency"], r["reason_type"], r["stage"], r["status"],
                       r["due_at"]), flags)
    it = {"decision": d, "row": dict(r), "flags": flags,
          "note": {"explanation": f"Plain reason for case {case}.", "what_to_check": []}}
    s = st.load()
    s["web"] = {"review": {"at": "2026-11-12T09:14:00+00:00", "items": [service._serialize(it)], "agent": None}}
    st.save(s)
    html = client.get(f"/cases/{case}").text
    assert "Agent’s explanation" in html and f"Plain reason for case {case}." in html
    assert "Why, in plain words" not in html


@pytest.mark.parametrize("case", ["A", "B", "C"])
def test_every_case_page_uses_the_shared_header(client, case):
    html = client.get(f"/cases/{case}").text
    head = html[html.index('class="casehead-bar"'):html.index("</dl>")]
    assert f"CASE {case}" in head and ORDERS[case]["customer"] in head
    assert f'{ORDERS[case]["order_id"]} · {ORDERS[case]["product"]}' in head
    assert f'Visa {ROWS[case]["reason_code"]}' in head
    # four facts, each <dt> directly before its <dd> in the markup
    assert len(re.findall(r"<dt>.*?</dt>\s*<dd>", head, re.S)) == head.count("<dd>") == 4
    assert ("is-urgent" in head) == (case == "C")
