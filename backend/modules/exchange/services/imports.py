"""Validate-then-commit for bulk imports.

The three guarantees this file exists to hold:

  1. a cell that looks like a formula is neutralised, not rejected;
  2. a commit whose ``source_digest`` disagrees with the validated file is
     refused with 409, because the reviewer approved different bytes;
  3. a commit is applied in keyed chunks, so a resumed commit re-runs the whole
     request and still applies every row exactly once.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from django.db import transaction

from contracts.errors import (
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from shared.fakes.platform import EagerModeNotAsserted

from ..adapters import adapter_for
from ..adapters.base import CODE_DUPLICATE_ROW
from ..models import CommitBatch, ImportJob, ImportJobState, ImportRow, ImportRowState
from . import csv_safe
from .authority import AuthorityGate
from .blobs import source_key, source_store
from .wire import import_job_to_wire

VALIDATE_TASK = "modules.exchange.tasks.process_import_validate"
COMMIT_TASK = "modules.exchange.tasks.process_import_commit"

DIGEST_MISMATCH = "exchange.error.digest_mismatch"
JOB_NOT_READY = "exchange.error.job_not_ready"
SOURCE_UNREADABLE = "exchange.error.source_unreadable"

#: Rows per CommitBatch. Small on purpose: the resume test needs more than one
#: batch to prove that a partially applied commit does not re-apply.
DEFAULT_CHUNK_ROWS = 2


@dataclass(frozen=True, slots=True)
class ImportService:
    """Creates, validates and commits bulk import jobs."""

    gate: AuthorityGate
    files: object
    platform: object
    clock: object

    # --- create and validate ------------------------------------------------

    def create(
        self, context: RequestContext, *, dataset: str, file_ref: UUID, mode: str
    ) -> dict:
        """Create a validate-only job for an uploaded file and start validation.

        The digest is taken from FilesPort, never from the client: the whole
        point of the later commit check is that the server decided what the
        file was.

        Raises ValidationFailed for a dataset outside the allowlist or a mode
        other than ``validate``, and ObjectInaccessible for a file this school
        cannot see.
        """
        self.gate.require_staff_action(context, "imports.validate")
        if mode != "validate":
            raise ValidationFailed("error.validation_failed")
        adapter = adapter_for(dataset, "import")
        status = self.files.get_status(context, file_ref)
        now = self.clock.now()
        job = ImportJob.objects.create(
            school_id=context.school_id,
            actor_id=context.actor_id,
            dataset=dataset,
            file_ref=file_ref,
            state=ImportJobState.VALIDATING,
            source_digest=status.sha256,
            validation_version=0,
            template_version=adapter.template_version,
            schema_version=adapter.schema_version,
            mode=mode,
            created_at=now,
            updated_at=now,
        )
        self._enqueue(VALIDATE_TASK, {"job_id": str(job.id)}, lambda: self.validate(job.id))
        job.refresh_from_db()
        return {
            "job_id": str(job.id),
            "template_version": job.template_version,
            "schema_version": job.schema_version,
        }

    def validate(self, job_id: UUID) -> dict:
        """Parse the source file, record rows and errors, and settle the state.

        Duplicate detection lives here rather than in the adapter because only
        the exchange sees the whole file; the adapter declares which columns
        form the key.

        A job with at least one accepted row becomes ``validated`` even when
        other rows failed: partial files are normal, and refusing the whole
        upload would make a single typo cost a day.
        """
        job = ImportJob.objects.filter(id=job_id).first()
        if job is None:
            raise ObjectInaccessible("error.object_inaccessible")
        adapter = adapter_for(job.dataset, "import")
        context = self._worker_context(job)
        body = self._read_source(job)
        prefix = self._prefix(job.school_id)
        _columns, parsed = csv_safe.parse_rows(body, prefix=prefix)

        errors_by_row = self._duplicate_errors(parsed, adapter.key_columns, prefix)
        outcome = adapter.validate_rows(context, parsed)
        for error in outcome["errors"]:
            errors_by_row.setdefault(error["row"], []).append(error)

        now = self.clock.now()
        with transaction.atomic():
            ImportRow.objects.filter(job_id=job.id).delete()
            accepted = 0
            for row in parsed:
                row_errors = errors_by_row.get(row["number"], [])
                if not row_errors:
                    accepted += 1
                ImportRow.objects.create(
                    school_id=job.school_id,
                    job_id=job.id,
                    number=row["number"],
                    external_key=self._external_key(row, adapter.key_columns, prefix),
                    validation_errors=row_errors,
                    state=ImportRowState.ACCEPTED
                    if not row_errors
                    else ImportRowState.REJECTED,
                    payload=row["values"],
                )
            job.accepted_count = accepted
            job.error_count = sum(len(v) for v in errors_by_row.values())
            job.validation_version = job.validation_version + 1
            job.state = (
                ImportJobState.VALIDATED if accepted else ImportJobState.VALIDATION_FAILED
            )
            job.version = job.version + 1
            job.updated_at = now
            job.save()
        return import_job_to_wire(job)

    # --- reads ---------------------------------------------------------------

    def get(self, context: RequestContext, job_id: UUID) -> dict:
        """Return one job in the actor's school, or 404."""
        self.gate.require_staff_action(context, "imports.validate")
        return import_job_to_wire(self._load(context, job_id))

    def list_errors(self, context: RequestContext, job_id: UUID, cursor: str | None) -> dict:
        """Return this job's row errors as a cursor page.

        Raises StateConflict while the job is still validating: an error list
        read mid-parse would be a snapshot of a half-written table.
        """
        self.gate.require_staff_action(context, "imports.validate")
        job = self._load(context, job_id)
        if job.state == ImportJobState.VALIDATING:
            raise StateConflict(JOB_NOT_READY)
        from .pages import page_of_errors

        return page_of_errors(job, cursor)

    def template(self, context: RequestContext, dataset: str) -> dict:
        """Return the column schema for one import dataset."""
        self.gate.require_staff_action(context, "imports.validate")
        adapter = adapter_for(dataset, "import")
        return {
            "dataset": dataset,
            "schema_version": adapter.schema_version,
            "columns": list(adapter.columns),
        }

    # --- commit --------------------------------------------------------------

    def commit(
        self,
        context: RequestContext,
        job_id: UUID,
        *,
        validation_version: int,
        source_digest: str,
        idempotency_key: str,
    ) -> dict:
        """Check the digest and version, then apply the accepted rows.

        Order matters and is part of the contract: version first (409
        ``error.version_conflict`` when the file was re-validated under the
        reviewer), then digest (409 ``exchange.error.digest_mismatch``). A job
        that fails either check keeps its ``validated`` state and is committable
        once the caller re-reads it.
        """
        self.gate.require_commit(context)
        job = self._load(context, job_id)
        if job.validation_version != validation_version:
            raise VersionConflict("error.version_conflict")
        if job.source_digest != source_digest:
            raise StateConflict(DIGEST_MISMATCH)
        # Same Idempotency-Key on an already-applied job is a no-op replay: return
        # the finished shape without re-entering the domain adapter. A different
        # key after apply is a state conflict, not a second apply.
        if job.state == ImportJobState.APPLIED:
            if job.commit_key == idempotency_key:
                return import_job_to_wire(job)
            raise StateConflict(JOB_NOT_READY)
        if job.state not in (ImportJobState.VALIDATED, ImportJobState.COMMITTING):
            raise StateConflict(JOB_NOT_READY)

        now = self.clock.now()
        ImportJob.objects.filter(id=job.id).update(
            state=ImportJobState.COMMITTING,
            commit_key=idempotency_key,
            updated_at=now,
        )
        self._enqueue(
            COMMIT_TASK,
            {"job_id": str(job.id), "idempotency_key": idempotency_key},
            lambda: self.apply_commit(job.id, idempotency_key),
        )
        job.refresh_from_db()
        return import_job_to_wire(job)

    def apply_commit(self, job_id: UUID, idempotency_key: str) -> dict:
        """Apply accepted rows in keyed chunks and emit import_completed.

        Every chunk is guarded by a CommitBatch row keyed
        ``{idempotency_key}:{index}``. A resumed commit walks the same chunks in
        the same order, finds the rows it already wrote, and skips them — so
        ``applied_count`` is identical whether the commit ran once or five
        times.
        """
        job = ImportJob.objects.filter(id=job_id).first()
        if job is None:
            raise ObjectInaccessible("error.object_inaccessible")
        adapter = adapter_for(job.dataset, "import")
        context = self._worker_context(job)
        accepted = list(
            ImportRow.objects.filter(
                job_id=job.id, state__in=[ImportRowState.ACCEPTED, ImportRowState.APPLIED]
            ).order_by("number")
        )
        chunk_size = self._chunk_rows(job.school_id)
        applied_total = 0
        for index in range(0, len(accepted), chunk_size):
            chunk = accepted[index : index + chunk_size]
            batch_key = f"{idempotency_key}:{index // chunk_size}"
            applied_total += self._apply_chunk(job, adapter, context, batch_key, chunk)

        now = self.clock.now()
        with transaction.atomic():
            job.applied_count = applied_total
            job.state = ImportJobState.APPLIED
            job.version = job.version + 1
            job.updated_at = now
            job.save()
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=job.school_id,
                    actor_id=context.actor_id,
                    action="exchange.import_committed",
                    resource_id=job.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"applied_count": applied_total, "error_count": job.error_count},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid4(),
                    school_id=job.school_id,
                    event_type="exchange.import_completed",
                    occurred_at=now,
                    aggregate_id=job.id,
                    aggregate_version=job.version,
                    payload={
                        "job_id": str(job.id),
                        "applied_count": applied_total,
                        "error_count": job.error_count,
                    },
                    correlation_id=context.request_id,
                )
            )
        return import_job_to_wire(job)

    def _apply_chunk(self, job, adapter, context, batch_key: str, chunk: list) -> int:
        """Apply one chunk unless its batch row already exists; return the count."""
        existing = CommitBatch.objects.filter(key=batch_key).first()
        if existing is not None:
            return existing.applied_count
        rows = [
            {"number": row.number, "values": row.payload, "malformed": False} for row in chunk
        ]
        outcome = adapter.apply_rows(context, batch_key, rows)
        applied = int(outcome["applied"])
        with transaction.atomic():
            CommitBatch.objects.create(
                school_id=job.school_id,
                job_id=job.id,
                key=batch_key,
                result=outcome,
                applied_count=applied,
                created_at=self.clock.now(),
            )
            ImportRow.objects.filter(id__in=[row.id for row in chunk]).update(
                state=ImportRowState.APPLIED
            )
        return applied

    # --- helpers -------------------------------------------------------------

    def _load(self, context: RequestContext, job_id: UUID) -> ImportJob:
        """Return a job in the actor's school. Another school's id is 404."""
        job = ImportJob.objects.filter(id=job_id, school_id=context.school_id).first()
        if job is None:
            raise ObjectInaccessible("error.object_inaccessible")
        return job

    def _read_source(self, job: ImportJob) -> str:
        """Return the staged source text for a job, or raise when it is gone."""
        store = source_store()
        key = source_key(job.school_id, job.file_ref)
        if not store.exists(key):
            raise ValidationFailed(SOURCE_UNREADABLE)
        return store.get(key).decode("utf-8")

    def _prefix(self, school_id: UUID) -> str:
        """Return the school's formula neutralisation prefix."""
        policy = self.gate.policy(school_id)
        return policy.formula_neutralization_prefix if policy else csv_safe.DEFAULT_PREFIX

    def _chunk_rows(self, school_id: UUID) -> int:
        """Return how many rows one CommitBatch covers for this school."""
        policy = self.gate.policy(school_id)
        return max(1, policy.commit_chunk_rows if policy else DEFAULT_CHUNK_ROWS)

    @staticmethod
    def _external_key(row: dict, key_columns: tuple[str, ...], prefix: str) -> str:
        """Return the dataset key for one row, with neutralisation stripped.

        Stripped because the prefix is presentation: two rows that differ only
        by a neutralising tab are still the same enrolment.
        """
        return "|".join(
            csv_safe.strip_neutralization(row["values"].get(column, ""), prefix)
            for column in key_columns
        )

    def _duplicate_errors(
        self, rows: list[dict], key_columns: tuple[str, ...], prefix: str
    ) -> dict[int, list[dict]]:
        """Return a duplicate_row error for every repeat of a key after the first.

        The FIRST occurrence is kept, so a reviewer fixing the file deletes the
        later line rather than discovering both were dropped.
        """
        seen: set[str] = set()
        found: dict[int, list[dict]] = {}
        for row in rows:
            if row.get("malformed"):
                continue
            key = self._external_key(row, key_columns, prefix)
            if not key.strip("|"):
                continue
            if key in seen:
                found[row["number"]] = [
                    {
                        "row": row["number"],
                        "field": key_columns[0],
                        "code": CODE_DUPLICATE_ROW,
                    }
                ]
            seen.add(key)
        return found

    def _worker_context(self, job: ImportJob) -> RequestContext:
        """Return the server-side context a worker acts under for this job.

        Built from the school and actor recorded ON THE JOB, never from
        anything the worker payload carried, so a crafted payload cannot steer
        a worker into another tenant or another actor's authority.
        """
        from datetime import timedelta

        from contracts.identity import AuthLevel

        return RequestContext(
            actor_id=job.actor_id,
            school_id=job.school_id,
            request_id=f"exchange-import-{job.id}",
            auth_level=AuthLevel.TWO_FACTOR,
            auth_time=self.clock.now() - timedelta(seconds=1),
        )

    def _enqueue(self, task_path: str, payload: dict, inline) -> None:
        """Enqueue background work, falling back to inline when no worker exists.

        The fallback is NOT a claim of worker coverage: TestPlatformAdapter
        raises EagerModeNotAsserted precisely so a suite cannot pretend, and
        running inline here keeps standalone usable while leaving crash and
        retry behaviour explicitly unproven.
        """
        try:
            self.platform.enqueue(task_path, payload=payload)
        except EagerModeNotAsserted:
            inline()
