"""Thin Airwallex REST client: login, token refresh, errors, request_id."""
import time
import uuid

import requests

import core.config as config


class AirwallexError(Exception):
    """Raised for any non-2xx response, carrying Airwallex's error code."""

    def __init__(self, status: int, code, message, body):
        super().__init__(f"HTTP {status} | {code} | {message}")
        self.status = status
        self.code = code
        self.message = message
        self.body = body


def new_request_id() -> str:
    """New UUID per new operation. Reuse one only when retrying the same operation."""#reuse is handled in state.py
    return str(uuid.uuid4())


class AirwallexClient:
    TOKEN_TTL_SECONDS = 25 * 60  # tokens last 30 min; refresh 5 min early

    def __init__(self, timeout: int = 30):
        self.api_base = config.API_BASE.rstrip("/")
        self.files_base = config.FILES_BASE.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self._token = None
        self._token_time = 0.0

    # ---- auth ----
    def _login(self) -> None:
        r = self.session.post(
            f"{self.api_base}/authentication/login",
            headers={
                "x-client-id": config.AWX_CLIENT_ID,
                "x-api-key": config.AWX_API_KEY,
            },
            timeout=self.timeout,
        )
        self._raise_for(r)
        self._token = r.json()["token"]
        self._token_time = time.monotonic()

    def _auth_headers(self) -> dict:
        expired = time.monotonic() - self._token_time > self.TOKEN_TTL_SECONDS
        if self._token is None or expired:
            self._login()
        return {"Authorization": f"Bearer {self._token}"}

    # ---- errors ----
    @staticmethod
    def _raise_for(r: requests.Response) -> None:
        if r.ok:
            return
        try:
            body = r.json()
        except ValueError:
            body = {"message": r.text}
        raise AirwallexError(r.status_code, body.get("code"), body.get("message"), body)

    # ---- requests ----
    def request(self, method: str, path: str, *, json=None, params=None,
                files=None, data=None, use_files_host: bool = False) -> dict:
        base = self.files_base if use_files_host else self.api_base
        url = f"{base}{path}"
        for attempt in (1, 2):
            r = self.session.request(
                method, url,
                headers=self._auth_headers(),
                json=json, params=params, files=files, data=data,
                timeout=self.timeout,
            )
            if r.status_code == 401 and attempt == 1:
                self._token = None  # token rejected: log in again, retry once
                continue
            self._raise_for(r)
            return r.json() if r.content else {}
        raise RuntimeError("unreachable")

    def get(self, path: str, **kw) -> dict:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> dict:
        return self.request("POST", path, **kw)


if __name__ == "__main__":
    # Smoke test: login + one read call covered by the Payment Acceptance scope.
    client = AirwallexClient()
    result = client.get("/pa/payment_intents", params={"page_size": 1})
    print("Login OK. Payment intents endpoint reachable.")
    print("Items returned:", len(result.get("items", [])))