"""Serialise platform aggregates to contracted DTO shapes."""

from __future__ import annotations

from ..models import AuditRecord, Job, RestoreRehearsal
from .redaction import redacted_diff


def job_dto(row: Job) -> dict:
    """Return JobDTO wire shape."""
    return {
        "id": str(row.id),
        "kind": row.kind,
        "school_id": str(row.school_id),
        "actor_id": str(row.actor_id),
        "payload_ref": row.payload_ref,
        "state": row.state,
        "progress": row.progress,
        "error_code": row.error_code,
        "idempotency_key": row.idempotency_key,
        "version": row.version,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def audit_dto(row: AuditRecord) -> dict:
    """Return AuditRecordDTO with redacted_diff."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "actor_id": str(row.actor_id),
        "action": row.action,
        "aggregate_id": str(row.resource_id),
        "redacted_diff": redacted_diff(before=row.before, after=row.after),
        "request_id": row.request_id,
        "occurred_at": row.occurred_at.isoformat(),
    }


def restore_dto(row: RestoreRehearsal) -> dict:
    """Return RestoreRehearsalDTO wire shape."""
    return {
        "id": str(row.id),
        "backup_manifest_id": str(row.backup_manifest_id),
        "isolated_target_label": row.isolated_target_label,
        "state": row.state,
        "record_counts": dict(row.record_counts),
        "object_hashes_matched": row.object_hashes_matched,
        "fee_total_paise": row.fee_total_paise,
        "error_code": row.error_code,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }
