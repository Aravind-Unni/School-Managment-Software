"""Baseline seed for M14: policy, jobs, audit with secret, backup manifest."""

from __future__ import annotations

from django.db import transaction

from . import fixture_ids as ids
from .models import (
    AuditRecord,
    BackupManifest,
    Job,
    JobState,
    OutboxEvent,
    PlatformPolicy,
)
from .services.outbox import reset_sample_side_effects


def clear_baseline() -> None:
    """Drop every M14 row for the named schools and reset process state."""
    from .models import ConsumerReceipt, RestoreRehearsal

    school_ids = [ids.SCHOOL_A, ids.SCHOOL_B]
    for model in (
        RestoreRehearsal,
        ConsumerReceipt,
        OutboxEvent,
        AuditRecord,
        Job,
        BackupManifest,
    ):
        model.objects.filter(school_id__in=school_ids).delete()
    PlatformPolicy.objects.filter(school_id__in=school_ids).delete()
    reset_sample_side_effects()


def seed_baseline() -> dict:
    """Load the contracted M14 baseline and return counts for the seed command."""
    ids_map = _seed_baseline_rows()
    return {
        "jobs": 3,
        "audit_records": 1,
        "backup_manifests": 2,
        "policies": 1,
        **{k: str(v) for k, v in ids_map.items() if hasattr(v, "hex")},
    }


def _seed_baseline_rows() -> dict:
    """Load the contracted M14 baseline and return ids a test needs."""
    from django.conf import settings

    clock = settings.SCHOOL_CLOCK
    now = clock.now()
    with transaction.atomic():
        clear_baseline()
        PlatformPolicy.objects.create(
            school_id=ids.SCHOOL_A,
            backup_age_alert_minutes=ids.BACKUP_AGE_ALERT_MINUTES,
        )
        Job.objects.create(
            id=ids.JOB_FAILED,
            school_id=ids.SCHOOL_A,
            actor_id=ids.OPERATOR_ACTOR,
            kind="platform.sample_producer",
            payload_ref="payloads/sample-producer-1",
            state=JobState.FAILED,
            progress=40,
            error_code="platform.error.worker_interrupted",
            idempotency_key="sample-producer-1",
            version=2,
            created_at=now,
            updated_at=now,
        )
        Job.objects.create(
            id=ids.JOB_RUNNING,
            school_id=ids.SCHOOL_A,
            actor_id=ids.OPERATOR_ACTOR,
            kind="platform.sample_producer",
            payload_ref="payloads/sample-producer-running",
            state=JobState.RUNNING,
            progress=10,
            error_code=None,
            idempotency_key="sample-producer-running",
            version=1,
            created_at=now,
            updated_at=now,
        )
        Job.objects.create(
            id=ids.JOB_FOREIGN,
            school_id=ids.SCHOOL_B,
            actor_id=ids.OPERATOR_ACTOR,
            kind="platform.sample_producer",
            payload_ref="payloads/foreign",
            state=JobState.FAILED,
            progress=0,
            error_code="platform.error.worker_interrupted",
            idempotency_key="foreign-1",
            version=1,
            created_at=now,
            updated_at=now,
        )
        AuditRecord.objects.create(
            id=ids.AUDIT_WITH_SECRET,
            school_id=ids.SCHOOL_A,
            actor_id=ids.OPERATOR_ACTOR,
            action="platform.sample_write",
            resource_id=ids.JOB_FAILED,
            occurred_at=now,
            request_id="req-m14-baseline-1",
            before={},
            after={"token": "super-secret-value", "note": "ok"},
        )
        from .services.redaction import redact_mapping

        row = AuditRecord.objects.get(id=ids.AUDIT_WITH_SECRET)
        row.after = redact_mapping(row.after)
        row.save(update_fields=["after"])
        BackupManifest.objects.create(
            id=ids.BACKUP_MANIFEST_ID,
            school_id=ids.SCHOOL_A,
            db_point="wal-base-m14-a",
            object_versions=[
                {
                    "storage_key": "canonical/sample-ledger.bin",
                    "version_id": "v1",
                    "sha256": ids.SAMPLE_OBJECT_SHA256,
                }
            ],
            fee_total_paise=ids.SAMPLE_FEE_TOTAL_PAISE,
            record_counts={"audit_records": 2, "jobs": 1},
            verified_at=now,
            created_at=now,
        )
        BackupManifest.objects.create(
            id=ids.BACKUP_MANIFEST_FOREIGN,
            school_id=ids.SCHOOL_B,
            db_point="wal-base-m14-b",
            object_versions=[],
            fee_total_paise=0,
            record_counts={},
            verified_at=None,
            created_at=now,
        )
    return {
        "job_failed": ids.JOB_FAILED,
        "job_running": ids.JOB_RUNNING,
        "audit_with_secret": ids.AUDIT_WITH_SECRET,
        "backup_manifest_id": ids.BACKUP_MANIFEST_ID,
        "sample_fee_total_paise": ids.SAMPLE_FEE_TOTAL_PAISE,
    }


SCENARIOS = {
    "baseline": seed_baseline,
}
