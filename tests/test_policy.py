from datetime import datetime, timezone
from itertools import product

import pytest

from merchant.policy import (ACCEPT, CHALLENGE, ESCALATE, MIN_CHALLENGE_PROB, Dispute,
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

def test_a_near_deadline_without_evidence_goes_to_a_person():
    tight = Dispute("A", 1240.0, "USD", "FRAUDULENT", "RFI", "REQUIRES_RESPONSE",
                    "2026-10-22T18:00:00+0000")          # about 1.25 days after NOW
    d = decide(tight, A_FLAGS, NOW)
    assert d.action == ESCALATE and d.urgent


def test_a_near_deadline_with_evidence_ready_is_still_challenged():
    tight = Dispute("A", 1240.0, "USD", "FRAUDULENT", "RFI", "REQUIRES_RESPONSE",
                    "2026-10-22T18:00:00+0000")
    d = decide(tight, A_FLAGS, NOW, evidence_ready=True)
    assert d.action == CHALLENGE


def test_escalation_near_deadline_is_urgent():
    soon = Dispute("C", 340.0, "USD", "CREDIT_NOT_PROCESSED", "CHARGEBACK",
                   "REQUIRES_RESPONSE", "2026-10-23T12:00:00+0000")   # 2 days after NOW
    d = decide(soon, C_FLAGS, NOW)
    assert d.action == ESCALATE and d.urgent


# ---- Break-even line ----

def test_a_break_even_is_low_and_the_policy_minimum_is_the_bar():
    d = decide(A, A_FLAGS, NOW)
    assert d.break_even_p == pytest.approx(25 / 1240)          # about 2%
    assert d.required_p == MIN_CHALLENGE_PROB                  # 50% is the real bar
    assert d.money_decided and d.p_win >= d.required_p


def test_a_after_rejection_the_arbitration_fee_raises_the_break_even():
    rejected = Dispute("A", 1240.0, "USD", "FRAUDULENT", "CHARGEBACK",
                       "REQUIRES_RESPONSE", DUE, rejected_before=True)
    d = decide(rejected, A_FLAGS, NOW)
    assert d.break_even_p == pytest.approx(500 / 1240)         # about 40%
    assert d.required_p == MIN_CHALLENGE_PROB
    assert d.p_win < d.break_even_p                            # money alone flips it


def test_b_cannot_break_even_when_the_fee_exceeds_the_amount():
    d = decide(B, B_FLAGS, NOW)
    assert d.break_even_p > 1 and d.money_decided


def test_escalations_are_not_decided_by_money():
    assert not decide(C, C_FLAGS, NOW).money_decided
    tight = Dispute("A", 1240.0, "USD", "FRAUDULENT", "RFI", "REQUIRES_RESPONSE",
                    "2026-10-22T18:00:00+0000")
    assert not decide(tight, A_FLAGS, NOW).money_decided


def test_the_bar_always_agrees_with_the_decision():
    """Whenever money decides, CHALLENGE happens exactly when the win chance clears
    the bar. Protects the UI from ever showing a number that contradicts the action."""
    reasons = ["FRAUDULENT", "PRODUCT_NOT_RECEIVED", "CREDIT_NOT_PROCESSED", "OTHER"]
    amounts = [10, 18, 25, 26, 40, 50, 60, 100, 340, 500, 1240, 5000]
    flag_sets = [EvidenceFlags(m, s, sc, c, r)
                 for m, s, sc, c, r in product([0, 3], [False, True], [False, True],
                                               [0, 1], [False, True])]
    checked = 0
    for reason, amount, flags, rejected in product(reasons, amounts, flag_sets, [False, True]):
        dispute = Dispute("X", float(amount), "USD", reason, "RFI", "REQUIRES_RESPONSE",
                          DUE, rejected_before=rejected)
        d = decide(dispute, flags, NOW)
        if not d.money_decided:
            continue
        clears = d.p_win >= MIN_CHALLENGE_PROB and d.p_win > d.break_even_p
        assert (d.action == CHALLENGE) == clears, (reason, amount, flags, rejected, d)
        checked += 1
    assert checked > 1000