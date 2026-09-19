"""School configuration and academic reference data.

Authorisation happens here, not in the view, so a worker or an import invoking
the same service gets the same decision as an HTTP caller.

Does not handle: people. That is ``services/people.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import IntegrityError, transaction

from contracts.errors import StateConflict, ValidationFailed
from contracts.identity import RequestContext
from contracts.scope import ScopeFacts

from ..models import AcademicYear, SchoolConfig, Section, Standard, Subject, Term
from .writes import fetch_in_school, require_expected_version, stamp_new, stamp_update

#: The lowest and highest class this school system has. Data, not a branch.
LOWEST_STANDARD = 1
HIGHEST_STANDARD = 12


@dataclass(frozen=True, slots=True)
class ConfigurationService:
    """Reads and writes the school's configuration and calendar.

    ``access`` is the authorisation port and ``clock`` supplies every timestamp;
    neither is read from a global, so a test controls both.
    """

    access: object
    clock: object

    def _authorise(self, context: RequestContext, action: str) -> None:
        """Ask Access whether this school-scoped action is permitted.

        Reference data has no single subject person, so the facts carry only the
        school. A relationship-gated rule would deny every call here.
        """
        self.access.check(context, action, ScopeFacts(resource_school_id=context.school_id))

    # -- school configuration -------------------------------------------------

    def get_school_config(self, context: RequestContext) -> SchoolConfig:
        """Return this deployment's single configuration row.

        Raises ObjectInaccessible when the bootstrap seed has not installed it,
        rather than creating one: an implicit create here would let a misrouted
        request invent configuration for a school that does not exist.
        """
        self._authorise(context, "registry.manage")
        return fetch_config(context.school_id)

    def update_school_config(
        self,
        context: RequestContext,
        *,
        display_name: str,
        board: str,
        default_language: str,
        expected_version: int,
    ) -> SchoolConfig:
        """Replace the configuration's mutable fields under optimistic locking.

        Never creates. The row is installed by the seed; a PUT is an update of
        it or a 404.
        """
        self._authorise(context, "registry.manage")
        with transaction.atomic():
            row = fetch_config(context.school_id, for_update=True)
            require_expected_version(row, expected_version)
            row.display_name = display_name
            row.board = board
            row.default_language = default_language
            stamp_update(row, now=self.clock.now())
            row.save()
        return row

    # -- academic years -------------------------------------------------------

    def create_academic_year(
        self, context: RequestContext, *, name: str, start: date, end: date
    ) -> AcademicYear:
        """Create a year in draft state.

        A year always starts in draft: activating it is a separate transition,
        because activation is what makes enrolment writes legal against it.
        """
        self._authorise(context, "registry.manage")
        require_ordered_dates(start, end)
        now = self.clock.now()
        row = AcademicYear(
            school_id=context.school_id, name=name, start=start, end=end, state="draft"
        )
        stamp_new(row, now=now)
        return save_unique(row, "registry.error.academic_year_exists")

    # -- terms ----------------------------------------------------------------

    def create_term(
        self, context: RequestContext, *, year_id: UUID, name: str, start: date, end: date
    ) -> Term:
        """Create a term inside an existing year.

        The term must fall within its year's inclusive range: a term outside it
        would put attendance and assessment dates in a year that does not
        contain them.
        """
        self._authorise(context, "registry.manage")
        require_ordered_dates(start, end)
        year = fetch_in_school(AcademicYear, school_id=context.school_id, row_id=year_id)
        if start < year.start or end > year.end:
            raise ValidationFailed("registry.error.term_outside_year")
        row = Term(school_id=context.school_id, year=year, name=name, start=start, end=end)
        stamp_new(row, now=self.clock.now())
        return save_unique(row, "registry.error.term_exists")

    # -- standards ------------------------------------------------------------

    def create_standard(self, context: RequestContext, *, number: int) -> Standard:
        """Create a class level.

        Refuses anything outside 1-12. There is no standard 13 to enrol a pupil
        into, so this is a refusal rather than a stored value to clean up later.
        """
        self._authorise(context, "registry.manage")
        if not LOWEST_STANDARD <= number <= HIGHEST_STANDARD:
            raise ValidationFailed("registry.error.standard_out_of_range")
        row = Standard(school_id=context.school_id, number=number)
        stamp_new(row, now=self.clock.now())
        return save_unique(row, "registry.error.standard_exists")

    # -- sections -------------------------------------------------------------

    def create_section(
        self, context: RequestContext, *, year_id: UUID, standard_id: UUID, name: str
    ) -> Section:
        """Create a division of a standard within a year.

        Both references are resolved inside this school. A reference to another
        school's row raises the same 404 as a missing one.
        """
        self._authorise(context, "registry.manage")
        year = fetch_in_school(AcademicYear, school_id=context.school_id, row_id=year_id)
        standard = fetch_in_school(Standard, school_id=context.school_id, row_id=standard_id)
        if standard.archived:
            raise StateConflict("registry.error.reference_archived")
        row = Section(school_id=context.school_id, year=year, standard=standard, name=name)
        stamp_new(row, now=self.clock.now())
        return save_unique(row, "registry.error.section_exists")

    def archive_section(
        self, context: RequestContext, *, section_id: UUID, expected_version: int
    ) -> Section:
        """Mark a section archived, preserving it and everything that cites it.

        Archive is not delete. The row stays readable so historical rosters and
        results keep resolving; it is simply unavailable for NEW links.
        """
        self._authorise(context, "registry.manage")
        with transaction.atomic():
            row = fetch_in_school(
                Section, school_id=context.school_id, row_id=section_id, for_update=True
            )
            require_expected_version(row, expected_version)
            row.archived = True
            stamp_update(row, now=self.clock.now())
            row.save()
        return row

    # -- subjects -------------------------------------------------------------

    def create_subject(
        self, context: RequestContext, *, code: str, display_name: str
    ) -> Subject:
        """Create a school-authored subject.

        This module seeds no curriculum. The school publishes its own subject
        list, because inventing one would put unapproved curriculum into pupil
        records.
        """
        self._authorise(context, "registry.manage")
        row = Subject(school_id=context.school_id, code=code.strip(), display_name=display_name)
        stamp_new(row, now=self.clock.now())
        return save_unique(row, "registry.error.subject_code_exists")


def fetch_config(school_id: UUID, *, for_update: bool = False) -> SchoolConfig:
    """Return the school's configuration row, or raise ObjectInaccessible.

    Separate from the service so the bootstrap and health check can use it
    without holding an authorisation context.
    """
    from contracts.errors import ObjectInaccessible

    queryset = SchoolConfig.objects.filter(school_id=school_id)
    if for_update:
        queryset = queryset.select_for_update()
    row = queryset.first()
    if row is None:
        raise ObjectInaccessible("error.object_inaccessible")
    return row


def require_ordered_dates(start: date, end: date) -> None:
    """Raise ValidationFailed when a range ends before it begins.

    Ranges in this module are inclusive, so a single-day range has start == end
    and is valid.
    """
    if end < start:
        raise ValidationFailed("registry.error.end_before_start")


def save_unique[ModelType](row: ModelType, message_key: str) -> ModelType:
    """Save a row, converting a unique-constraint violation into StateConflict.

    Catching the database's own answer rather than checking first is deliberate:
    a check-then-insert races, and under concurrency two writers would both pass
    the check. The constraint is the authority.

    Does not handle: distinguishing WHICH constraint failed when a table has
    several. Each caller passes the key for its own single unique rule.
    """
    try:
        with transaction.atomic():
            row.save()
    except IntegrityError as exc:
        raise StateConflict(message_key) from exc
    return row
