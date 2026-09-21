"""Dataset exports: enqueue, render, store and hand out a download URL.

Two protections live here. The field allowlist decides which columns may leave
the building, and it is applied when the FILE is written rather than when the
request is parsed — so a column the adapter produced but policy withholds can
never reach the bytes. And the download endpoint re-runs the Access check
instead of trusting the job's existence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from django.db import transaction

from contracts.errors import ObjectInaccessible, StateConflict, ValidationFailed
from contracts.events import AuditRecord
from contracts.exchange import ArtifactAccessDTO
from contracts.identity import RequestContext
from shared.fakes.platform import EagerModeNotAsserted

from ..adapters import ExportPorts, adapter_for
from ..models import ExportJob, JobState
from . import csv_safe
from .authority import AuthorityGate
from .blobs import artifact_key, artifact_store, digest_of
from .pdf_render import render_pdf
from .wire import export_job_to_wire

EXPORT_TASK = "modules.exchange.tasks.process_export"

FORBIDDEN_FIELD = "exchange.error.forbidden_field"
JOB_NOT_READY = "exchange.error.job_not_ready"

#: FilesPort purpose for a generated export artifact.
EXPORT_PURPOSE = "export_artifact"

MIME_BY_FORMAT = {
    "csv": "text/csv",
    "xlsx": "text/csv",
    "pdf": "application/pdf",
}

#: How long a rendered export stays downloadable before it must be regenerated.
ARTIFACT_TTL = timedelta(hours=24)


@dataclass(frozen=True, slots=True)
class ExportService:
    """Creates, renders and serves dataset export jobs."""

    gate: AuthorityGate
    files: object
    platform: object
    clock: object
    ports: ExportPorts

    def create(
        self,
        context: RequestContext,
        *,
        dataset: str,
        filters: dict,
        fields: list[str],
        export_format: str,
        locale: str,
    ) -> dict:
        """Enqueue one export job after narrowing the requested fields.

        Raises ValidationFailed carrying ``exchange.error.forbidden_field``
        when NOTHING the caller asked for is exportable: silently returning an
        empty file would look like "there is no data" rather than "you may not
        see these columns".
        """
        self.gate.require_staff_action(context, "reports.export")
        adapter = adapter_for(dataset, "export", ports=self.ports)
        granted = adapter.granted_fields(fields)
        if not granted:
            raise ValidationFailed(FORBIDDEN_FIELD)
        now = self.clock.now()
        job = ExportJob.objects.create(
            school_id=context.school_id,
            actor_id=context.actor_id,
            dataset=dataset,
            filters=dict(filters),
            requested_fields=list(fields),
            field_grants=granted,
            format=export_format,
            locale=locale,
            state=JobState.QUEUED,
            expires_at=now + ARTIFACT_TTL,
            created_at=now,
            updated_at=now,
        )
        self._enqueue({"job_id": str(job.id)}, lambda: self.process(job.id))
        job.refresh_from_db()
        return export_job_to_wire(job)

    def get(self, context: RequestContext, job_id: UUID) -> dict:
        """Return one export job in the actor's school, or 404."""
        self.gate.require_staff_action(context, "reports.export")
        return export_job_to_wire(self._load(context, job_id))

    def process(self, job_id: UUID) -> dict:
        """Render the artifact, store it through FilesPort and mark the job ready.

        The renderer only ever sees ``field_grants``, so the withheld columns
        are absent from the bytes rather than blanked — a blanked column still
        tells the reader the field exists.
        """
        job = ExportJob.objects.filter(id=job_id).first()
        if job is None:
            raise ObjectInaccessible("error.object_inaccessible")
        adapter = adapter_for(job.dataset, "export", ports=self.ports)
        context = self._worker_context(job)
        ExportJob.objects.filter(id=job.id).update(state=JobState.PROCESSING)

        page = adapter.export_rows(context, job.dataset, dict(job.filters), None)
        columns = list(job.field_grants)
        body = self._render(job, columns, list(page["rows"]))
        digest = digest_of(body)
        key = artifact_key(job.school_id, job.id)
        artifact_store().put(key, body)
        ref = self.files.store_artifact(
            context,
            EXPORT_PURPOSE,
            key,
            MIME_BY_FORMAT[job.format],
            digest,
        )
        now = self.clock.now()
        with transaction.atomic():
            job.state = JobState.READY
            job.artifact_file_id = ref.file_id
            job.artifact_sha256 = digest
            job.version = job.version + 1
            job.updated_at = now
            job.save()
            artifact_store().put(artifact_key(job.school_id, ref.file_id), body)
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=job.school_id,
                    actor_id=job.actor_id,
                    action="exchange.export_ready",
                    resource_id=job.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"artifact_ref": str(ref.file_id), "fields": columns},
                )
            )
        return export_job_to_wire(job)

    def download(self, context: RequestContext, job_id: UUID) -> ArtifactAccessDTO:
        """Return a short-lived authorised read URL for a finished export.

        Access is re-checked here, not inherited from the request that created
        the job: the two can be hours apart, and a permission can be withdrawn
        in between.
        """
        self.gate.require_staff_action(context, "reports.export")
        job = self._load(context, job_id)
        if job.state != JobState.READY or job.artifact_file_id is None:
            raise StateConflict(JOB_NOT_READY)
        grant = self.gate.mint_read_grant(context, job.artifact_file_id)
        url = self.files.issue_read(context, grant)
        return ArtifactAccessDTO(
            authorized_read_url=url.read_url,
            expires_at=url.expires_at,
        )

    def _render(self, job: ExportJob, columns: list[str], rows: list[dict]) -> bytes:
        """Return the artifact bytes for this job's format.

        ``xlsx`` is served as CSV bytes under a documented limitation: no
        spreadsheet writer is in the lockfile and adding a dependency is a
        reviewed change, not one to make in passing. The formula neutralisation
        is identical either way, which is the property that matters.
        """
        if job.format == "pdf":
            lines = [", ".join(str(row.get(column, "")) for column in columns) for row in rows]
            return render_pdf(
                title=f"{job.dataset} ({job.locale})",
                lines=[", ".join(columns), *lines],
                locale=job.locale,
            )
        prefix = self._prefix(job.school_id)
        return csv_safe.write_rows(columns, rows, prefix=prefix).encode("utf-8")

    def _prefix(self, school_id: UUID) -> str:
        """Return the school's formula neutralisation prefix."""
        policy = self.gate.policy(school_id)
        return policy.formula_neutralization_prefix if policy else csv_safe.DEFAULT_PREFIX

    def _load(self, context: RequestContext, job_id: UUID) -> ExportJob:
        """Return an export job in the actor's school. Another school's id is 404."""
        job = ExportJob.objects.filter(id=job_id, school_id=context.school_id).first()
        if job is None:
            raise ObjectInaccessible("error.object_inaccessible")
        return job

    def _worker_context(self, job: ExportJob) -> RequestContext:
        """Return the server-side context the render worker acts under."""
        from contracts.identity import AuthLevel

        return RequestContext(
            actor_id=job.actor_id,
            school_id=job.school_id,
            request_id=f"exchange-export-{job.id}",
            auth_level=AuthLevel.TWO_FACTOR,
            auth_time=self.clock.now() - timedelta(seconds=1),
        )

    def _enqueue(self, payload: dict, inline) -> None:
        """Enqueue the render, falling back to inline when no worker exists.

        Not a claim of worker coverage: see ImportService._enqueue for why the
        adapter refuses to pretend.
        """
        try:
            self.platform.enqueue(EXPORT_TASK, payload=payload)
        except EagerModeNotAsserted:
            inline()
