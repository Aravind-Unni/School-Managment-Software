"""The draft weekly editor: create, read, list and replace a grid.

A create always produces a DRAFT. Publication is a separate, separately
authorised transition, so a create can never skip it.

A replace takes the whole week in one transaction rather than a cell at a time:
that is how the editor is used, and it means a grid is either taken or refused,
never left half-applied with a teacher double-booked in the gap.

Does not handle: publication or conflict detection. Those are ``publication.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import transaction

from contracts.errors import (
    FieldError,
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
)
from contracts.identity import RequestContext

from ..models import PeriodTemplate, Slot, TimetableVersion
from ..sessions import local_windows_overlap
from .journal import record_audit
from .writes import fetch_in_school, require_expected_version, stamp_new, stamp_update


@dataclass(frozen=True, slots=True)
class DraftService:
    """Builds and amends draft revisions. Holds ports, never global state."""

    scope: object
    registry: object
    platform: object
    clock: object

    def create(
        self,
        context: RequestContext,
        *,
        year_id: UUID,
        effective_from: date,
        effective_to: date | None,
        periods: list[dict],
        slots: list[dict],
    ) -> TimetableVersion:
        """Create a draft revision with its whole grid.

        The grid is validated before anything is written, so a refused create
        leaves no partial revision behind.
        """
        self.scope.require_school_action(context, "timetable.edit")
        require_ordered_range(effective_from, effective_to)
        validate_grid(periods, slots)
        self._require_known_sections(context, slots, effective_from)

        now = self.clock.now()
        with transaction.atomic():
            version = TimetableVersion(
                school_id=context.school_id,
                year_id=year_id,
                effective_from=effective_from,
                effective_to=effective_to,
                state="draft",
            )
            stamp_new(version, now=now)
            version.save()
            self._write_grid(version, periods, slots, now=now)
            record_audit(
                self.platform,
                context,
                action="timetable.create_draft",
                resource_id=version.id,
                before={},
                after=_summary(version, periods, slots),
                now=now,
            )
        return self.get(context, timetable_id=version.id)

    def replace(
        self,
        context: RequestContext,
        *,
        timetable_id: UUID,
        effective_from: date,
        effective_to: date | None,
        periods: list[dict],
        slots: list[dict],
        expected_version: int,
    ) -> TimetableVersion:
        """Replace a draft's grid under optimistic locking.

        Refuses a published or superseded revision: correcting one is a NEW
        revision, so the grid a past register was taken against still exists.
        """
        self.scope.require_school_action(context, "timetable.edit")
        require_ordered_range(effective_from, effective_to)
        validate_grid(periods, slots)
        self._require_known_sections(context, slots, effective_from)

        now = self.clock.now()
        with transaction.atomic():
            version = fetch_in_school(
                TimetableVersion,
                school_id=context.school_id,
                row_id=timetable_id,
                for_update=True,
            )
            # Version before state, matching publish: a writer holding a stale
            # version is told that someone moved first, which is the actionable
            # message, rather than being told about a state they did not cause.
            require_expected_version(version, expected_version)
            require_draft(version)
            before = _summary(version, [], [])
            version.slots.all().delete()
            version.periods.all().delete()
            version.effective_from = effective_from
            version.effective_to = effective_to
            stamp_update(version, now=now)
            version.save()
            self._write_grid(version, periods, slots, now=now)
            record_audit(
                self.platform,
                context,
                action="timetable.replace_draft",
                resource_id=version.id,
                before=before,
                after=_summary(version, periods, slots),
                now=now,
            )
        return self.get(context, timetable_id=timetable_id)

    def get(self, context: RequestContext, *, timetable_id: UUID) -> TimetableVersion:
        """Return one revision with its grid, or 404.

        A revision in another school raises the same error as an absent one, so a
        probe cannot tell them apart.
        """
        self.scope.require_school_action(context, "timetable.read")
        version = fetch_in_school(
            TimetableVersion, school_id=context.school_id, row_id=timetable_id
        )
        return version

    def listing(
        self,
        context: RequestContext,
        *,
        year_id: UUID | None,
        state: str | None,
    ):
        """Return every revision matching the filters, newest range first.

        Historical revisions are listed deliberately: reconciliation needs the
        revision a past register was recorded against, so nothing is hidden once
        it has been superseded.
        """
        self.scope.require_school_action(context, "timetable.read")
        queryset = TimetableVersion.objects.filter(school_id=context.school_id)
        if year_id is not None:
            queryset = queryset.filter(year_id=year_id)
        if state is not None:
            queryset = queryset.filter(state=state)
        return queryset.order_by("-effective_from", "-created_at", "id")

    # --- internals ----------------------------------------------------------

    def _write_grid(
        self, version: TimetableVersion, periods: list[dict], slots: list[dict], *, now
    ) -> None:
        """Insert the period templates and slots of a validated grid."""
        created: dict[tuple[int, str], PeriodTemplate] = {}
        for row in periods:
            period = PeriodTemplate(
                school_id=version.school_id,
                timetable=version,
                day_of_week=row["day_of_week"],
                slot_code=row["slot_code"],
                starts_at_local=row["starts_at_local"],
                ends_at_local=row["ends_at_local"],
            )
            stamp_new(period, now=now)
            period.save()
            created[(period.day_of_week, period.slot_code)] = period

        for row in slots:
            period = created[(row["day_of_week"], row["slot_code"])]
            slot = Slot(
                school_id=version.school_id,
                timetable=version,
                period=period,
                section_id=row["section_id"],
                subject_id=row["subject_id"],
                teacher_id=row["teacher_id"],
                room_code=row.get("room_code"),
            )
            stamp_new(slot, now=now)
            slot.save()

    def _require_known_sections(
        self, context: RequestContext, slots: list[dict], on: date
    ) -> None:
        """Refuse a grid naming a section Registry does not report for this school.

        Confirmed through ``get_roster`` because the frozen RegistryPort has no
        ``get_section`` to ask; an ObjectInaccessible from it is read as "unknown
        section". That conflates an unknown section with one the actor may not see,
        and it fetches a pupil list to answer a yes/no question. Recorded as gap 1
        in contracts/M03/ports.md rather than papered over.
        """
        for section_id in sorted({row["section_id"] for row in slots}, key=str):
            try:
                self.registry.get_roster(context, section_id, on)
            except ObjectInaccessible as exc:
                raise ValidationFailed(
                    "timetable.error.unknown_section",
                    field_errors=(
                        FieldError("slots.section_id", "timetable.error.unknown_section"),
                    ),
                ) from exc


def require_draft(version: TimetableVersion) -> None:
    """Raise StateConflict unless the revision is still editable."""
    if version.state != "draft":
        raise StateConflict("timetable.error.not_draft")


def require_ordered_range(effective_from: date, effective_to: date | None) -> None:
    """Raise unless a revision's range runs forwards."""
    if effective_to is not None and effective_to < effective_from:
        raise ValidationFailed(
            "timetable.error.effective_to_before_from",
            field_errors=(
                FieldError("effective_to", "timetable.error.effective_to_before_from"),
            ),
        )


def validate_grid(periods: list[dict], slots: list[dict]) -> None:
    """Refuse a malformed grid before any of it is written.

    Four rules, in the order a reader of the error would want them:
      * a period must end strictly after it starts;
      * two periods on one weekday may not share a slot code;
      * two periods on one weekday may not overlap, compared half-open, so an
        abutting pair is an ordinary school day and not a clash;
      * a slot must name a period the grid defines, and one section may hold only
        one slot per period.

    Pure: no database, no clock. The same rules are re-checked by the conflict
    detector before publication, because a revision stored before a rule existed
    must still be caught.
    """
    seen_periods: set[tuple[int, str]] = set()
    by_day: dict[int, list[dict]] = {}
    for row in periods:
        if row["ends_at_local"] <= row["starts_at_local"]:
            raise ValidationFailed(
                "timetable.error.period_end_not_after_start",
                field_errors=(
                    FieldError(
                        "periods.ends_at_local", "timetable.error.period_end_not_after_start"
                    ),
                ),
            )
        key = (row["day_of_week"], row["slot_code"])
        if key in seen_periods:
            raise ValidationFailed(
                "timetable.error.duplicate_period",
                field_errors=(
                    FieldError("periods.slot_code", "timetable.error.duplicate_period"),
                ),
            )
        seen_periods.add(key)
        by_day.setdefault(row["day_of_week"], []).append(row)

    for day_rows in by_day.values():
        ordered = sorted(day_rows, key=lambda row: (row["starts_at_local"], row["slot_code"]))
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                if local_windows_overlap(
                    (first["starts_at_local"], first["ends_at_local"]),
                    (second["starts_at_local"], second["ends_at_local"]),
                ):
                    raise ValidationFailed(
                        "timetable.error.period_overlap",
                        field_errors=(FieldError("periods", "timetable.error.period_overlap"),),
                    )

    seen_slots: set[tuple[int, str, UUID]] = set()
    for row in slots:
        key = (row["day_of_week"], row["slot_code"])
        if key not in seen_periods:
            raise ValidationFailed(
                "timetable.error.unknown_slot_code",
                field_errors=(
                    FieldError("slots.slot_code", "timetable.error.unknown_slot_code"),
                ),
            )
        placed = (row["day_of_week"], row["slot_code"], row["section_id"])
        if placed in seen_slots:
            raise ValidationFailed(
                "timetable.error.duplicate_slot",
                field_errors=(
                    FieldError("slots.section_id", "timetable.error.duplicate_slot"),
                ),
            )
        seen_slots.add(placed)


def _summary(version: TimetableVersion, periods: list[dict], slots: list[dict]) -> dict:
    """Return the redacted audit summary of a revision.

    Counts and states, never the grid itself: an audit row that copied every cell
    would duplicate the table it describes.
    """
    return {
        "state": version.state,
        "effective_from": version.effective_from.isoformat(),
        "effective_to": version.effective_to.isoformat() if version.effective_to else None,
        "period_count": len(periods),
        "slot_count": len(slots),
    }
