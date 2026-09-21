"""Periodic platform tasks — outbox dispatch and backup age monitor."""

from __future__ import annotations


def dispatch_outbox() -> int:
    """Deliver pending outbox events via the sample consumer."""
    from django.conf import settings

    from .services.outbox import dispatch_pending

    return dispatch_pending(clock=settings.SCHOOL_CLOCK)


def monitor_backup_age() -> dict:
    """Return backup age status without claiming production RPO verification.

    PENDING for full-scale RPO/RTO; this only surfaces fixture-policy age.
    """
    from django.conf import settings
    from django.utils import timezone

    from .fixture_ids import BACKUP_AGE_ALERT_MINUTES, SCHOOL_A
    from .models import BackupManifest

    latest = BackupManifest.objects.filter(school_id=SCHOOL_A).order_by("-created_at").first()
    if latest is None:
        return {"ok": False, "detail": "no_manifest"}
    age = timezone.now() - latest.created_at
    minutes = age.total_seconds() / 60.0
    return {
        "ok": minutes <= BACKUP_AGE_ALERT_MINUTES,
        "age_minutes": minutes,
        "alert_minutes": BACKUP_AGE_ALERT_MINUTES,
        "clock": str(settings.SCHOOL_CLOCK.now()),
    }
