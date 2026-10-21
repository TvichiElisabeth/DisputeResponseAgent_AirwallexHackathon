"""Merchant actions on disputes, over REST (the MCP challenge tool lacks fields).

Every action runs at most once per dispute: its result is saved in state,
and its request_id is reused if the same action is retried.
"""
from core.client import AirwallexClient
from records import state as st

ACCEPT_REASONS = {
    "LOW_VALUE_TRANSACTION", "VALID_CUSTOMER_DISPUTE", "AGREEMENT_REACHED_WITH_CUSTOMER",
    "CUSTOMER_RELATIONSHIP_MAINTENANCE", "COLLABORATION_ACCEPTED_MANUAL", "OTHERS",
}
REFUND_REASONS = {"REQUESTED_BY_CUSTOMER", "DUPLICATE", "FRAUDULENT", "ABANDONED", "OTHERS"}

CHALLENGE_REASONS = {
    "CUSTOMER_WITHDRAWN", "CUSTOMER_REFUNDED", "PRODUCT_RECEIVED", "PURCHASE_HISTORY",
    "NOT_ENTITLED", "SEPARATE_PRODUCT", "AUTHENTIC_PRODUCT", "OTHER_REASONS",
}
CHALLENGEABLE_STAGES = {"RFI", "CHARGEBACK"}


def _already_done(state: dict, op: str):
    return state.setdefault("actions", {}).get(op)


def _record(state: dict, op: str, res: dict) -> dict:
    result = {"status": res.get("status"), "stage": res.get("stage")}
    state["actions"][op] = result
    st.save(state)
    return result


def accept(client: AirwallexClient, state: dict, dispute: dict, reason: str,
           description: str, accepted_by: str, refund_reason: str | None = None) -> dict:
    """dispute: a row from merchant.queue.read_queue().
    Refunds only at RFI: at CHARGEBACK the bank already took the money back."""
    if reason not in ACCEPT_REASONS:
        raise ValueError(f"Unknown accept reason {reason!r}")

    op = f"accept_{dispute['case']}_{dispute['id']}"
    if done := _already_done(state, op):
        print(f"[{dispute['case']}] already accepted ({done['status']}), skipping")
        return done

    body = {
        "request_id": st.request_id_for(state, op),
        "reason": reason,
        "description": description,
        "accepted_by": accepted_by,
    }
    if dispute["stage"] == "RFI":
        if refund_reason not in REFUND_REASONS:
            raise ValueError("Accepting at RFI needs a valid refund_reason")
        body["refund"] = {"amount": float(dispute["amount"]), "reason": refund_reason}

    res = client.post(f"/pa/payment_disputes/{dispute['id']}/accept", json=body)
    result = _record(state, op, res)
    print(f"[{dispute['case']}] accepted -> {result['stage']} / {result['status']}"
          + (" (refund requested)" if "refund" in body else ""))
    return result


def challenge(client: AirwallexClient, state: dict, dispute: dict, reason: str,
              evidence_file: dict, details: dict, challenged_by: str) -> dict:
    """dispute: a row from read_queue(). evidence_file: {"file_id", "sha256"} from
    evidence_files.upload(). details: structured order facts (ORDER_FACTS[case])."""
    if reason not in CHALLENGE_REASONS:
        raise ValueError(f"Unknown challenge reason {reason!r}")
    if dispute["status"] != "REQUIRES_RESPONSE" or dispute["stage"] not in CHALLENGEABLE_STAGES:
        raise ValueError(f"[{dispute['case']}] can't challenge at "
                         f"{dispute['stage']} / {dispute['status']}")

    # Stage is part of the key: a second challenge after a rejection is a new action.
    op = f"challenge_{dispute['case']}_{dispute['id']}_{dispute['stage']}"
    if done := _already_done(state, op):
        print(f"[{dispute['case']}] already challenged at this stage ({done['status']}), skipping")
        return done

    body = {
        "request_id": st.request_id_for(state, op),
        "reason": reason,
        "challenged_by": challenged_by,
        **details,
        "supporting_documents": {
            "documents": [{
                "type": "PRIMARY",
                "file_ids": [evidence_file["file_id"]],
                "description": "Prior undisputed orders with matching device and IP; signed delivery.",
            }],
        },
    }
    res = client.post(f"/pa/payment_disputes/{dispute['id']}/challenge", json=body)
    result = _record(state, op, res)
    result["evidence_sha256"] = evidence_file["sha256"]   # which exact file we argued with
    st.save(state)
    print(f"[{dispute['case']}] challenged ({reason}) -> {result['stage']} / {result['status']}")
    return result


if __name__ == "__main__":
    import sys

    from merchant.queue import read_queue
    from records.evidence_text import ORDER_FACTS

    client = AirwallexClient()
    state = st.load()
    queue = {r["case"]: r for r in read_queue(client, state)}
    what = sys.argv[1] if len(sys.argv) > 1 else ""

    if what == "accept-b":
        accept(client, state, queue["B"],
               reason="LOW_VALUE_TRANSACTION",
               description="Dispute fee ($25) exceeds the amount at risk ($18).",
               accepted_by="dispute-agent (auto, under $50 limit)",
               refund_reason="REQUESTED_BY_CUSTOMER")
    elif what == "challenge-a":
        evidence = state.get("evidence_files", {}).get("A")
        if not evidence:
            raise SystemExit("Upload A's evidence first: python -m merchant.evidence_files")
        challenge(client, state, queue["A"],
                  reason="PURCHASE_HISTORY",
                  evidence_file=evidence,
                  details=ORDER_FACTS["A"],
                  challenged_by="finance-ops-lead (approved)")
    else:
        print("Usage: python -m merchant.actions accept-b | challenge-a")