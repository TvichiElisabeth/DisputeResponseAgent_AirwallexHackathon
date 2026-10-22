"""Bank side: the card network gives its final ruling and closes the dispute."""
import sys

from bank.sandbox import AirwallexSandboxSimulator
from core.client import AirwallexClient, AirwallexError
from records import state as st


def final_ruling(client: AirwallexClient, state: dict, case_key: str, in_favor_of: str) -> dict:
    rulings = state.setdefault("rulings", {})
    if case_key in rulings:
        print(f"[{case_key}] already ruled: {rulings[case_key]}")
        return rulings[case_key]

    dispute = state["disputes"][case_key]
    live = client.get(f"/pa/payment_disputes/{dispute['id']}")      # current status, not cached
    if live.get("status") not in {"CHALLENGED", "PENDING_DECISION"}:
        print(f"[{case_key}] status is {live.get('status')}: only disputes still being "
              f"argued can get a final ruling. Accepted disputes are already closed.")
        return {"skipped": live.get("status")}
    try:
        d = AirwallexSandboxSimulator(client).final_ruling(
            dispute["id"], in_favor_of,
            comment="Final ruling by the card network.")
    except AirwallexError as e:
        print(f"[{case_key}] resolve not applied: {e}")
        return {"error": str(e)}

    rulings[case_key] = {"in_favor_of": in_favor_of,
                         "stage": d.get("stage"), "status": d.get("status")}
    dispute.update({"stage": d.get("stage"), "status": d.get("status")})
    st.save(state)
    print(f"[{case_key}] ruled for {in_favor_of} -> {d.get('stage')} / {d.get('status')}")
    return rulings[case_key]


if __name__ == "__main__":
    case = sys.argv[1] if len(sys.argv) > 1 else "A"
    side = sys.argv[2] if len(sys.argv) > 2 else "CUSTOMER"
    final_ruling(AirwallexClient(), st.load(), case, side)