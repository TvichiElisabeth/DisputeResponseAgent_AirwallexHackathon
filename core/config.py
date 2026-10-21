"""Connection settings. Credentials come from .env, never from code."""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name}. Add it to your .env file.")
    return value


AWX_CLIENT_ID = _require("AWX_CLIENT_ID")
AWX_API_KEY = _require("AWX_API_KEY")

API_BASE = os.getenv("AWX_API_BASE", "https://api.sandbox.airwallex.com/api/v1")
FILES_BASE = os.getenv("AWX_FILES_BASE", "https://files.sandbox.airwallex.com/api/v1")

# Safety rail: this project must never point at production.
if "sandbox" not in API_BASE or "sandbox" not in FILES_BASE:
    raise RuntimeError("Refusing to run: API URLs must be sandbox URLs.")