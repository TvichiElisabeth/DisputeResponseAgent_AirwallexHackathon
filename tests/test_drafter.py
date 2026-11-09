"""Code checks on the customer reply. No model calls here."""
import os

# merchant.drafter -> merchant.llm -> core.config needs these to exist (values unused).
os.environ.setdefault("AWX_CLIENT_ID", "test")
os.environ.setdefault("AWX_API_KEY", "test")

from merchant.drafter import check_draft, template_reply  # noqa: E402
from merchant.policy import Dispute, resolution_for  # noqa: E402

C = Dispute("C", 340.0, "USD", "CREDIT_NOT_PROCESSED", "CHARGEBACK", "REQUIRES_RESPONSE",
            "2026-10-28T10:50:09+0000")
GOOD = ("Hello, I'm sorry your emails about your return went unanswered. We have accepted "
        "your case: the USD 340.00 was already returned to your card through your bank. "
        "Customer Support")


def test_a_good_chargeback_reply_passes():
    assert check_draft("Your return of order ORD-9750", GOOD, 340.0, "CHARGEBACK") == []


def test_reply_must_state_the_amount():
    assert check_draft("Your order", "Hello, it's sorted. Customer Support", 340.0, "CHARGEBACK")


def test_reply_must_not_mention_other_amounts():
    body = GOOD + " We also noticed a $25 fee."
    assert any("other amounts" in p for p in check_draft("Your order", body, 340.0, "CHARGEBACK"))


def test_at_chargeback_the_shop_must_not_claim_it_refunded():
    body = "Hello, we have refunded USD 340.00 to your card. Customer Support"
    assert check_draft("Refund", body, 340.0, "CHARGEBACK")
    # The same sentence is correct at RFI, where the shop does refund.
    assert check_draft("Refund", body, 340.0, "RFI") == []


def test_no_promises_beyond_the_resolution():
    body = GOOD + " As an apology, here is a 10% discount voucher."
    assert check_draft("Your order", body, 340.0, "CHARGEBACK")


def test_empty_or_too_long_replies_are_rejected():
    assert check_draft("", GOOD, 340.0, "CHARGEBACK")
    assert check_draft("Your order", GOOD + " x" * 700, 340.0, "CHARGEBACK")


def test_templates_always_pass_their_own_checks():
    for stage in ("CHARGEBACK", "RFI"):
        reply = template_reply("ORD-9750", 340.0, "USD", resolution_for(C, stage))
        assert check_draft(reply["subject"], reply["body"], 340.0, stage) == []
