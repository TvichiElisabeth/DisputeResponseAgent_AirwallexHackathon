"""Create and confirm one card payment per case, using the sandbox test card."""
import time

import records.state as st
from records.cases import CASES, Case
from core.client import AirwallexClient

#Instructions: Use test card 4035501000000008 with any future expiry and CVC when you create the payment intents.
TEST_CARD = {
    "number": "4035501000000008",   # kit's sandbox test card
    "expiry_month": "12",
    "expiry_year": "2030",          # any future date
    "cvc": "123",                   # any CVC
    "name": "Demo Customer",
}


def create_and_confirm(client: AirwallexClient, state: dict, case: Case) -> dict:
    payments = state.setdefault("payments", {})
    record = payments.get(case.key, {})

    if record.get("status") == "SUCCEEDED":
        print(f"[{case.key}] already paid ({record['id']}), skipping")
        return record

    # Step 1: create the payment intent (only once per case)
    if "id" not in record:
        order_id = f"{case.order_ref}-{int(time.time())}"
        res = client.post("/pa/payment_intents/create", json={
            "request_id": st.request_id_for(state, f"pi_create_{case.key}"),
            "amount": case.amount,
            "currency": case.currency,
            "merchant_order_id": order_id,
            "metadata": {"demo_case": case.key},
        })
        record = {"id": res["id"], "merchant_order_id": order_id,
                  "amount": case.amount, "currency": case.currency,
                  "status": res.get("status")}
        payments[case.key] = record
        st.save(state)
        print(f"[{case.key}] created {record['id']} ({res.get('status')})")

    # Step 2: confirm it with the test card
    res = client.post(f"/pa/payment_intents/{record['id']}/confirm", json={
        "request_id": st.request_id_for(state, f"pi_confirm_{case.key}"),
        "payment_method": {"type": "card", "card": TEST_CARD},
        "payment_method_options": {"card": {"auto_capture": True}},
    })
    record["status"] = res.get("status")
    st.save(state)
    print(f"[{case.key}] confirmed -> {record['status']}")

    if record["status"] != "SUCCEEDED":
        print(f"[{case.key}] WARNING: expected SUCCEEDED. next_action={res.get('next_action')}")
    return record


if __name__ == "__main__":
    client = AirwallexClient()
    state = st.load()
    for case in CASES:
        create_and_confirm(client, state, case)

    print("\nPayments:")
    for key, p in state["payments"].items():
        print(f"  {key}: {p['id']}  {p['currency']} {p['amount']:>9,.2f}  {p['status']}")