"""Module-local fake SMS provider. Never contacts a real gateway."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import uuid4

from contracts.errors import Unauthenticated


@dataclass(frozen=True, slots=True)
class SmsMessage:
    """Rendered SMS body ready for a provider send."""

    body: str
    sender_id: str
    recipient_ref: str


@dataclass(frozen=True, slots=True)
class ProviderSendResult:
    """Outcome of one provider send call."""

    provider_ref: str
    state: str


@dataclass(frozen=True, slots=True)
class VerifiedCallbackEvent:
    """Authenticated callback payload after signature + replay checks."""

    provider_ref: str
    state: str
    nonce: str


@dataclass
class FakeSmsProvider:
    """Deterministic SMS adapter for standalone and tests.

    Supports accepted, failed, timeout, lookup and signed callbacks. Records
    calls for assertions. Does not log secret values — only secret_ref.
    """

    secret_ref: str = "secrets/fake-sms"
    signing_secret: str = "fake-sms-signing-secret"
    mode: str = "accepted"
    sends: list[tuple[str, SmsMessage]] = field(default_factory=list)
    lookups: list[str] = field(default_factory=list)
    _states: dict[str, str] = field(default_factory=dict)
    _idempotency: dict[str, ProviderSendResult] = field(default_factory=dict)

    def send(self, message: SmsMessage, idempotency_key: str) -> ProviderSendResult:
        """Send or replay one message keyed by idempotency_key.

        Timeout mode still records an accepted provider_ref so reconcile can
        look it up without resending. Does not handle real network IO.
        """
        existing = self._idempotency.get(idempotency_key)
        if existing is not None:
            return existing
        self.sends.append((idempotency_key, message))
        provider_ref = f"fake-msg-{uuid4()}"
        if self.mode == "failed":
            result = ProviderSendResult(provider_ref=provider_ref, state="failed")
        elif self.mode == "timeout":
            self._states[provider_ref] = "accepted"
            result = ProviderSendResult(provider_ref=provider_ref, state="unknown")
        else:
            result = ProviderSendResult(provider_ref=provider_ref, state="accepted")
            self._states[provider_ref] = "accepted"
        self._idempotency[idempotency_key] = result
        return result

    def lookup(self, provider_ref: str) -> str:
        """Return provider-side state for reconcile-before-resend."""
        self.lookups.append(provider_ref)
        return self._states.get(provider_ref, "unknown")

    def sign(self, raw_body: bytes) -> str:
        """Return HMAC signature for a callback body (tests/fake server)."""
        return hmac.new(
            self.signing_secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()

    def verify_callback(
        self,
        headers: Mapping[str, str],
        raw_body: bytes,
    ) -> VerifiedCallbackEvent:
        """Validate signature then parse provider_ref/state/nonce.

        Raises Unauthenticated on bad signature. Caller enforces replay.
        """
        provided = headers.get("X-Sms-Signature") or headers.get("x-sms-signature") or ""
        expected = self.sign(raw_body)
        if not hmac.compare_digest(provided, expected):
            raise Unauthenticated("communications.error.callback_unauthenticated")
        import json

        payload = json.loads(raw_body.decode("utf-8"))
        return VerifiedCallbackEvent(
            provider_ref=str(payload["provider_ref"]),
            state=str(payload["state"]),
            nonce=str(payload["nonce"]),
        )

    def set_outage(self) -> None:
        """Simulate provider outage: subsequent sends fail."""
        self.mode = "failed"


#: Process-wide fake used by M11 standalone/tests. Production refuses this.
SMS_PROVIDER = FakeSmsProvider()


def provider() -> FakeSmsProvider:
    """Return the bound fake SMS adapter."""
    return SMS_PROVIDER
