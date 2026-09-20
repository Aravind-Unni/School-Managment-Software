"""Row-to-wire rendering for M03's browser responses.

Kept out of the views so the shape a consumer sees is defined once, next to the
frozen schema it mirrors, rather than assembled inline at each call site where a
field is easy to forget.

Local times render as "HH:MM" school wall-clock strings; instants render as UTC
ISO-8601. Both appear on a session on purpose: the UI shows the bell time a
school recognises, and a consumer compares the instant.
"""

from __future__ import annotations

from ..models import CalendarException, Substitution, TeacherUnavailable, TimetableVersion
from ..services.reads import CalendarDay, SessionView


def _local(value) -> str:
    """Render a school wall-clock time."""
    return value.strftime("%H:%M")


def period_to_wire(period) -> dict[str, object]:
    """Render one period template."""
    return {
        "id": str(period.id),
        "school_id": str(period.school_id),
        "timetable_id": str(period.timetable_id),
        "day_of_week": period.day_of_week,
        "slot_code": period.slot_code,
        "starts_at_local": _local(period.starts_at_local),
        "ends_at_local": _local(period.ends_at_local),
    }


def slot_to_wire(slot) -> dict[str, object]:
    """Render one grid cell, carrying its period's weekday and code."""
    return {
        "id": str(slot.id),
        "school_id": str(slot.school_id),
        "timetable_id": str(slot.timetable_id),
        "period_template_id": str(slot.period_id),
        "day_of_week": slot.period.day_of_week,
        "slot_code": slot.period.slot_code,
        "section_id": str(slot.section_id),
        "subject_id": str(slot.subject_id),
        "teacher_id": str(slot.teacher_id),
        "room_code": slot.room_code,
    }


def timetable_to_wire(version: TimetableVersion) -> dict[str, object]:
    """Render one revision with its whole grid, ordered for a weekly editor."""
    periods = sorted(
        version.periods.all(), key=lambda row: (row.day_of_week, row.starts_at_local)
    )
    slots = sorted(
        version.slots.select_related("period").all(),
        key=lambda row: (
            row.period.day_of_week,
            row.period.starts_at_local,
            str(row.section_id),
        ),
    )
    return {
        **_version_head(version),
        "periods": [period_to_wire(period) for period in periods],
        "slots": [slot_to_wire(slot) for slot in slots],
    }


def timetable_summary_to_wire(version: TimetableVersion) -> dict[str, object]:
    """Render one revision without its grid, for listing."""
    return {
        **_version_head(version),
        "period_count": version.periods.count(),
        "slot_count": version.slots.count(),
    }


def _version_head(version: TimetableVersion) -> dict[str, object]:
    """Render the fields every revision shape shares."""
    return {
        "id": str(version.id),
        "school_id": str(version.school_id),
        "version": version.version,
        "year_id": str(version.year_id),
        "effective_from": version.effective_from.isoformat(),
        "effective_to": version.effective_to.isoformat() if version.effective_to else None,
        "state": version.state,
        "published_at": version.published_at.isoformat() if version.published_at else None,
    }


def conflict_to_wire(conflict) -> dict[str, object]:
    """Render one detected conflict."""
    return {
        "code": conflict.code,
        "message_key": conflict.message_key,
        "blocking": conflict.blocking,
        "slot_ids": [str(slot_id) for slot_id in conflict.slot_ids],
        "teacher_id": str(conflict.teacher_id) if conflict.teacher_id else None,
        "section_id": str(conflict.section_id) if conflict.section_id else None,
        "date": conflict.date.isoformat() if conflict.date else None,
    }


def session_to_wire(session: SessionView) -> dict[str, object]:
    """Render one dated teaching period."""
    dated = session.dated
    return {
        "timetable_session_id": str(dated.timetable_session_id),
        "school_id": str(dated.school_id),
        "section_id": str(dated.section_id),
        "date": dated.date.isoformat(),
        "slot_id": str(dated.slot_id),
        "slot_code": dated.slot_code,
        "subject_id": str(dated.subject_id),
        "assigned_teacher_id": str(dated.teacher_id),
        "substitute_teacher_id": (
            str(session.substitute_teacher_id) if session.substitute_teacher_id else None
        ),
        "starts_at": dated.starts_at.isoformat(),
        "ends_at": dated.ends_at.isoformat(),
        "starts_at_local": _local(dated.starts_at_local),
        "ends_at_local": _local(dated.ends_at_local),
        "cancelled": session.cancelled,
        "cancellation_reason_key": session.cancellation_reason_key,
        "room_code": dated.room_code,
        "timetable_id": str(session.timetable_id),
        "timetable_version": session.timetable_version,
    }


def calendar_day_to_wire(day: CalendarDay) -> dict[str, object]:
    """Render one calendar answer."""
    return {
        "date": day.date.isoformat(),
        "is_school_day": day.is_school_day,
        "reason_key": day.reason_key,
        "kinds": list(day.kinds),
    }


def exception_to_wire(row: CalendarException) -> dict[str, object]:
    """Render one calendar exception."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "date": row.date.isoformat(),
        "kind": row.kind,
        "reason_key": row.reason_key,
        "withdrawn": row.withdrawn,
    }


def unavailability_to_wire(row: TeacherUnavailable) -> dict[str, object]:
    """Render one unavailability interval."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "staff_id": str(row.staff_id),
        "starts_at": row.starts_at.isoformat(),
        "ends_at": row.ends_at.isoformat(),
        "reason_key": row.reason_key,
        "withdrawn": row.withdrawn,
    }


def substitution_to_wire(row: Substitution) -> dict[str, object]:
    """Render one dated substitution."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "date": row.date.isoformat(),
        "slot_id": str(row.slot_id),
        "timetable_session_id": str(row.timetable_session_id),
        "section_id": str(row.section_id),
        "subject_id": str(row.subject_id),
        "original_teacher_id": str(row.original_teacher_id),
        "substitute_teacher_id": str(row.substitute_teacher_id),
        "reason": row.reason,
        "valid_until": row.valid_until.isoformat(),
        "withdrawn": row.withdrawn,
    }
