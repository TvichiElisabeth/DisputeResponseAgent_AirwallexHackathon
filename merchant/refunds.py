"""Refund checks: confirm refunds happened, and never refund the same money twice."""
from core.client import AirwallexClient
from records import state as st

FAILED_STATUSES = {"FAILED", "CANCELLED"}   # anything else counts as money going back


def refunds_for(client: AirwallexClient, payment_intent_id: str) -> list[dict]:
    """All refunds on one payment. Filtered here in code, so it works even if
    the API ignores the payment_intent_id query parameter."""
    res = client.get("/pa/refunds", params={"payment_intent_id": payment_intent_id,
                                            "page_size": 100})
    return [r for r in res.get("items", []) if r.get("payment_intent_id") == payment_intent_id]


def refunded_amount(client: AirwallexClient, payment_intent_id: str) -> float:
    """How much of this payment is already on its way back to the customer."""
    return round(sum(float(r.get("amount", 0))
                     for r in refunds_for(client, payment_intent_id)
                     if r.get("status") not in FAILED_STATUSES), 2)


def can_refund(client: AirwallexClient, payment_intent_id: str, amount: float,
               paid_amount: float) -> bool:
    """Double-refund guard: only refund what hasn't been refunded yet."""
    return refunded_amount(client, payment_intent_id) + amount <= paid_amount


if __name__ == "__main__":
    client = AirwallexClient()
    state = st.load()

    print("Refunds per case:")
    for key, payment in state["payments"].items():
        refunds = refunds_for(client, payment["id"])
        if not refunds:
            print(f"  {key}  {payment['id']}  no refunds")
            continue
        for r in refunds:
            print(f"  {key}  {payment['id']}  refund {r.get('id')}  "
                  f"{r.get('currency')} {float(r.get('amount', 0)):,.2f}  "
                  f"{r.get('status')}  reason={r.get('reason')}")

    b = state["payments"]["B"]
    print(f"\nGuard check on B: can we refund another ${b['amount']:.2f}? "
          f"{can_refund(client, b['id'], b['amount'], b['amount'])}  (should be False)")