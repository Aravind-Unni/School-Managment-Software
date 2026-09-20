"""Typed in-process service ports. Protocols only -- no implementations.

A module depends on these Protocols, never on another module's concrete class.
Standalone mode binds deterministic fakes; integrated mode binds real adapters.
The architecture check enforces that ``backend/modules/<a>`` never imports
``backend/modules/<b>``.

Does not handle: transport. These are in-process calls in a modular monolith;
there is no HTTP between modules.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from .decisions import Decision
from .events import AuditRecord, EventEnvelope
from .evidence import EvidenceRef, ResourceGrant
from .files import (
    ArtifactRef,
    FileDTO,
    FileEvidenceRef,
    ReadUrlDTO,
    UploadSession,
)
from .identity import RequestContext
from .people import RosterDTO, StudentDTO, TeachingAssignment
from .scope import RelationshipFacts, ScopeFacts
from .timetable import (
    AttendanceSummaryDTO,
    CalendarDayDTO,
    PeriodSessionDTO,
    TeachingAuthorityDTO,
)


@runtime_checkable
class ClockPort(Protocol):
    """Source of time. Injected so tests control 'now' explicitly."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC instant."""
        ...


@runtime_checkable
class AccessPort(Protocol):
    """Authorisation decisions. Owned by M01 access.

    Every implementation must default to deny: an action it has no rule for is
    denied, never allowed.

    ``authorize`` is the primitive: it returns a Decision and never raises for a
    policy outcome. ``check`` is a convenience wrapper that turns a denial into
    the right exception. Implementations should define ``authorize`` and derive
    ``check`` from it, so the two can never disagree.
    """

    def authorize(
        self,
        context: RequestContext,
        action: str,
        scope_facts: ScopeFacts,
    ) -> Decision:
        """Return whether ``action`` is permitted, with a reason code.

        Never raises for a policy outcome -- a denial is a return value, because
        callers that need to record *why* (audit, telemetry, conditional UI)
        should not have to catch an exception to learn it.

        ``scope_facts`` is server-resolved. An implementation MUST NOT fetch a
        consumer module's ORM models to fill it in; the host scope resolver has
        already asked Registry.

        Does not handle: freshness of the second factor. Ask
        ``require_recent_2fa`` for that, so an action can require step-up without
        every policy rule restating the window.
        """
        ...

    def require_recent_2fa(
        self,
        context: RequestContext,
        max_age_seconds: int = 300,
    ) -> None:
        """Return None if 2FA was asserted recently enough, else raise.

        Raises StaleAuth (401) carrying AUTH_STEP_UP_REQUIRED. The default window
        is five minutes, which is the proposed profile; a caller may demand a
        shorter one for an especially sensitive write.

        Does not handle: deciding whether the action needs step-up at all. The
        call site decides, because only it knows how sensitive the write is.
        """
        ...

    def check(
        self,
        context: RequestContext,
        action: str,
        facts: ScopeFacts,
    ) -> None:
        """Authorise ``action`` for the context, or raise.

        Raises ActionDenied (403), ObjectInaccessible (404) when the school does
        not match, or StaleAuth (401) when 2FA is too old for this action.
        Returns None on success so that call sites read as assertions.

        Does not handle: row filtering. A list endpoint asks for a predicate via
        ``visible_scope`` instead of checking every row.
        """
        ...

    def is_allowed(
        self,
        context: RequestContext,
        action: str,
        facts: ScopeFacts,
    ) -> bool:
        """Return whether the action is permitted, without raising.

        For building navigation and conditional UI only. Never use this in place
        of ``check`` on a write path.
        """
        ...


@runtime_checkable
class RegistryPort(Protocol):
    """People, sections and relationships. Owned by M02 registry.

    Extended additively for M01. Every method is read-only: no consumer may
    mutate Registry state through this port.
    """

    def get_student(
        self,
        context: RequestContext,
        student_id: UUID,
    ) -> StudentDTO:
        """Return one student.

        Raises ObjectInaccessible (404) for an unknown student AND for one in
        another school, deliberately conflating them so cross-tenant probing
        cannot tell the difference.
        """
        ...

    def get_roster(
        self,
        context: RequestContext,
        section_id: UUID,
        effective_date: date,
        subject_id: UUID | None = None,
    ) -> RosterDTO:
        """Return the pupils in a section on a date.

        When ``subject_id`` is supplied, only pupils enrolled in that subject
        offering on that date are included, and that filtered roster is the one a
        timetable period must use.

        Does not handle: authorising the caller to see the section. Ask Access.
        """
        ...

    def get_relationships(
        self,
        context: RequestContext,
        actor_id: UUID,
        student_id: UUID,
        effective_date: date,
    ) -> RelationshipFacts:
        """Return how an actor relates to a student on a date.

        Dated because a guardianship or a posting can lapse. Returns
        Relationship.NONE rather than raising when unrelated, because 'unrelated'
        is a normal policy input.
        """
        ...

    def get_teaching_assignments(
        self,
        context: RequestContext,
        staff_id: UUID,
        effective_date: date,
    ) -> tuple[TeachingAssignment, ...]:
        """Return the assignments in force for a staff member on a date.

        Returns an empty tuple for an unassigned staff member -- not an error,
        because 'teaches nothing today' is a legitimate state.
        """
        ...

    def relationship_facts(
        self,
        context: RequestContext,
        subject_person_id: UUID,
    ) -> RelationshipFacts:
        """Return how the context's actor relates to the subject person.

        Returns Relationship.NONE rather than raising when unrelated, because
        'unrelated' is a normal policy input, not an error.

        Does not handle: authorising the caller to see the subject. The caller
        folds this into ScopeFacts and asks Access.
        """
        ...


@runtime_checkable
class PlatformPort(Protocol):
    """Audit, outbox and background jobs. Owned by M14 platform.

    Both writes MUST join the caller's open database transaction so that a
    rollback removes them. The test adapter asserts exactly that.
    """

    def record_audit(self, record: AuditRecord) -> None:
        """Append an audit row inside the caller's transaction."""
        ...

    def append_event(self, event: EventEnvelope) -> None:
        """Append an outbox row inside the caller's transaction.

        Does not handle: publishing. A separate relay moves committed rows to
        the broker, so an uncommitted event is never delivered.
        """
        ...

    def enqueue(self, task_path: str, *, payload: dict[str, object]) -> str:
        """Schedule background work and return its job id.

        Does not handle: result retrieval. Jobs report through their own
        aggregates, not through return values.
        """
        ...


@runtime_checkable
class ObjectStoragePort(Protocol):
    """Private object storage. Owned by M12 files."""

    def put(
        self,
        context: RequestContext,
        *,
        storage_key: str,
        content_type: str,
        body: bytes,
    ) -> EvidenceRef:
        """Store bytes under the school's private prefix and return a ref."""
        ...

    def signed_read_url(
        self,
        ref: EvidenceRef,
        *,
        grant: ResourceGrant,
        expires_in_seconds: int,
    ) -> str:
        """Mint a short-lived read URL for an already-authorised grant.

        Assumes the caller has run an Access check and minted ``grant``.
        Implementations must reject an expired grant rather than trusting it.
        """
        ...


@runtime_checkable
class NotificationPort(Protocol):
    """Outbound messages. Owned by M11 communications.

    Local and test profiles must never reach a real SMS or email provider; the
    fake records messages in memory for assertion.
    """

    def send(
        self,
        context: RequestContext,
        *,
        channel: str,
        recipients: Sequence[UUID],
        template_key: str,
        variables: dict[str, object],
    ) -> str:
        """Queue a templated message and return its dispatch id."""
        ...


@runtime_checkable
class TimetablePort(Protocol):
    """Central timetable facts. Owned by M03 timetable.

    Every method is read-only. Callers must not import the timetable ORM.
    """

    def get_sessions(
        self,
        context: RequestContext,
        section_id: UUID,
        effective_date: date,
    ) -> tuple[PeriodSessionDTO, ...]:
        """Return every eligible teaching period for a section on a date.

        Published effective periods only. A holiday returns an empty tuple. A
        cancelled period is returned with ``cancelled`` true.
        """
        ...

    def get_session(
        self,
        context: RequestContext,
        timetable_session_id: UUID,
    ) -> PeriodSessionDTO:
        """Return one dated period by its stable school-scoped identity.

        Raises ObjectInaccessible for an unknown id AND for one in another
        school, conflating the two.
        """
        ...

    def get_calendar(
        self,
        context: RequestContext,
        from_date: date,
        to_date: date,
    ) -> tuple[CalendarDayDTO, ...]:
        """Return whether each date in an inclusive range is a teaching day."""
        ...

    def get_teaching_authority(
        self,
        context: RequestContext,
        timetable_session_id: UUID,
    ) -> TeachingAuthorityDTO:
        """Return who may teach one dated period, and until when.

        Reports a live substitute only while the substitution is still valid.
        ``eligible_for_attendance`` is false for holidays and cancelled periods.
        """
        ...

    def get_sessions_for_staff(
        self,
        context: RequestContext,
        staff_id: UUID,
        effective_date: date,
    ) -> tuple[PeriodSessionDTO, ...]:
        """Return dated periods where ``staff_id`` is assigned or live substitute.

        Attendance uses this to build the teacher's day list. Cancelled and
        holiday-empty days return accordingly. Does not authorise the caller;
        the consumer asks Access and matches the actor to ``staff_id``.
        """
        ...


@runtime_checkable
class AttendancePort(Protocol):
    """Period attendance facts. Owned by M04 attendance."""

    def get_summary(
        self,
        context: RequestContext,
        student_id: UUID,
        from_date: date,
        to_date: date,
        subject_id: UUID | None = None,
    ) -> AttendanceSummaryDTO:
        """Return period-based counts for one pupil in an inclusive date range.

        ``eligible`` includes non-cancelled scheduled periods with no attendance
        row yet. ``percentage`` is None until a calculation version is configured.
        """
        ...


@runtime_checkable
class FilesPort(Protocol):
    """Private file lifecycle. Owned by M12 files.

    Only ``purpose=answer_sheet`` supports quality review and evidence pinning.
    Implementations must not accept browser-supplied ResourceGrant values.
    """

    def begin_upload(
        self,
        context: RequestContext,
        purpose: str,
        client_name: str,
        declared_bytes: int,
        mime: str,
    ) -> UploadSession:
        """Open an upload session for an approved purpose."""
        ...

    def get_status(self, context: RequestContext, file_id: UUID) -> FileDTO:
        """Return file status. Cross-school ids are ObjectInaccessible."""
        ...

    def confirm_quality(
        self,
        context: RequestContext,
        file_id: UUID,
        candidate_version: int,
    ) -> FileDTO:
        """Mark a candidate version as teacher-confirmed canonical."""
        ...

    def pin_evidence(
        self,
        context: RequestContext,
        file_id: UUID,
        canonical_version: int,
        binding_id: UUID,
    ) -> FileEvidenceRef:
        """Pin an immutable confirmed version into a binding."""
        ...

    def issue_read(self, context: RequestContext, grant: ResourceGrant) -> ReadUrlDTO:
        """Mint a short-lived read URL for a server-internal grant."""
        ...

    def store_artifact(
        self,
        context: RequestContext,
        purpose: str,
        content_ref: str,
        mime: str,
        sha256: str,
    ) -> ArtifactRef:
        """Store a service-generated report artifact."""
        ...


@runtime_checkable
class AssessmentPort(Protocol):
    """Published assessment facts. Owned by M05 assessment."""

    def get_published_results(
        self,
        context: RequestContext,
        student_id: UUID,
        term_id: UUID,
        cursor: str | None = None,
    ) -> dict[str, object]:
        """Return published results for one pupil in one term.

        Draft/submitted/approved rows are never returned to student or guardian
        scopes.
        """
        ...

    def get_assignment_summary(
        self,
        context: RequestContext,
        student_id: UUID,
        window_from: datetime,
        window_to: datetime,
    ) -> dict[str, object]:
        """Return assignment counts for one pupil in a closed time window."""
        ...
