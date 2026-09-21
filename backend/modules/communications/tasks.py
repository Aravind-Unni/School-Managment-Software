"""Celery tasks for delivery processing and reconcile."""

from __future__ import annotations

from uuid import UUID

from celery import shared_task

from .api import deps
from .models import Delivery, DeliveryState


@shared_task(name="modules.communications.tasks.process_delivery")
def process_delivery(delivery_id: str) -> None:
    """Process one queued delivery. Does not claim crash coverage when eager."""
    deps.delivery_service().process(UUID(delivery_id))


@shared_task(name="modules.communications.tasks.reconcile_unknown")
def reconcile_unknown() -> int:
    """Reconcile deliveries stuck in unknown after provider timeout."""
    service = deps.delivery_service()
    count = 0
    for row in Delivery.objects.filter(state=DeliveryState.UNKNOWN)[:100]:
        service.reconcile(row.id)
        count += 1
    return count
