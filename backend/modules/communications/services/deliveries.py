"""Delivery enqueue, process, reconcile and callbacks."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from django.db import transaction

from contracts.communications import DeliveryDTO
from contracts.errors import (
    ObjectInaccessible,
    StateConflict,
    Unauthenticated,
    ValidationFailed,
)
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from shared.fakes.platform import EagerModeNotAsserted

from ..models import (
    Attempt,
    CallbackNonce,
    Channel,
    Delivery,
    DeliveryState,
    MessageTemplate,
    ProviderConfig,
    VerifiedContact,
)
from .authority import AuthorityGate
from .content import assert_safe_text, assert_safe_variables
from .provider import SmsMessage, provider

logger = logging.getLogger(__name__)


def _payload_hash(
    template_key: str, locale: str, channel: str, variables: dict[str, object]
) -> str:
    """Stable SHA-256 of the logical message payload."""
    blob = json.dumps(
        {
            "template_key": template_key,
            "locale": locale,
            "channel": channel,
            "variables": variables,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _render(body: str, variables: dict[str, object]) -> str:
    """Escape and substitute {{var}} placeholders. Does not evaluate expressions."""
    rendered = body
    for key, value in variables.items():
        token = "{{" + key + "}}"
        rendered = rendered.replace(token, str(value).replace("<", "&lt;"))
    return rendered


def _attempt_dto(row: Attempt) -> dict:
    """Sanitize one attempt for API responses."""
    return {
        "id": str(row.id),
        "attempted_at": row.attempted_at.isoformat().replace("+00:00", "Z"),
        "outcome": row.outcome,
    }


def delivery_dto(row: Delivery, *, include_attempts: bool = True) -> dict:
    """Serialize a Delivery to the contracted API shape."""
    attempts = []
    if include_attempts:
        attempts = [
            _attempt_dto(a)
            for a in Attempt.objects.filter(delivery_id=row.id).order_by("attempted_at")
        ]
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "recipient_ref": str(row.recipient_ref),
        "channel": row.channel,
        "dedupe_key": row.dedupe_key,
        "payload_hash": row.payload_hash,
        "state": row.state,
        "provider_ref": row.provider_ref,
        "template_key": row.template_key,
        "locale": row.locale,
        "version": row.version,
        "created_at": row.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": row.updated_at.isoformat().replace("+00:00", "Z"),
        "attempts": attempts,
        "provider_status": row.state if row.provider_ref else None,
    }


@dataclass(frozen=True, slots=True)
class DeliveryService:
    """Enqueue, process, reconcile and accept SMS callbacks."""

    gate: AuthorityGate
    platform: object
    clock: object

    def enqueue(
        self,
        context: RequestContext,
        *,
        template_key: str,
        recipient_ref: UUID,
        channel: str,
        locale: str,
        variables: dict[str, object],
        dedupe_key: str,
    ) -> dict:
        """Create or replay a Delivery; process inline when no worker."""
        self.gate.require_action(context, "messages.send")
        if channel not in (Channel.IN_APP, Channel.SMS):
            raise ValidationFailed("error.validation_failed")
        if locale not in ("en", "ml"):
            raise ValidationFailed("error.validation_failed")
        assert_safe_variables(variables)
        template = (
            MessageTemplate.objects.filter(
                school_id=context.school_id, key=template_key, locale=locale
            )
            .order_by("-version")
            .first()
        )
        if template is None:
            raise ValidationFailed("communications.error.unknown_template")
        assert_safe_text(template.body)
        contact = VerifiedContact.objects.filter(
            school_id=context.school_id, recipient_ref=recipient_ref
        ).first()
        if contact is None or not contact.verified:
            raise ValidationFailed("communications.error.unverified_recipient")
        digest = _payload_hash(template_key, locale, channel, variables)
        rendered = _render(template.body, variables)
        now = self.clock.now()
        with transaction.atomic():
            existing = (
                Delivery.objects.select_for_update()
                .filter(school_id=context.school_id, dedupe_key=dedupe_key)
                .first()
            )
            if existing is not None:
                if existing.payload_hash != digest:
                    raise StateConflict("communications.error.dedupe_payload_mismatch")
                return delivery_dto(existing)
            row = Delivery.objects.create(
                school_id=context.school_id,
                recipient_ref=recipient_ref,
                channel=channel,
                dedupe_key=dedupe_key,
                payload_hash=digest,
                state=DeliveryState.QUEUED,
                template_key=template_key,
                locale=locale,
                variables=variables,
                rendered_body=rendered,
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="communications.delivery_queued",
                    resource_id=row.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    before={},
                    after={"state": "queued", "dedupe_key": dedupe_key},
                )
            )
            self._emit_status(context, row, now)
        self._schedule_or_process(row.id)
        row.refresh_from_db()
        return delivery_dto(row)

    def get(self, context: RequestContext, delivery_id: UUID) -> dict:
        """Return delivery status for messages.read_status."""
        self.gate.require_action(context, "messages.read_status")
        row = Delivery.objects.filter(id=delivery_id, school_id=context.school_id).first()
        if row is None:
            raise ObjectInaccessible("error.object_inaccessible")
        return delivery_dto(row)

    def process(self, delivery_id: UUID) -> None:
        """Worker entry: send or skip revoked; reconcile timeout before resend."""
        row = Delivery.objects.filter(id=delivery_id).first()
        if row is None or row.state not in (
            DeliveryState.QUEUED,
            DeliveryState.UNKNOWN,
            DeliveryState.SENDING,
        ):
            return
        contact = VerifiedContact.objects.filter(
            school_id=row.school_id, recipient_ref=row.recipient_ref
        ).first()
        now = self.clock.now()
        if contact is None or contact.revoked or not contact.purpose_allowed:
            Attempt.objects.create(
                school_id=row.school_id,
                delivery_id=row.id,
                attempted_at=now,
                outcome="skipped_revoked",
            )
            row.state = DeliveryState.FAILED
            row.updated_at = now
            row.save(update_fields=["state", "updated_at"])
            return
        if row.channel == Channel.IN_APP:
            row.state = DeliveryState.DELIVERED
            row.updated_at = now
            row.save(update_fields=["state", "updated_at"])
            Attempt.objects.create(
                school_id=row.school_id,
                delivery_id=row.id,
                attempted_at=now,
                outcome="delivered",
            )
            return
        sms = provider()
        config = ProviderConfig.objects.filter(school_id=row.school_id).first()
        sender_id = config.sender_id if config else "SCHFAKE"
        logger.info(
            "communications.sms_send secret_ref=%s delivery_id=%s",
            config.secret_ref if config else sms.secret_ref,
            row.id,
        )
        if row.provider_ref:
            looked = sms.lookup(row.provider_ref)
            if looked in ("accepted", "delivered"):
                row.state = looked
                row.updated_at = now
                row.save(update_fields=["state", "updated_at"])
                Attempt.objects.create(
                    school_id=row.school_id,
                    delivery_id=row.id,
                    attempted_at=now,
                    outcome="accepted" if looked == "accepted" else "delivered",
                )
                return
        row.state = DeliveryState.SENDING
        row.updated_at = now
        row.save(update_fields=["state", "updated_at"])
        result = sms.send(
            SmsMessage(
                body=row.rendered_body,
                sender_id=sender_id,
                recipient_ref=str(row.recipient_ref),
            ),
            idempotency_key=f"{row.school_id}:{row.dedupe_key}",
        )
        outcome = "timeout" if result.state == "unknown" else result.state
        Attempt.objects.create(
            school_id=row.school_id,
            delivery_id=row.id,
            attempted_at=now,
            outcome=outcome,
        )
        row.provider_ref = result.provider_ref
        row.state = DeliveryState.UNKNOWN if result.state == "unknown" else result.state
        row.updated_at = now
        row.version = row.version + 1
        row.save(update_fields=["provider_ref", "state", "updated_at", "version"])

    def reconcile(self, delivery_id: UUID) -> None:
        """Lookup provider_ref before any resend after uncertain timeout."""
        row = Delivery.objects.filter(id=delivery_id).first()
        if row is None or not row.provider_ref:
            return
        looked = provider().lookup(row.provider_ref)
        now = self.clock.now()
        if looked in ("accepted", "delivered"):
            row.state = looked
            row.updated_at = now
            row.save(update_fields=["state", "updated_at"])
            Attempt.objects.create(
                school_id=row.school_id,
                delivery_id=row.id,
                attempted_at=now,
                outcome="accepted" if looked == "accepted" else "delivered",
            )
            return
        if looked == "failed":
            row.state = DeliveryState.FAILED
            row.updated_at = now
            row.save(update_fields=["state", "updated_at"])
            return
        self.process(delivery_id)

    def accept_callback(
        self,
        *,
        school_id: UUID,
        provider_name: str,
        headers: dict[str, str],
        raw_body: bytes,
    ) -> dict:
        """Verify signature + replay; update delivery when valid."""
        sms = provider()
        try:
            event = sms.verify_callback(headers, raw_body)
        except Unauthenticated:
            raise
        now = self.clock.now()
        with transaction.atomic():
            if CallbackNonce.objects.filter(
                school_id=school_id, provider=provider_name, nonce=event.nonce
            ).exists():
                raise StateConflict("communications.error.callback_replay")
            CallbackNonce.objects.create(
                school_id=school_id,
                provider=provider_name,
                nonce=event.nonce,
                consumed_at=now,
            )
            row = (
                Delivery.objects.select_for_update()
                .filter(school_id=school_id, provider_ref=event.provider_ref)
                .first()
            )
            if row is None:
                return {"accepted": True}
            row.state = event.state
            row.updated_at = now
            row.version = row.version + 1
            row.save(update_fields=["state", "updated_at", "version"])
            Attempt.objects.create(
                school_id=school_id,
                delivery_id=row.id,
                attempted_at=now,
                outcome=event.state
                if event.state in ("delivered", "failed", "accepted")
                else "accepted",
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid4(),
                    school_id=school_id,
                    event_type="communications.delivery_status_changed",
                    occurred_at=now,
                    aggregate_id=row.id,
                    aggregate_version=row.version,
                    payload={"delivery_id": str(row.id), "state": row.state},
                    correlation_id=str(uuid4()),
                )
            )
        return {"accepted": True}

    def port_enqueue(
        self,
        context: RequestContext,
        template_key: str,
        recipient_ref: UUID,
        channel: str,
        locale: str,
        variables: dict[str, object],
        dedupe_key: str,
    ) -> DeliveryDTO:
        """CommunicationsPort.enqueue → compact DeliveryDTO."""
        full = self.enqueue(
            context,
            template_key=template_key,
            recipient_ref=recipient_ref,
            channel=channel,
            locale=locale,
            variables=variables,
            dedupe_key=dedupe_key,
        )
        return DeliveryDTO(id=UUID(full["id"]), state=full["state"])

    def _schedule_or_process(self, delivery_id: UUID) -> None:
        """Enqueue worker job when available; otherwise process inline."""
        try:
            self.platform.enqueue(
                "modules.communications.tasks.process_delivery",
                payload={"delivery_id": str(delivery_id)},
            )
        except EagerModeNotAsserted:
            self.process(delivery_id)

    def _emit_status(self, context: RequestContext, row: Delivery, now) -> None:
        """Append delivery_status_changed for the initial queued state."""
        self.platform.append_event(
            EventEnvelope(
                event_id=uuid4(),
                school_id=context.school_id,
                event_type="communications.delivery_status_changed",
                occurred_at=now,
                aggregate_id=row.id,
                aggregate_version=row.version,
                payload={"delivery_id": str(row.id), "state": row.state},
                correlation_id=context.request_id,
            )
        )
