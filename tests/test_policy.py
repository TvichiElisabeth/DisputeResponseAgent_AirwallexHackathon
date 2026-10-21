from datetime import datetime, timezone

import pytest

from merchant.policy import (ACCEPT, CHALLENGE, ESCALATE, Dispute,
                             EvidenceFlags, decide)

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
DUE = "2026-10-28T10:50:09+0000"

A = Dispute("A", 1240.0, "USD", "FRAUDULENT", "RFI", "REQUIRES_RESPONSE", DUE)
B = Dispute("B", 18.0, "USD", "PRODUCT_NOT_RECEIVED", "CHARGEBACK", "REQUIRES_RESPONSE", DUE)
C = Dispute("C", 340.0, "USD", "CREDIT_NOT_PROCESSED", "CHARGEBACK", "REQUIRES_RESPONSE", DUE)

A_FLAGS = EvidenceFlags(prior_undisputed_matches=3, signed_delivery=True, delivery_scanned=True)
B_FLAGS = EvidenceFlags(delivery_scanned=True)
C_FLAGS = EvidenceFlags(unanswered_contacts=2)


def test_a_strong_fraud_case_is_challenged_with_approval():
    d = decide(A, A_FLAGS, NOW)
    assert d.action == CHALLENGE and d.needs_human and d.p_win == 0.85


def test_b_small_case_is_accepted_automatically():
    d = decide(B, B_FLAGS, NOW)
    assert d.action == ACCEPT and not d.needs_human


def test_c_merchant_at_fault_is_escalated():
    assert decide(C, C_FLAGS, NOW).action == ESCALATE


def test_a_after_rejection_flips_to_accept_with_approval():
    rejected = Dispute("A", 1240.0, "USD", "FRAUDULENT", "CHARGEBACK",
                       "REQUIRES_RESPONSE", DUE, rejected_before=True)
    d = decide(rejected, A_FLAGS, NOW)
    assert d.action == ACCEPT and d.needs_human and d.p_win == 0.34


def test_weak_fraud_evidence_is_not_challenged():
    assert decide(A, EvidenceFlags(), NOW).action == ACCEPT


def test_guards_block_closed_or_late_disputes():
    closed = Dispute("A", 1240.0, "USD", "FRAUDULENT", "RFI", "ACCEPTED", DUE)
    late = Dispute("A", 1240.0, "USD", "FRAUDULENT", "RFI", "REQUIRES_RESPONSE",
                   "2026-10-01T00:00:00+0000")
    with pytest.raises(ValueError):
        decide(closed, A_FLAGS, NOW)
    with pytest.raises(ValueError):
        decide(late, A_FLAGS, NOW)