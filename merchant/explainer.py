"""The model explains decisions the policy already made. It never changes them.

Covers two parts of the brief:
- propose a plan: a short reason per case, shown in the plan before anything runs(The rules propose the plan, because money decisions should be repeatable;
                                                                                 the model presents it and explains it, in plain language, to the person approving.)
- explain an exception: why C needs a person (plus what to check), and why A's
  decision changed after the bank rejected our evidence
"""
import anthropic

from core import config
import math

from merchant.policy import (ARBITRATION_FEE, DISPUTE_FEE, MIN_CHALLENGE_PROB, Decision,
                             EvidenceFlags)
from merchant.llm import call_tool

TOOL = {
    "name": "record_explanation",
    "description": "Explain a dispute decision to a finance ops lead.",
    "input_schema": {
        "type": "object",
        "properties": {
            "explanation": {
                "type": "string",
                "description": "2-3 plain sentences: why this decision follows from the "
                               "facts and the money. Do not suggest a different action.",
            },
            "what_to_check": {
                "type": "array", "items": {"type": "string"}, "maxItems": 3,
                "description": "Only for ESCALATE or decisions after new information: up to "
                               "3 concrete things the person should verify. Else empty.",
            },
        },
        "required": ["explanation"],
    },
}

SYSTEM = (
    "You explain chargeback decisions that were already made by the merchant's rules. "
    "Never recommend a different action and never invent facts or numbers: use only "
    "what you are given. Plain language, no jargon. If you are told the previous "
    "decision and it differs from the current one, say clearly that the decision changed "
    "and what caused it."
)


def _bar_line(decision: Decision) -> str:
    """The break-even numbers, as plain facts the model may cite."""
    be, req = decision.break_even_p, decision.required_p
    if be is None:
        line = "Break-even: not applicable (no amount at risk)."
    elif be >= 1:
        line = (f"Break-even win chance: {be:.0%}, i.e. above 100%: the fee is more than "
                f"the amount, so no win chance makes challenging pay.")
    else:
        line = (f"Win chance needed to challenge: {req:.0%} (the higher of the cost "
                f"break-even {be:.0%} and the {MIN_CHALLENGE_PROB:.0%} policy minimum).")
    if not decision.money_decided:
        line += " The money comparison did NOT decide this case; the rule above did."
    return line


def _rejection_line(decision: Decision) -> str:
    """After the bank rejects our evidence: how the fee that counts raised the bar.
    Empty unless this decision was priced with the arbitration fee."""
    amount, be = decision.cost_if_accept, decision.break_even_p
    if amount <= 0 or be is None or not math.isclose(be, ARBITRATION_FEE / amount):
        return ""
    return (f"Before the rejection, challenging cost the ${DISPUTE_FEE:.0f} dispute fee, so "
            f"the break-even was {DISPUTE_FEE / amount:.0%}. Fighting on now costs the "
            f"${ARBITRATION_FEE:.0f} arbitration fee (the ${DISPUTE_FEE:.0f} is already spent), "
            f"so the break-even rose to {be:.0%}.")


def explain(decision: Decision, facts: EvidenceFlags, evidence_summary: str,
            new_information: str | None = None) -> dict:
    prompt = (
        f"Case {decision.case}\n"
        f"Decision (final, made by rules): {decision.action}\n"
        f"Rule that fired: {decision.rule}\n"
        f"Win chance: {decision.p_win:.0%} | cost if accept: ${decision.cost_if_accept:,.2f} | "
        f"expected cost if challenge: ${decision.expected_cost_if_challenge:,.2f}\n"
        f"{_bar_line(decision)}\n"
        f"Needs a person: {decision.needs_human} | days to deadline: {decision.days_left}\n"
        f"Facts: {facts}\n"
        f"Evidence summary: {evidence_summary}\n"
    )
    if new_information:
        prompt += f"New information since the last decision: {new_information}\n"
        if line := _rejection_line(decision):
            prompt += f"{line}\n"

    try:
        data = call_tool(SYSTEM, TOOL, prompt, max_tokens=600)
    except RuntimeError:
        # Words only, not money: fall back to the rule text the policy wrote.
        return {"explanation": decision.rule, "what_to_check": []}
    return {
        "explanation": str(data["explanation"]).strip()[:600],
        "what_to_check": [str(x)[:300] for x in data.get("what_to_check", [])][:3],
    }