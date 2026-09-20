"""DTO serialisation helpers for library API responses."""

from __future__ import annotations

from ..models import Copy, CopyAdjustment, Loan, Renewal, Title


def title_to_wire(row: Title) -> dict:
    """Serialise a Title row."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "isbn": row.isbn,
        "name": row.name,
        "author": row.author,
        "language": row.language,
        "version": row.version,
    }


def copy_to_wire(row: Copy) -> dict:
    """Serialise a Copy row."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "title_id": str(row.title_id),
        "accession_no": row.accession_no,
        "state": row.state,
        "version": row.version,
    }


def loan_to_wire(row: Loan) -> dict:
    """Serialise a Loan row."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "copy_id": str(row.copy_id),
        "borrower_person_id": str(row.borrower_person_id),
        "borrower_type": row.borrower_type,
        "issued_at": row.issued_at.isoformat().replace("+00:00", "Z"),
        "due_date": row.due_date.isoformat(),
        "returned_at": (
            row.returned_at.isoformat().replace("+00:00", "Z") if row.returned_at else None
        ),
        "version": row.version,
    }


def renewal_to_wire(row: Renewal) -> dict:
    """Serialise a Renewal row."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "loan_id": str(row.loan_id),
        "old_due": row.old_due.isoformat(),
        "new_due": row.new_due.isoformat(),
        "actor_id": str(row.actor_id),
        "reason": row.reason,
    }


def adjustment_to_wire(row: CopyAdjustment) -> dict:
    """Serialise a CopyAdjustment row."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "copy_id": str(row.copy_id),
        "reason": row.reason,
        "old_state": row.old_state,
        "new_state": row.new_state,
        "actor_id": str(row.actor_id),
    }
