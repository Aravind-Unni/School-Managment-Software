"""Drive the product's HTTP API in-process as a given account.

Creates a real session for the account (as if it had just signed in with 2FA)
and sends requests through the full middleware stack with the session and
double-submit CSRF cookies set. Sessions are renewed before the step-up window
closes, so long seeding runs keep passing 2FA-freshness checks.
"""

from __future__ import annotations

import json
from datetime import timedelta

from django.conf import settings
from django.test import Client

#: Renew the session well inside the 300-second step-up window.
SESSION_MAX_AGE = timedelta(seconds=200)

DEMO_CSRF = "demo-seed-csrf-token"


class DemoApiError(RuntimeError):
    """A demo API call failed; carries the method, path, status and body."""


class ApiActor:
    """One signed-in account making API calls."""

    def __init__(self, user) -> None:
        """Remember the account; the session is created on first use."""
        self.user = user
        self._client: Client | None = None
        self._since = None

    def _session_client(self) -> Client:
        """Return a client whose session is fresh enough for step-up actions."""
        from modules.access.services.sessions import create_session

        now = settings.SCHOOL_CLOCK.now()
        if self._client is None or now - self._since > SESSION_MAX_AGE:
            issued = create_session(
                user=self.user, auth_level="password_totp", instant=now, user_agent="demo-seed"
            )
            host = next((h for h in settings.ALLOWED_HOSTS if h and h != "*"), "localhost")
            client = Client(HTTP_HOST=host.lstrip("."), secure=True)
            client.cookies["school_session"] = issued.token
            client.cookies["school_csrf"] = DEMO_CSRF
            self._client = client
            self._since = now
        return self._client

    def call(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        *,
        ok=(200, 201, 202, 204),
        idempotency_key: str | None = None,
    ):
        """Send one request to /api/v1<path>; return parsed JSON or raise DemoApiError."""
        client = self._session_client()
        url = f"/api/v1{path}"
        kwargs = {"HTTP_X_CSRF_TOKEN": DEMO_CSRF}
        if idempotency_key is not None:
            kwargs["HTTP_IDEMPOTENCY_KEY"] = idempotency_key
        if method == "GET":
            response = client.get(url, body or {}, **kwargs)
        else:
            response = getattr(client, method.lower())(
                url,
                data=json.dumps(body or {}),
                content_type="application/json",
                **kwargs,
            )
        if response.status_code not in ok:
            raise DemoApiError(
                f"{method} {url} -> {response.status_code}: {response.content[:400]!r}"
            )
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def get(self, path: str, query: dict | None = None):
        """GET a path with optional query parameters."""
        return self.call("GET", path, query)

    def post(self, path: str, body: dict | None = None, **options):
        """POST JSON."""
        return self.call("POST", path, body, **options)

    def put(self, path: str, body: dict, **options):
        """PUT JSON."""
        return self.call("PUT", path, body, **options)

    def patch(self, path: str, body: dict, **options):
        """PATCH JSON."""
        return self.call("PATCH", path, body, **options)
