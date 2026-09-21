"""Report cards and the immutable snapshots they produce.

The property this file defends: a report card says what it said. The revision
ids and policy versions a snapshot was built from are written once and never
updated. When the policy changes, the school issues a NEW snapshot and the old
one is marked superseded with a link to its replacement — so a parent holding
last term's card and the office looking at the record agree about what was
issued, and both can see that something newer exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from django.db import transaction

from contracts.errors import ObjectInaccessible, StateConflict, ValidationFailed
from contracts.events import AuditRecord, EventEnvelope
from contracts.exchange import ArtifactAccessDTO, ReportJobStartDTO
from contracts.identity import AuthLevel, RequestContext
from contracts.values import school_date
from shared.fakes.platform import EagerModeNotAsserted

from ..fixture_ids import MALAYALAM_LANGUAGE_WORD
from ..models import JobState, ReportCardJob, ReportSnapshot, SnapshotState, Supersession
from .authority import AuthorityGate
from .blobs import artifact_key, artifact_store, digest_of
from .pdf_render import render_pdf
from .reportcard_layout import report_card_lines, subject_lines
from .wire import report_card_job_to_wire, report_snapshot_to_wire

REPORT_CARD_TASK = "modules.exchange.tasks.process_report_card"

JOB_NOT_READY = "exchange.error.job_not_ready"
NO_PUBLISHED_RESULTS = "exchange.error.no_published_results"
RENDER_FAILED = "exchange.error.render_failed"

#: FilesPort purpose for a generated report artifact.
REPORT_PURPOSE = "report_pdf"
REPORT_MIME = "application/pdf"

#: Snapshot type for a per-pupil report card.
REPORT_CARD = "report_card"


@dataclass(frozen=True, slots=True)
class ReportCardService:
    """Generates report cards and manages their immutable snapshots."""

    gate: AuthorityGate
    files: object
    assessment: object
    platform: object
    clock: object

    def create(
        self,
        context: RequestContext,
        *,
        publication_id: UUID,
        student_ids: list[UUID],
        locale: str,
        template_version: str,
    ) -> dict:
        """Enqueue one job per student and return them all.

        Fanning out per student rather than one job for the batch means a
        pupil whose results are missing fails alone, and the office can see
        exactly which cards are outstanding.
        """
        self.gate.require_staff_action(context, "reportcards.generate")
        now = self.clock.now()
        jobs = []
        for student_id in student_ids:
            self.gate.ensure_student_in_school(context, student_id)
            jobs.append(
                ReportCardJob.objects.create(
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    publication_id=publication_id,
                    student_id=student_id,
                    locale=locale,
                    template_version=template_version,
                    state=JobState.QUEUED,
                    created_at=now,
                    updated_at=now,
                )
            )
        for job in jobs:
            self._enqueue({"job_id": str(job.id)}, job.id)
        return {"jobs": [report_card_job_to_wire(self._reload(job)) for job in jobs]}

    def request_report(
        self,
        context: RequestContext,
        kind: str,
        source_refs: list[dict],
        locale: str,
        template_version: str,
    ) -> ReportJobStartDTO:
        """ExchangePort entry point for another module asking for a report.

        Only ``report_card`` is wired today; other kinds go through the export
        surface. Raises ValidationFailed for anything else rather than
        returning a job that would never finish.
        """
        if kind != REPORT_CARD:
            raise ValidationFailed("exchange.error.unknown_dataset")
        if not source_refs:
            raise ValidationFailed("error.validation_failed")
        first = source_refs[0]
        result = self.create(
            context,
            publication_id=UUID(str(first["publication_id"])),
            student_ids=[UUID(str(ref["student_id"])) for ref in source_refs],
            locale=locale,
            template_version=template_version,
        )
        head = result["jobs"][0]
        state = head["state"] if head["state"] in ("queued", "processing") else "processing"
        return ReportJobStartDTO(job_id=UUID(head["id"]), state=state)

    def get_job(self, context: RequestContext, job_id: UUID) -> dict:
        """Return one report-card job in the actor's school, or 404."""
        self.gate.require_staff_action(context, "reportcards.generate")
        job = ReportCardJob.objects.filter(id=job_id, school_id=context.school_id).first()
        if job is None:
            raise ObjectInaccessible("error.object_inaccessible")
        return report_card_job_to_wire(job)

    def get_snapshot(self, context: RequestContext, report_id: UUID) -> dict:
        """Return one snapshot's metadata after a relationship-gated read check."""
        snapshot = self._load_snapshot(context, report_id)
        self.gate.require_report_read(context, subject_person_id=snapshot.student_id)
        return report_snapshot_to_wire(snapshot)

    def download(self, context: RequestContext, report_id: UUID) -> ArtifactAccessDTO:
        """Return a short-lived authorised read URL for a ready snapshot.

        The relationship is re-resolved at this moment, which is what turns a
        lapsed or never-present guardianship into a 403 rather than a working
        link. A superseded snapshot is still downloadable: the card was really
        issued, and hiding it would rewrite history.
        """
        snapshot = self._load_snapshot(context, report_id)
        self.gate.require_report_read(context, subject_person_id=snapshot.student_id)
        if snapshot.state not in (SnapshotState.READY, SnapshotState.SUPERSEDED):
            raise StateConflict(JOB_NOT_READY)
        file_id = snapshot.artifact_ref.get("file_id")
        if not file_id:
            raise StateConflict(JOB_NOT_READY)
        grant = self.gate.mint_read_grant(context, UUID(str(file_id)))
        url = self.files.issue_read(context, grant)
        return ArtifactAccessDTO(
            authorized_read_url=url.read_url,
            expires_at=url.expires_at,
        )

    def get_artifact(self, context: RequestContext, job_id: UUID) -> ArtifactAccessDTO:
        """ExchangePort entry point: the URL for a finished job's report."""
        job = ReportCardJob.objects.filter(id=job_id, school_id=context.school_id).first()
        if job is None:
            raise ObjectInaccessible("error.object_inaccessible")
        if job.state != JobState.READY or job.report_id is None:
            raise StateConflict(JOB_NOT_READY)
        return self.download(context, job.report_id)

    # --- rendering -----------------------------------------------------------

    def process(self, job_id: UUID) -> dict:
        """Render one report card; a crash marks the card failed instead of stuck.

        The exception is re-raised so the platform job records it too.
        """
        try:
            return self._process(job_id)
        except Exception:
            ReportCardJob.objects.filter(id=job_id).exclude(state=JobState.READY).update(
                state=JobState.FAILED,
                failure_message_key=RENDER_FAILED,
                updated_at=self.clock.now(),
            )
            raise

    def _process(self, job_id: UUID) -> dict:
        """Render one report card and bind its snapshot to the source revisions."""
        job = ReportCardJob.objects.filter(id=job_id).first()
        if job is None:
            raise ObjectInaccessible("error.object_inaccessible")
        context = self._worker_context(job)
        ReportCardJob.objects.filter(id=job.id).update(state=JobState.PROCESSING)
        items = self._published_items(context, job)
        if not items:
            now = self.clock.now()
            ReportCardJob.objects.filter(id=job.id).update(
                state=JobState.FAILED,
                failure_message_key=NO_PUBLISHED_RESULTS,
                updated_at=now,
            )
            return report_card_job_to_wire(self._reload(job))
        snapshot = self._write_snapshot(context, job, items)
        now = self.clock.now()
        with transaction.atomic():
            job.state = JobState.READY
            job.report_id = snapshot.id
            job.version = job.version + 1
            job.updated_at = now
            job.save()
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=job.school_id,
                    actor_id=job.actor_id,
                    action="exchange.report_ready",
                    resource_id=snapshot.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"job_id": str(job.id), "report_id": str(snapshot.id)},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid4(),
                    school_id=job.school_id,
                    event_type="exchange.report_ready",
                    occurred_at=now,
                    aggregate_id=snapshot.id,
                    aggregate_version=snapshot.version,
                    payload={"job_id": str(job.id), "report_id": str(snapshot.id)},
                    correlation_id=context.request_id,
                )
            )
        return report_card_job_to_wire(self._reload(job))

    def supersede(self, context: RequestContext, report_id: UUID, *, reason: str) -> dict:
        """Issue a replacement snapshot and retire the old one.

        The old row's ``source_revision_ids`` and ``policy_versions`` are NOT
        touched. Only ``state`` and ``superseded_by`` move, which is the whole
        difference between a correction and a rewrite.
        """
        self.gate.require_staff_action(context, "reportcards.generate")
        old = self._load_snapshot(context, report_id)
        if old.state != SnapshotState.READY:
            raise StateConflict(JOB_NOT_READY)
        worker = self._context_for_school(old.school_id, context.actor_id, str(old.id))
        items = self._published_for(worker, old.student_id, old.publication_id)
        if not items:
            raise ValidationFailed(NO_PUBLISHED_RESULTS)
        new = self._write_snapshot_row(
            worker,
            school_id=old.school_id,
            student_id=old.student_id,
            publication_id=old.publication_id,
            locale=old.locale,
            template_version=old.template_version,
            items=items,
        )
        now = self.clock.now()
        with transaction.atomic():
            ReportSnapshot.objects.filter(id=old.id).update(
                state=SnapshotState.SUPERSEDED, superseded_by=new.id
            )
            Supersession.objects.create(
                school_id=old.school_id,
                old_report_id=old.id,
                new_report_id=new.id,
                reason=reason,
                created_at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=old.school_id,
                    actor_id=context.actor_id,
                    action="exchange.report_superseded",
                    resource_id=old.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    before={"state": str(SnapshotState.READY)},
                    after={"state": str(SnapshotState.SUPERSEDED), "new": str(new.id)},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid4(),
                    school_id=old.school_id,
                    event_type="exchange.report_superseded",
                    occurred_at=now,
                    aggregate_id=new.id,
                    aggregate_version=new.version,
                    payload={"old_report_id": str(old.id), "new_report_id": str(new.id)},
                    correlation_id=context.request_id,
                )
            )
        return report_snapshot_to_wire(self._reload_snapshot(new.id))

    def _write_snapshot(self, context, job: ReportCardJob, items: list[dict]) -> ReportSnapshot:
        """Render and persist the snapshot for one report-card job."""
        return self._write_snapshot_row(
            context,
            school_id=job.school_id,
            student_id=job.student_id,
            publication_id=job.publication_id,
            locale=job.locale,
            template_version=job.template_version,
            items=items,
        )

    def _write_snapshot_row(
        self,
        context,
        *,
        school_id,
        student_id,
        publication_id,
        locale: str,
        template_version: str,
        items: list[dict],
    ) -> ReportSnapshot:
        """Render the PDF, store it via FilesPort and create the snapshot row.

        ``source_revision_ids`` and ``policy_versions`` are read out of the
        published items HERE, at render time, and are what the row is frozen
        with.
        """
        revision_ids = [
            str(item["result_revision_id"]) for item in items if item.get("result_revision_id")
        ]
        policy_versions = sorted(
            {
                str(item.get("policy_version", ""))
                for item in items
                if item.get("policy_version")
            }
        )
        body = self._render(context, locale, student_id, items, template_version)
        digest = digest_of(body)
        snapshot_id = uuid4()
        key = artifact_key(school_id, snapshot_id)
        artifact_store().put(key, body)
        ref = self.files.store_artifact(context, REPORT_PURPOSE, key, REPORT_MIME, digest)
        artifact_store().put(artifact_key(school_id, ref.file_id), body)
        return ReportSnapshot.objects.create(
            id=snapshot_id,
            school_id=school_id,
            type=REPORT_CARD,
            source_revision_ids=revision_ids,
            policy_versions=policy_versions or [""],
            locale=locale,
            artifact_ref={
                "file_id": str(ref.file_id),
                "version": ref.version,
                "sha256": ref.sha256,
                "mime": ref.mime,
            },
            state=SnapshotState.READY,
            publication_id=publication_id,
            student_id=student_id,
            template_version=template_version,
            created_at=self.clock.now(),
        )

    def _render(
        self, context, locale: str, student_id, items: list[dict], template_version: str
    ) -> bytes:
        """Return the report-card PDF bytes for one pupil.

        Name, admission number, class, subject names, school name and grade
        bands all come from Registry; marks from the published results. A
        Malayalam card prints Malayalam labels (see pdf_render for the font
        limitation).
        """
        registry = self.gate.registry
        student = registry.get_student(context, student_id)
        profile = registry.school_profile(context)
        try:
            facts = registry.get_relationships(
                context, context.actor_id, student_id, school_date(self.clock.now())
            )
            class_label = (
                registry.section_label(context, facts.section_id) if facts.section_id else None
            )
        except ObjectInaccessible:
            class_label = None
        names = {str(key): value for key, value in registry.subject_names(context).items()}
        malayalam = locale == "ml"
        lines = report_card_lines(
            locale=locale,
            school_name=profile.display_name if profile else "",
            student_name=student.display_name,
            admission_no=student.admission_no,
            class_label=class_label,
            subjects=subject_lines(items, names),
            bands=list((profile.settings if profile else {}).get("grading_bands") or []),
            language_word=MALAYALAM_LANGUAGE_WORD if malayalam else "English",
            template_version=template_version,
        )
        heading = "പുരോഗതി കാർഡ്" if malayalam else "Report card"
        return render_pdf(title=heading, lines=lines, locale=locale)

    # --- helpers -------------------------------------------------------------

    def _published_items(self, context, job: ReportCardJob) -> list[dict]:
        """Return the published results backing one job's card."""
        return self._published_for(context, job.student_id, job.publication_id)

    def _published_for(self, context, student_id, publication_id) -> list[dict]:
        """Return published results for a pupil in one publication, or empty."""
        try:
            page = self.assessment.get_published_results(context, student_id, publication_id)
        except ObjectInaccessible:
            return []
        return list(page.get("items", []))

    def _load_snapshot(self, context: RequestContext, report_id: UUID) -> ReportSnapshot:
        """Return a snapshot in the actor's school. Another school's id is 404."""
        row = ReportSnapshot.objects.filter(id=report_id, school_id=context.school_id).first()
        if row is None:
            raise ObjectInaccessible("error.object_inaccessible")
        return row

    @staticmethod
    def _reload(job: ReportCardJob) -> ReportCardJob:
        """Return the job re-read from the database."""
        return ReportCardJob.objects.get(id=job.id)

    @staticmethod
    def _reload_snapshot(snapshot_id: UUID) -> ReportSnapshot:
        """Return the snapshot re-read from the database."""
        return ReportSnapshot.objects.get(id=snapshot_id)

    def _worker_context(self, job: ReportCardJob) -> RequestContext:
        """Return the server-side context the render worker acts under."""
        return self._context_for_school(job.school_id, job.actor_id, str(job.id))

    def _context_for_school(self, school_id, actor_id, tag: str) -> RequestContext:
        """Build a server-derived context from stored ids, never from a payload."""
        return RequestContext(
            actor_id=actor_id,
            school_id=school_id,
            request_id=f"exchange-reportcard-{tag}",
            auth_level=AuthLevel.TWO_FACTOR,
            auth_time=self.clock.now() - timedelta(seconds=1),
        )

    def _enqueue(self, payload: dict, job_id: UUID) -> None:
        """Enqueue the render, falling back to inline when no worker exists."""
        try:
            self.platform.enqueue(REPORT_CARD_TASK, payload=payload)
        except EagerModeNotAsserted:
            self.process(job_id)
