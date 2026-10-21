"""Bank side: the issuer rejects the merchant's evidence on a challenged case.

Moves the dispute RFI -> CHARGEBACK, back to REQUIRES_RESPONSE.
"""
import sys

from bank.sandbox import AirwallexSandboxSimulator
from core.client import AirwallexClient
from records import state as st


def reject_evidence(client: AirwallexClient, state: dict, case_key: str) -> dict:
    dispute = state["disputes"][case_key]
    challenged = any(op.startswith(f"challenge_{case_key}_{dispute['id']}_")
                     for op in state.get("actions", {}))
    if not challenged:
        raise SystemExit(f"[{case_key}] hasn't been challenged yet; nothing to reject.")

    done = state.setdefault("rejections", {})
    if case_key in done:
        print(f"[{case_key}] evidence already rejected, skipping")
        return done[case_key]

    sim = AirwallexSandboxSimulator(client)
    d = sim.issuer_rejects_evidence(
        dispute["id"],
        current_stage=dispute.get("stage", "RFI"),
        due_days=7,
        comment="Evidence does not prove the cardholder took part in the transaction.",
    )
    done[case_key] = {"stage": d.get("stage"), "status": d.get("status")}
    dispute.update(done[case_key])
    st.save(state)
    print(f"[{case_key}] issuer rejected the evidence -> {d.get('stage')} / {d.get('status')}")
    return done[case_key]


if __name__ == "__main__":
    reject_evidence(AirwallexClient(), st.load(), sys.argv[1] if len(sys.argv) > 1 else "A")