"""Wire shapes for attendance API responses."""

from __future__ import annotations

from typing import Any

from ..models import AttendanceEntry, AttendanceSession


def entry_to_wire(entry: AttendanceEntry) -> dict[str, Any]:
    """Serialise one entry to the frozen DTO shape."""
    return {
        "id": str(entry.id),
        "session_id": str(entry.session_id),
        "enrolment_id": str(entry.enrolment_id),
        "student_id": str(entry.student_id),
        "status": entry.status,
        "note": entry.note or None,
        "version": entry.version,
    }


def session_to_wire(session: AttendanceSession) -> dict[str, Any]:
    """Serialise one session with its entries."""
    entries = [entry_to_wire(e) for e in session.entries.order_by("enrolment_id")]
    return {
        "id": str(session.id),
        "school_id": str(session.school_id),
        "timetable_session_id": str(session.timetable_session_id),
        "date": session.date.isoformat(),
        "section_id": str(session.section_id),
        "slot_id": str(session.slot_id),
        "subject_id": str(session.subject_id),
        "timetable_version": session.timetable_version,
        "roster_version": session.roster_version,
        "roster_snapshot": session.roster_snapshot,
        "state": session.state,
        "version": session.version,
        "entries": entries,
        "submitted_at": session.submitted_at.isoformat() if session.submitted_at else None,
    }
