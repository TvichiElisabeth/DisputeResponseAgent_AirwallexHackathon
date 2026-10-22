"""The model explains decisions the policy already made. It never changes them.

Covers two parts of the brief:
- propose a plan: a short reason per case, shown in the plan before anything runs(The rules propose the plan, because money decisions should be repeatable;
                                                                                 the model presents it and explains it, in plain language, to the person approving.)
- explain an exception: why C needs a person (plus what to check), and why A's
  decision changed after the bank rejected our evidence
"""
import anthropic

from core import config
from merchant.policy import Decision, EvidenceFlags
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
    "what you are given. Plain language, no jargon."
)


def explain(decision: Decision, facts: EvidenceFlags, evidence_summary: str,
            new_information: str | None = None) -> dict:
    prompt = (
        f"Case {decision.case}\n"
        f"Decision (final, made by rules): {decision.action}\n"
        f"Rule that fired: {decision.rule}\n"
        f"Win chance: {decision.p_win:.0%} | cost if accept: ${decision.cost_if_accept:,.2f} | "
        f"expected cost if challenge: ${decision.expected_cost_if_challenge:,.2f}\n"
        f"Needs a person: {decision.needs_human} | days to deadline: {decision.days_left}\n"
        f"Facts: {facts}\n"
        f"Evidence summary: {evidence_summary}\n"
    )
    if new_information:
        prompt += f"New information since the last decision: {new_information}\n"

    try:
        data = call_tool(SYSTEM, TOOL, prompt, max_tokens=600)
    except RuntimeError:
        # Words only, not money: fall back to the rule text the policy wrote.
        return {"explanation": decision.rule, "what_to_check": []}
    return {
        "explanation": str(data["explanation"]).strip()[:600],
        "what_to_check": [str(x)[:200] for x in data.get("what_to_check", [])][:3],
    }