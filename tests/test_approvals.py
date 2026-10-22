from datetime import datetime, timezone

import pytest

from merchant.approvals import request_approval, verify_approval
from merchant.policy import Dispute, EvidenceFlags, decide

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
ROW = {"case": "A", "id": "dst_test", "stage": "RFI", "amount": 1240.0, "currency": "USD",
       "reason_code": "10.4", "due_at": "2026-10-28T10:00:00+00:00"}
EVIDENCE = {"filename": "A_compelling_evidence.pdf", "sha256": "abc123"}
DECISION = decide(Dispute("A", 1240.0, "USD", "FRAUDULENT", "RFI", "REQUIRES_RESPONSE",
                          ROW["due_at"]),
                  EvidenceFlags(prior_undisputed_matches=3, signed_delivery=True), NOW)
NO_SAVE = lambda s: None


def approve(state, row=ROW, evidence=EVIDENCE):
    return request_approval(state, row, DECISION, "PURCHASE_HISTORY", evidence,
                            ask=lambda _: "y", save=NO_SAVE)


def test_approved_action_can_proceed():
    state = {}
    approve(state)
    assert verify_approval(state, ROW, DECISION, "PURCHASE_HISTORY", EVIDENCE) == "finance-ops-lead"


def test_changed_evidence_voids_approval():
    state = {}
    approve(state)
    with pytest.raises(PermissionError):
        verify_approval(state, ROW, DECISION, "PURCHASE_HISTORY",
                        {"filename": "A_compelling_evidence.pdf", "sha256": "DIFFERENT"})


def test_changed_amount_voids_approval():
    state = {}
    approve(state)
    with pytest.raises(PermissionError):
        verify_approval(state, {**ROW, "amount": 2000.0}, DECISION, "PURCHASE_HISTORY", EVIDENCE)


def test_no_approval_means_no_action():
    with pytest.raises(PermissionError):
        verify_approval({}, ROW, DECISION, "PURCHASE_HISTORY", EVIDENCE)