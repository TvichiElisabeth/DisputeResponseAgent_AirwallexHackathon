"""Bank side: the issuer opens one dispute per case."""
from bank.sandbox import AirwallexSandboxSimulator, DisputeSimulator
from core.client import AirwallexClient
from records import state as st
from records.cases import CASES

# What the cardholder told their bank (synthetic). The agent reads this later.
CARDHOLDER_CLAIMS = {
    "A": "Cardholder states they did not authorise this purchase.",
    "B": "Cardholder states the parcel never arrived.",
    "C": "Cardholder returned the item and was promised a refund that never came.",
}


def open_disputes(sim: DisputeSimulator, state: dict) -> None:
    disputes = state.setdefault("disputes", {})
    for case in CASES:
        if case.key in disputes:
            print(f"[{case.key}] dispute already open ({disputes[case.key]['id']}), skipping")
            continue
        pi_id = state["payments"][case.key]["id"]
        d = sim.open_dispute(
            payment_intent_id=pi_id,
            stage=case.start_stage,
            reason_code=case.reason_code,
            due_days=case.due_days,
            comment=CARDHOLDER_CLAIMS[case.key],
        )
        disputes[case.key] = {"id": d["id"], "payment_intent_id": pi_id}
        st.save(state)  # save after EACH one, so a crash never causes a duplicate
        print(f"[{case.key}] opened {d['id']} at {d.get('stage')} / {d.get('status')}")


if __name__ == "__main__":
    open_disputes(AirwallexSandboxSimulator(AirwallexClient()), st.load())