"""The 'bank side' of the demo.

Every sandbox-only simulation call lives here, behind one interface.
Decision logic talks to DisputeSimulator and never to /simulation/ endpoints,
so this file can be swapped (real issuer feed, fake for tests) without
rewriting any decision code.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from client import AirwallexClient, AirwallexError

# Sandbox facts from the kit:
# - PRE_CHARGEBACK auto-accepts in the same second, so we never create it.
# - Escalating from CHARGEBACK fails with "Dispute transition is not supported".
CREATABLE_STAGES = {"RFI", "CHARGEBACK"}
ESCALATABLE_STAGES = {"RFI"}
RESOLUTIONS = {"MERCHANT", "CUSTOMER"}


def due_in(days: int) -> str:
    """Deadline N days from now, in Airwallex's format: 2026-10-28T09:00:00+0000."""
    when = datetime.now(timezone.utc) + timedelta(days=days)
    return when.strftime("%Y-%m-%dT%H:%M:%S%z")


def _clean(body: dict) -> dict:
    """Drop optional fields that weren't provided."""
    return {k: v for k, v in body.items() if v is not None}


class DisputeSimulator(ABC):
    """What the issuing bank / card network does to a dispute."""

    @abstractmethod
    def open_dispute(self, payment_intent_id: str, stage: str, reason_code: str,
                     due_days: int, amount: float | None = None,
                     comment: str | None = None) -> dict:
        """Cardholder's bank opens a dispute on a payment."""

    @abstractmethod
    def issuer_rejects_evidence(self, dispute_id: str, current_stage: str,
                                due_days: int, comment: str | None = None) -> dict:
        """Issuer declines the merchant's evidence; dispute moves to the next stage."""

    @abstractmethod
    def final_ruling(self, dispute_id: str, in_favor_of: str,
                     amount: float | None = None, comment: str | None = None) -> dict:
        """Network closes the dispute for the MERCHANT or the CUSTOMER."""


class AirwallexSandboxSimulator(DisputeSimulator):
    """Real implementation using Airwallex's sandbox simulation endpoints."""

    BASE = "/simulation/pa/payment_disputes"

    def __init__(self, client: AirwallexClient):
        self.client = client

    def open_dispute(self, payment_intent_id, stage, reason_code, due_days,
                     amount=None, comment=None):
        if stage not in CREATABLE_STAGES:
            raise ValueError(f"Refusing to create at stage {stage!r}. "
                             f"Use one of {sorted(CREATABLE_STAGES)}.")
        body = _clean({
            "payment_intent_id": payment_intent_id,
            "stage": stage,
            "reason_code": reason_code,
            "due_at": due_in(due_days),
            "amount": amount,
            "comment": comment,
        })
        return self.client.post(f"{self.BASE}/create", json=body)

    def issuer_rejects_evidence(self, dispute_id, current_stage, due_days, comment=None):
        if current_stage not in ESCALATABLE_STAGES:
            raise ValueError(f"Cannot escalate from {current_stage!r}; the sandbox "
                             f"only supports escalating from {sorted(ESCALATABLE_STAGES)}.")
        body = _clean({"due_at": due_in(due_days), "comment": comment})
        return self.client.post(f"{self.BASE}/{dispute_id}/escalate", json=body)

    def final_ruling(self, dispute_id, in_favor_of, amount=None, comment=None):
        if in_favor_of not in RESOLUTIONS:
            raise ValueError(f"in_favor_of must be one of {sorted(RESOLUTIONS)}.")
        body = _clean({"in_favor_of": in_favor_of, "amount": amount, "comment": comment})
        return self.client.post(f"{self.BASE}/{dispute_id}/resolve", json=body)


if __name__ == "__main__":
    # Smoke test without creating anything.
    sim = AirwallexSandboxSimulator(AirwallexClient())

    # 1. Local guard: must fail BEFORE any API call.
    try:
        sim.issuer_rejects_evidence("dsp_x", "CHARGEBACK", due_days=7)
    except ValueError as e:
        print("Guard OK:", e)

    # 2. Scope check: call resolve on a fake id.
    #    not_found / validation_error => endpoint reachable, Simulations scope OK.
    #    401 / 403 => the key is missing the Simulations permission.
    try:
        sim.final_ruling("dsp_does_not_exist", "MERCHANT")
    except AirwallexError as e:
        if e.status in (401, 403):
            print("Scope PROBLEM: add Simulations > Write to the API key.", e)
        else:
            print("Scope OK (expected error for a fake id):", e)

    print("Example deadline format:", due_in(7))