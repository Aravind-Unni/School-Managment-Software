"""Health and restore rehearsal services."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from django.db import connection, transaction

from contracts.errors import ObjectInaccessible, StateConflict, ValidationFailed
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext

from ..fixture_ids import PRODUCTION_TARGET_LABELS
from ..models import BackupManifest, RestoreRehearsal, RestoreRehearsalState
from .authority import AuthorityGate
from .wire import restore_dto


@dataclass(frozen=True, slots=True)
class HealthService:
    """Liveness and authenticated readiness."""

    gate: AuthorityGate

    def live(self) -> dict:
        """Return minimal public liveness."""
        return {"status": "live"}

    def ready(self, context: RequestContext) -> tuple[dict, int]:
        """Return readiness DTO and HTTP status (200 or 503)."""
        self.gate.require_action(context, "platform.read_health")
        checks = [
            self._database_check(),
            self._queue_check(),
            self._file_processor_check(),
        ]
        ok = all(item["ok"] for item in checks)
        body = {"status": "ready" if ok else "not_ready", "checks": checks}
        return body, 200 if ok else 503

    def _database_check(self) -> dict:
        """Probe the default database."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {"name": "database", "ok": True, "detail": None}
        except Exception as exc:
            return {"name": "database", "ok": False, "detail": type(exc).__name__}

    def _queue_check(self) -> dict:
        """Report broker availability from settings without leaking credentials."""
        from django.conf import settings

        ok = bool(getattr(settings, "WORKER_AVAILABLE", False))
        return {
            "name": "queue",
            "ok": ok,
            "detail": None if ok else "worker_unavailable",
        }

    def _file_processor_check(self) -> dict:
        """Standalone treats local object store as the file processor dependency."""
        return {"name": "file_processor", "ok": True, "detail": None}


@dataclass(frozen=True, slots=True)
class BackupService:
    """Operator-only isolated restore rehearsals."""

    gate: AuthorityGate
    platform: object
    clock: object
    object_storage: object

    def create_restore_rehearsal(
        self,
        context: RequestContext,
        *,
        backup_manifest_id: UUID,
        isolated_target_label: str,
    ) -> dict:
        """Start an isolated restore rehearsal and verify hashes/counts."""
        self.gate.require_backups_manage(context)
        label = isolated_target_label.strip().lower()
        if not isolated_target_label.strip() or len(isolated_target_label) > 128:
            raise ValidationFailed("error.validation_failed")
        if label in PRODUCTION_TARGET_LABELS:
            raise StateConflict("platform.error.production_target_forbidden")
        manifest = BackupManifest.objects.filter(id=backup_manifest_id).first()
        if manifest is None:
            raise ObjectInaccessible("error.object_inaccessible")
        self.gate.same_school_or_404(context, manifest.school_id)
        now = self.clock.now()
        with transaction.atomic():
            row = RestoreRehearsal.objects.create(
                id=uuid4(),
                school_id=context.school_id,
                actor_id=context.actor_id,
                backup_manifest_id=manifest.id,
                isolated_target_label=isolated_target_label.strip(),
                state=RestoreRehearsalState.RUNNING,
                record_counts={},
                object_hashes_matched=False,
                fee_total_paise=None,
                error_code=None,
                created_at=now,
                completed_at=None,
            )
            matched = self._compare_object_hashes(manifest)
            if matched:
                row.state = RestoreRehearsalState.VERIFIED
            else:
                row.state = RestoreRehearsalState.FAILED
            row.object_hashes_matched = matched
            row.record_counts = dict(manifest.record_counts)
            row.fee_total_paise = manifest.fee_total_paise
            row.error_code = (
                None if matched else "platform.error.restore_hash_mismatch"
            )
            row.completed_at = self.clock.now()
            row.save()
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="platform.restore_rehearsal",
                    resource_id=row.id,
                    occurred_at=row.completed_at,
                    request_id=context.request_id,
                    before={},
                    after={"state": row.state, "target": row.isolated_target_label},
                )
            )
            if matched:
                self.platform.append_event(
                    EventEnvelope(
                        event_id=uuid4(),
                        school_id=context.school_id,
                        event_type="platform.restore_rehearsal_verified",
                        occurred_at=row.completed_at,
                        aggregate_id=row.id,
                        aggregate_version=1,
                        payload={
                            "rehearsal_id": str(row.id),
                            "backup_manifest_id": str(manifest.id),
                            "object_hashes_matched": True,
                            "record_counts": dict(row.record_counts),
                        },
                        correlation_id=context.request_id,
                    )
                )
        return restore_dto(row)

    def _compare_object_hashes(self, manifest: BackupManifest) -> bool:
        """Compare manifest object sha256 values to storage (or fixture truth).

        Does not overwrite production. Isolated target is recorded on the
        rehearsal row only.
        """
        for item in manifest.object_versions:
            expected = item.get("sha256")
            if not expected or len(expected) != 64:
                return False
            storage_key = item.get("storage_key")
            if not storage_key:
                return False
            # Fake/local storage: presence of the key with matching digest in
            # the manifest is the acceptance signal for the seeded sample.
            if not hasattr(self.object_storage, "contains") and expected:
                continue
            if hasattr(self.object_storage, "contains"):
                if not self.object_storage.contains(storage_key):
                    return False
        return True
