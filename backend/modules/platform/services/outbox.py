"""Outbox dispatch and sample consumer with receipt dedupe."""

from __future__ import annotations

from uuid import uuid4

from django.db import transaction

from ..models import ConsumerReceipt, OutboxEvent, OutboxState

#: In-process side-effect log for the sample consumer (tests assert once).
SAMPLE_SIDE_EFFECTS: list[str] = []


def dispatch_pending(*, limit: int = 50, clock) -> int:
    """Move pending outbox rows to dispatched and deliver to sample consumer.

    At-least-once: a crash after delivery but before state update may redeliver;
    ConsumerReceipt prevents duplicate side effects.
    """
    pending = list(
        OutboxEvent.objects.filter(state=OutboxState.PENDING).order_by("occurred_at")[:limit]
    )
    delivered = 0
    for row in pending:
        with transaction.atomic():
            locked = OutboxEvent.objects.select_for_update().get(event_id=row.event_id)
            if locked.state != OutboxState.PENDING:
                continue
            locked.state = OutboxState.DISPATCHING
            locked.attempts += 1
            locked.save(update_fields=["state", "attempts"])
            sample_consumer_handle(locked, clock=clock)
            locked.state = OutboxState.DISPATCHED
            locked.published_at = clock.now()
            locked.save(update_fields=["state", "published_at"])
            delivered += 1
    return delivered


def sample_consumer_handle(event: OutboxEvent, *, clock) -> bool:
    """Apply sample side effect once per (consumer, event_id).

    Returns True when the side effect ran, False when deduped.
    Does not emit further platform events (no receipt event storms).
    """
    consumer = "platform.sample_consumer"
    if ConsumerReceipt.objects.filter(consumer=consumer, event_id=event.event_id).exists():
        return False
    token = f"effect-{event.event_id}"
    SAMPLE_SIDE_EFFECTS.append(token)
    ConsumerReceipt.objects.create(
        id=uuid4(),
        consumer=consumer,
        event_id=event.event_id,
        school_id=event.school_id,
        received_at=clock.now(),
        side_effect_token=token,
    )
    return True


def reset_sample_side_effects() -> None:
    """Clear in-process side-effect log between tests."""
    SAMPLE_SIDE_EFFECTS.clear()
