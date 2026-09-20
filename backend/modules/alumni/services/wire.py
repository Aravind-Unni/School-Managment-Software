"""DTO serialisation helpers for alumni API responses."""

from __future__ import annotations

from ..models import AlumniCandidate, AlumniProfile, ContactPreference


def _iso(value) -> str:
    """Format an aware datetime as UTC Zulu."""
    return value.isoformat().replace("+00:00", "Z")


def preference_to_wire(row: ContactPreference) -> dict:
    """Serialise one contact preference."""
    return {
        "person_id": str(row.person_id),
        "purpose": row.purpose,
        "channel": row.channel,
        "allowed": row.allowed,
        "updated_at": _iso(row.updated_at),
    }


def candidate_to_wire(row: AlumniCandidate) -> dict:
    """Serialise an AlumniCandidate row."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "student_id": str(row.student_id),
        "leaving_event_id": str(row.leaving_event_id),
        "outcome": row.outcome,
        "state": row.state,
        "version": row.version,
        "admission_no": row.admission_no,
        "display_name": row.display_name,
        "last_standard": row.last_standard,
        "leaving_year": row.leaving_year,
    }


def profile_to_wire(
    row: AlumniProfile,
    preferences: list[ContactPreference] | None = None,
) -> dict:
    """Serialise an AlumniProfile with preferences.

    Does not emit grade, mark or transcript fields.
    """
    prefs = preferences
    if prefs is None:
        prefs = list(
            ContactPreference.objects.filter(profile_id=row.id).order_by(
                "purpose", "channel", "id"
            )
        )
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "student_id": str(row.student_id),
        "last_standard": row.last_standard,
        "leaving_year": row.leaving_year,
        "outcome": row.outcome,
        "snapshot_version": row.snapshot_version,
        "contact_fields": {
            "email": row.email,
            "phone": row.phone,
            "postal_address": row.postal_address,
        },
        "preferences": [preference_to_wire(p) for p in prefs],
        "version": row.version,
        "display_name": row.display_name,
        "admission_no": row.admission_no,
    }
