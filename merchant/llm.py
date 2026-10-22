"""One place to call the model with a typed tool.

Some models don't allow forcing a tool, so we ask for it, then CHECK in code
that the answer came back through the tool. One retry, then fail loudly.
"""
import anthropic

from core import config

def call_tool(system: str, tool: dict, user: str, max_tokens: int = 1024) -> dict:
    client = anthropic.Anthropic()
    system = (f"{system}\n\nAlways answer by calling the {tool['name']} tool exactly once, "
              f"filling in every required field. Do not answer in plain text.")
    for attempt in (1, 2):
        msg = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            tools=[tool],
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": user}],
        )
        for block in msg.content:
            if block.type == "tool_use" and block.name == tool["name"]:
                required = tool["input_schema"].get("required", [])
                missing = [k for k in required if k not in block.input]
                if not missing:
                    return block.input
                print(f"  (model left out {missing}; asking again)")
    raise RuntimeError(f"Model did not return a complete {tool['name']} after 2 attempts.")