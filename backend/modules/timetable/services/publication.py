"""Validating a draft and making it the school's effective schedule.

Two properties this module exists to protect:

  * **Publication is forward-only.** A revision may not take effect on or before
    the currently effective one's start date. A past register was taken against
    the grid that was effective then, and rewriting it retrospectively would make
    historical attendance unreconcilable.
  * **Nothing is deleted.** Publishing CLOSES the previous revision's range and
    marks it superseded. It stays readable and listable forever.

Does not handle: editing. A published revision is immutable; correcting it is a
new draft.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from django.db import transaction

from contracts.errors import FieldError, StateConflict
from contracts.identity import RequestContext

from ..conflicts import (
    Conflict,
    PeriodRow,
    SlotRow,
    UnavailabilityRow,
    detect_conflicts,
    has_blocking,
)
from ..models import TeacherUnavailable, TimetableVersion
from .journal import append_event, record_audit
from .writes import fetch_in_school, require_expected_version, stamp_update

#: The reviewed step-up window for publication, in seconds. The same number the
#: fixture policy holds; stated as data in both places rather than as a branch.
PUBLISH_TWO_FACTOR_MAX_AGE_SECONDS = 300


@dataclass(frozen=True, slots=True)
class PublishResult:
    """What publishing produced, ready to render."""

    version: TimetableVersion
    superseded_timetable_id: UUID | None


@dataclass(frozen=True, slots=True)
class PublicationService:
    """Validates and publishes revisions. Holds ports, never global state."""

    scope: object
    access: object
    registry: object
    platform: object
    clock: object

    def validate(
        self, context: RequestContext, *, timetable_id: UUID
    ) -> tuple[TimetableVersion, tuple[Conflict, ...]]:
        """Return a revision and every conflict in it.

        Read-only. An empty list is an observation, not a reservation: publish
        re-runs the same detection inside its own transaction, because the world
        can move between the two calls.
        """
        self.scope.require_school_action(context, "timetable.edit")
        version = fetch_in_school(
            TimetableVersion, school_id=context.school_id, row_id=timetable_id
        )
        return version, self._detect(context, version)

    def publish(
        self, context: RequestContext, *, timetable_id: UUID, expected_version: int
    ) -> PublishResult:
        """Make a draft the school's effective schedule.

        Refuses a stale ``expected_version`` BEFORE it looks at state, so two
        academic heads publishing the same draft get a version conflict -- which
        tells the loser that someone else moved first -- rather than a state
        conflict, which would suggest they had the wrong draft.
        """
        self.scope.require_school_action(context, "timetable.publish")
        # Belt and braces with real Access: the fixture policy already carries the
        # window, but a real policy that forgot it must not silently drop step-up
        # from the single most consequential write in this module.
        self.access.require_recent_2fa(
            context, max_age_seconds=PUBLISH_TWO_FACTOR_MAX_AGE_SECONDS
        )

        now = self.clock.now()
        with transaction.atomic():
            version = fetch_in_school(
                TimetableVersion,
                school_id=context.school_id,
                row_id=timetable_id,
                for_update=True,
            )
            require_expected_version(version, expected_version)
            if version.state != "draft":
                raise StateConflict("timetable.error.already_published")

            conflicts = self._detect(context, version)
            if has_blocking(conflicts):
                raise StateConflict(
                    "timetable.error.conflicts_present",
                    field_errors=tuple(
                        FieldError("conflicts", conflict.message_key)
                        for conflict in conflicts
                        if conflict.blocking
                    ),
                )

            superseded = self._close_previous(context, version, now=now)
            version.state = "published"
            version.published_at = now
            stamp_update(version, now=now)
            version.save()

            record_audit(
                self.platform,
                context,
                action="timetable.publish",
                resource_id=version.id,
                before={"state": "draft"},
                after={
                    "state": "published",
                    "effective_from": version.effective_from.isoformat(),
                    "superseded_timetable_id": str(superseded.id) if superseded else None,
                },
                now=now,
            )
            append_event(
                self.platform,
                context,
                event_type="timetable.published",
                aggregate_id=version.id,
                aggregate_version=version.version,
                payload={
                    "timetable_id": str(version.id),
                    "effective_from": version.effective_from.isoformat(),
                    "effective_to": (
                        version.effective_to.isoformat() if version.effective_to else None
                    ),
                    "version": version.version,
                    "year_id": str(version.year_id),
                    "superseded_timetable_id": str(superseded.id) if superseded else None,
                },
                now=now,
            )
        return PublishResult(
            version=version, superseded_timetable_id=superseded.id if superseded else None
        )

    # --- internals ----------------------------------------------------------

    def _close_previous(
        self, context: RequestContext, version: TimetableVersion, *, now
    ) -> TimetableVersion | None:
        """Close the currently effective revision's range, or refuse the publish.

        Returns the revision that was superseded, or None when this is the
        school's first. Raises when the new revision would take effect on or
        before the current one's start date.
        """
        current = (
            TimetableVersion.objects.filter(
                school_id=context.school_id, state__in=("published", "superseded")
            )
            .exclude(id=version.id)
            .order_by("-effective_from", "-published_at", "-id")
            .select_for_update()
            .first()
        )
        if current is None:
            return None
        if version.effective_from <= current.effective_from:
            raise StateConflict("timetable.error.effective_from_not_after_effective")

        closes_on = version.effective_from - timedelta(days=1)
        if current.effective_to is None or current.effective_to > closes_on:
            current.effective_to = closes_on
        current.state = "superseded"
        stamp_update(current, now=now)
        current.save()
        return current

    def _detect(
        self, context: RequestContext, version: TimetableVersion
    ) -> tuple[Conflict, ...]:
        """Gather everything the pure detector needs and run it.

        Registry is asked once per distinct teacher and once per distinct section,
        on the revision's first effective date, rather than once per slot.
        """
        periods = tuple(
            PeriodRow(
                period_id=period.id,
                day_of_week=period.day_of_week,
                slot_code=period.slot_code,
                starts_at_local=period.starts_at_local,
                ends_at_local=period.ends_at_local,
            )
            for period in version.periods.all()
        )
        slots = tuple(
            SlotRow(
                slot_id=slot.id,
                period_id=slot.period_id,
                section_id=slot.section_id,
                subject_id=slot.subject_id,
                teacher_id=slot.teacher_id,
            )
            for slot in version.slots.all()
        )
        unavailability = tuple(
            UnavailabilityRow(
                staff_id=row.staff_id, starts_at=row.starts_at, ends_at=row.ends_at
            )
            for row in TeacherUnavailable.objects.filter(
                school_id=context.school_id, withdrawn=False
            )
        )
        on = version.effective_from
        assignments = {
            teacher_id: self.registry.get_teaching_assignments(context, teacher_id, on)
            for teacher_id in sorted({slot.teacher_id for slot in slots}, key=str)
        }
        known_sections = frozenset(
            section_id
            for section_id in sorted({slot.section_id for slot in slots}, key=str)
            if self._section_exists(context, section_id, on)
        )
        return detect_conflicts(
            periods=periods,
            slots=slots,
            unavailability=unavailability,
            assignments=assignments,
            known_sections=known_sections,
            effective_from=version.effective_from,
            effective_to=version.effective_to,
        )

    def _section_exists(self, context: RequestContext, section_id: UUID, on) -> bool:
        """Return whether Registry reports a section for this school on a date.

        Asked through ``get_roster`` because the frozen port has no
        ``get_section``; gap 1 in contracts/M03/ports.md.
        """
        from contracts.errors import ObjectInaccessible

        try:
            self.registry.get_roster(context, section_id, on)
        except ObjectInaccessible:
            return False
        return True
