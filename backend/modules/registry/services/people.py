"""Students, guardians and staff, and the duplicate-review gate on admission.

The admission path is the one worth reading closely. Detection is pure and lives
in ``duplicates.py``; this file supplies the rows, issues the token, and rechecks
everything INSIDE the write transaction under a lock. Rechecking outside it would
let a candidate change between the reviewer's decision and the insert.

Does not handle: guardian links, enrolment or teaching assignments. Those are
steps 2 and 3.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from django.db import transaction

from contracts.errors import StateConflict, ValidationFailed
from contracts.identity import RequestContext
from contracts.people import StudentDTO, StudentStatus
from contracts.scope import ScopeFacts

from ..models import DuplicateReview, ExternalIdentity, Guardian, StaffProfile, Student
from . import duplicates
from .configuration import save_unique
from .writes import fetch_in_school, require_expected_version, stamp_new, stamp_update

#: How long a reviewer's duplicate decision stays usable. A reviewed technical
#: parameter, not a school policy: it bounds how stale the picture they judged
#: may be. Data, so changing it is a one-line reviewable diff.
DUPLICATE_REVIEW_LIFETIME = timedelta(minutes=15)


@dataclass(frozen=True, slots=True)
class PeopleService:
    """Reads and writes the school's people records."""

    access: object
    clock: object

    def _authorise(self, context: RequestContext, action: str) -> None:
        """Ask Access whether this school-scoped action is permitted."""
        self.access.check(context, action, ScopeFacts(resource_school_id=context.school_id))

    # -- duplicate review -----------------------------------------------------

    def open_duplicate_review(
        self,
        context: RequestContext,
        *,
        admission_no: str,
        display_name: str,
        date_of_birth: date | None,
    ) -> DuplicateReview:
        """Show the candidates a proposed admission may duplicate, and pin them.

        The token records the actor, the school, a digest of the canonical input
        and the exact versions shown. It asserts nothing: admitting the student
        still rechecks all of it.
        """
        self._authorise(context, "students.update")
        proposed = canonical_input(admission_no, display_name, date_of_birth)
        found = self._candidates_for(context.school_id, proposed)
        now = self.clock.now()
        row = DuplicateReview(
            school_id=context.school_id,
            actor_id=context.actor_id,
            input_digest=duplicates.input_digest(proposed),
            candidates=[candidate.to_wire() for candidate in found],
            created_at=now,
            expires_at=now + DUPLICATE_REVIEW_LIFETIME,
        )
        row.save()
        return row

    def _candidates_for(
        self, school_id: UUID, proposed: duplicates.CandidateInput
    ) -> tuple[duplicates.Candidate, ...]:
        """Return the stored students a proposed admission may duplicate.

        Narrows in the database to the two things that can match -- the exact
        admission number, or the exact name with a non-null birth date -- so the
        pure detector is never handed the whole school.
        """
        from django.db.models import Q

        criteria = Q(admission_no=proposed.admission_no)
        if proposed.date_of_birth is not None:
            criteria |= Q(
                display_name=proposed.display_name, date_of_birth=proposed.date_of_birth
            )
        rows = tuple(
            duplicates.ExistingStudent(
                student_id=row.id,
                version=row.version,
                admission_no=row.admission_no,
                display_name=row.display_name,
                date_of_birth=row.date_of_birth,
            )
            for row in Student.objects.filter(criteria, school_id=school_id).order_by("id")
        )
        return duplicates.find_candidates(proposed, rows)

    # -- students -------------------------------------------------------------

    def admit_student(
        self,
        context: RequestContext,
        *,
        admission_no: str,
        display_name: str,
        date_of_birth: date | None,
        preferred_language: str,
        external_ids: tuple[dict[str, str], ...],
        acknowledgement: dict | None,
    ) -> StudentDTO:
        """Admit a student, refusing or requiring review when it may be a duplicate.

        Returns the frozen minimal StudentDTO, which carries no version. The
        caller reads the versioned browser record with a follow-up GET; the two
        shapes are deliberately different, so extending the browser record can
        never alter what other modules receive.
        """
        self._authorise(context, "students.update")
        proposed = canonical_input(admission_no, display_name, date_of_birth)
        now = self.clock.now()

        with transaction.atomic():
            found = self._candidates_for(context.school_id, proposed)
            if duplicates.has_admission_collision(found):
                # Never overridable. The number is the school's own key, and an
                # acknowledgement cannot make two records share it.
                raise StateConflict("registry.error.admission_number_exists")
            if found:
                self._require_valid_acknowledgement(
                    context, proposed, found, acknowledgement, now
                )

            row = Student(
                school_id=context.school_id,
                admission_no=proposed.admission_no,
                display_name=display_name.strip(),
                date_of_birth=date_of_birth,
                preferred_language=preferred_language,
                status=StudentStatus.ACTIVE,
            )
            stamp_new(row, now=now)
            save_unique(row, "registry.error.admission_number_exists")
            self._store_external_ids(
                context, kind="student", person_id=row.id, values=external_ids
            )

        return StudentDTO(
            id=row.id,
            school_id=row.school_id,
            admission_no=row.admission_no,
            display_name=row.display_name,
            status=StudentStatus(row.status),
        )

    def _require_valid_acknowledgement(
        self,
        context: RequestContext,
        proposed: duplicates.CandidateInput,
        found: tuple[duplicates.Candidate, ...],
        acknowledgement: dict | None,
        now,
    ) -> None:
        """Raise unless a human acknowledged exactly this picture, just now.

        Four separate ways to be stale, each a real failure mode rather than a
        theoretical one: no token at all, a token issued for different input, a
        token past its window, and a token whose candidates have since moved.
        A null reason is not a decision -- it is a click-through -- so it is
        refused with the same conflict.
        """
        if acknowledgement is None:
            raise StateConflict("registry.error.duplicate_review_required")
        if not acknowledgement.get("distinct_person_reason"):
            raise StateConflict("registry.error.duplicate_review_required")

        review = DuplicateReview.objects.filter(
            school_id=context.school_id,
            id=acknowledgement["review_id"],
            actor_id=context.actor_id,
        ).first()
        if review is None or review.version != acknowledgement["review_version"]:
            raise StateConflict("registry.error.duplicate_review_stale")
        if review.input_digest != duplicates.input_digest(proposed):
            raise StateConflict("registry.error.duplicate_review_stale")
        if review.expires_at <= now:
            raise StateConflict("registry.error.duplicate_review_stale")

        shown = tuple(
            duplicates.Candidate(
                student_id=UUID(entry["student_id"]),
                version=entry["version"],
                reason=entry["reason"],
            )
            for entry in review.candidates
        )
        if not duplicates.candidates_are_unchanged(shown, found):
            raise StateConflict("registry.error.duplicate_review_stale")

    def get_student(self, context: RequestContext, student_id: UUID) -> Student:
        """Return one student's versioned browser record."""
        self._authorise(context, "students.read")
        return fetch_in_school(Student, school_id=context.school_id, row_id=student_id)

    def update_student(
        self,
        context: RequestContext,
        *,
        student_id: UUID,
        display_name: str,
        date_of_birth: date | None,
        preferred_language: str,
        expected_version: int,
    ) -> Student:
        """Amend a student's profile under optimistic locking."""
        self._authorise(context, "students.update")
        with transaction.atomic():
            row = fetch_in_school(
                Student, school_id=context.school_id, row_id=student_id, for_update=True
            )
            require_expected_version(row, expected_version)
            row.display_name = display_name.strip()
            row.date_of_birth = date_of_birth
            row.preferred_language = preferred_language
            stamp_update(row, now=self.clock.now())
            row.save()
        return row

    def list_students(
        self, context: RequestContext, *, after_id: UUID | None, page_size: int
    ) -> tuple[tuple[Student, ...], bool]:
        """Return one keyset page of students and whether more remain.

        Ordered by id, which is stable and does not shift when a name changes
        under a reader's cursor. Filtering happens before pagination, so a page
        cannot leak a count of rows the actor may not see.
        """
        self._authorise(context, "students.read")
        queryset = Student.objects.filter(school_id=context.school_id).order_by("id")
        if after_id is not None:
            queryset = queryset.filter(id__gt=after_id)
        rows = tuple(queryset[: page_size + 1])
        return rows[:page_size], len(rows) > page_size

    # -- guardians and staff --------------------------------------------------

    def create_guardian(
        self,
        context: RequestContext,
        *,
        display_name: str,
        email: str | None,
        phone: str | None,
        external_ids: tuple[dict[str, str], ...],
    ) -> Guardian:
        """Create a guardian record.

        Creating one grants no access to anything. What a guardian may see comes
        from a dated GuardianLink, which arrives in step 2.
        """
        self._authorise(context, "guardians.manage")
        row = Guardian(
            school_id=context.school_id,
            display_name=display_name.strip(),
            email=email,
            phone=phone,
        )
        stamp_new(row, now=self.clock.now())
        row.save()
        self._store_external_ids(
            context, kind="guardian", person_id=row.id, values=external_ids
        )
        return row

    def create_staff(
        self,
        context: RequestContext,
        *,
        display_name: str,
        external_ids: tuple[dict[str, str], ...],
    ) -> StaffProfile:
        """Create a staff person record, independent of any login account."""
        self._authorise(context, "staff.assign")
        row = StaffProfile(school_id=context.school_id, display_name=display_name.strip())
        stamp_new(row, now=self.clock.now())
        row.save()
        self._store_external_ids(context, kind="staff", person_id=row.id, values=external_ids)
        return row

    def external_ids_for(self, person_id: UUID) -> list[dict[str, str]]:
        """Return a person's external identities in a stable order."""
        return [
            {"source": row.source, "value": row.value}
            for row in ExternalIdentity.objects.filter(person_id=person_id).order_by(
                "source", "value"
            )
        ]

    def _store_external_ids(
        self,
        context: RequestContext,
        *,
        kind: str,
        person_id: UUID,
        values: tuple[dict[str, str], ...],
    ) -> None:
        """Record a person's external identities, refusing a repeated mapping.

        A source that maps twice to different people inside one request is a
        caller error, not something to resolve by picking one.
        """
        now = self.clock.now()
        seen: set[tuple[str, str]] = set()
        for entry in values:
            key = (entry["source"], entry["value"])
            if key in seen:
                raise ValidationFailed("registry.error.external_id_repeated")
            seen.add(key)
            row = ExternalIdentity(
                school_id=context.school_id,
                kind=kind,
                person_id=person_id,
                source=entry["source"],
                value=entry["value"],
                created_at=now,
            )
            save_unique(row, "registry.error.external_id_exists")


def canonical_input(
    admission_no: str, display_name: str, date_of_birth: date | None
) -> duplicates.CandidateInput:
    """Return the normalised form every duplicate comparison is made against.

    One function, so the digest stored in a token and the comparison made when
    it is redeemed can never drift apart.
    """
    return duplicates.CandidateInput(
        admission_no=duplicates.normalise_admission_no(admission_no),
        display_name=duplicates.normalise_display_name(display_name),
        date_of_birth=date_of_birth,
    )
