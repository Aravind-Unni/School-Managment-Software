"""Authority helpers for files reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ActionDenied, ObjectInaccessible
from contracts.identity import RequestContext
from contracts.scope import Relationship, ScopeFacts
from contracts.values import school_date
from shared.fixtures import guards, section_of, teaches

from ..models import File, FilesPolicy


@dataclass(frozen=True, slots=True)
class AuthorityGate:
    """Resolves Access for school-scoped files actions."""

    access: object
    clock: object

    def effective_date(self) -> date:
        """Return Asia/Kolkata civil date from the injected clock."""
        return school_date(self.clock.now())

    def require_action(self, context: RequestContext, action: str) -> None:
        """Authorise a school-scoped staff action."""
        self.access.check(
            context,
            action,
            ScopeFacts(
                resource_school_id=context.school_id,
                effective_date=self.effective_date(),
            ),
        )

    def require_retention(self, context: RequestContext) -> None:
        """Authorise retention.manage with recent 2FA when fixture policy says so."""
        self.require_action(context, "files.retention.manage")
        policy = FilesPolicy.objects.filter(school_id=context.school_id).first()
        if policy is not None and policy.retention_requires_2fa:
            self.access.require_recent_2fa(context, max_age_seconds=300)

    def require_file_read_grant(self, context: RequestContext, file_row: File) -> None:
        """Authorise files.read for a subject-scoped answer sheet, or staff upload.

        Maps relationship denials to ObjectInaccessible so wrong-child grants
        cannot probe existence. Does not handle: Registry — uses shared fixture
        guardian/teacher links when subject_person_id is set.
        """
        if file_row.subject_person_id is None:
            self.require_action(context, "files.upload")
            return
        relationship = self._fixture_relationship(context.actor_id, file_row.subject_person_id)
        try:
            self.access.check(
                context,
                "files.read",
                ScopeFacts(
                    resource_school_id=file_row.school_id,
                    subject_person_id=file_row.subject_person_id,
                    relationship=relationship,
                    effective_date=self.effective_date(),
                ),
            )
        except ActionDenied as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc

    def _fixture_relationship(self, actor_id: UUID, subject_id: UUID) -> Relationship:
        """Derive SELF/GUARDIAN/teacher relationship from synthetic fixtures."""
        if actor_id == subject_id:
            return Relationship.SELF
        if guards(actor_id, subject_id):
            return Relationship.GUARDIAN
        section = section_of(subject_id)
        if section is not None and teaches(actor_id, section):
            return Relationship.ASSIGNED_TEACHER
        return Relationship.NONE

    def load_file(self, context: RequestContext, file_id: UUID) -> File:
        """Load a school-scoped file or raise 404."""
        row = File.objects.filter(id=file_id).first()
        if row is None or row.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return row
