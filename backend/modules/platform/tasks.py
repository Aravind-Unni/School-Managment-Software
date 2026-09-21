"""Periodic platform tasks — outbox dispatch and backup age monitor."""

from __future__ import annotations


def dispatch_outbox() -> int:
    """Deliver pending outbox events via the sample consumer."""
    from django.conf import settings

    from .services.outbox import dispatch_pending

    return dispatch_pending(clock=settings.SCHOOL_CLOCK)


def monitor_backup_age() -> dict:
    """Return this deployment's newest-backup age against its policy threshold.

    Reads the school from settings and the threshold from its PlatformPolicy
    (falling back to the fixture default). Does not verify the backup restores.
    """
    from uuid import UUID

    from django.conf import settings
    from django.utils import timezone

    from .fixture_ids import BACKUP_AGE_ALERT_MINUTES
    from .models import BackupManifest, PlatformPolicy

    school_id = UUID(str(settings.SCHOOL_ID))
    policy = PlatformPolicy.objects.filter(school_id=school_id).first()
    alert_minutes = policy.backup_age_alert_minutes if policy else BACKUP_AGE_ALERT_MINUTES
    latest = BackupManifest.objects.filter(school_id=school_id).order_by("-created_at").first()
    if latest is None:
        return {"ok": False, "detail": "no_manifest"}
    age = timezone.now() - latest.created_at
    minutes = age.total_seconds() / 60.0
    return {
        "ok": minutes <= alert_minutes,
        "age_minutes": minutes,
        "alert_minutes": alert_minutes,
        "clock": str(settings.SCHOOL_CLOCK.now()),
    }
