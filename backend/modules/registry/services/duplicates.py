"""Duplicate detection for student admission. Pure: no IO, no clock, no globals.

The reviewed rule, in one place so it can be read without chasing call sites:

  * An exact admission-number collision is a HARD refusal. No token, reason or
    acknowledgement overrides it, because the number is the school's own key.
  * An exact display name plus a non-null, equal birth date raises a CANDIDATE.
    A human decides. This module never merges two records into one.
  * A null birth date matches nothing, including another null. Absence of a
    birth date is not evidence that two children are the same child.

Does not handle: fetching candidates, issuing tokens or expiry. The service
layer does that and passes the rows in.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from uuid import UUID

#: Reason codes, frozen in contracts/M02/schemas/dtos.schema.json.
REASON_ADMISSION_NO = "admission_no"
REASON_NAME_AND_BIRTH_DATE = "name_and_birth_date"


@dataclass(frozen=True, slots=True)
class ExistingStudent:
    """The fields of a stored student that duplicate detection compares."""

    student_id: UUID
    version: int
    admission_no: str
    display_name: str
    date_of_birth: date | None


@dataclass(frozen=True, slots=True)
class CandidateInput:
    """The canonical, already-normalised admission being checked."""

    admission_no: str
    display_name: str
    date_of_birth: date | None


@dataclass(frozen=True, slots=True)
class Candidate:
    """One student the admission may duplicate, with why and at which version."""

    student_id: UUID
    version: int
    reason: str

    def to_wire(self) -> dict[str, object]:
        """Serialise to the contracted DuplicateCandidate shape."""
        return {
            "student_id": str(self.student_id),
            "version": self.version,
            "reason": self.reason,
        }


def normalise_admission_no(raw: str) -> str:
    """Return the canonical form of an admission number.

    Trims outer whitespace only. Case is preserved and significant: the school
    may legitimately issue both "2026/ab01" and "2026/AB01", and folding them
    together would refuse a real child's admission.

    Does not handle: inner whitespace or punctuation, which are part of the
    number as the school writes it.
    """
    return raw.strip()


def normalise_display_name(raw: str) -> str:
    """Return the canonical form of a name for comparison.

    Collapses runs of whitespace and trims, so "Arjun  Pillai" and "Arjun
    Pillai" compare equal. Case is preserved, matching the admission rule.

    Does not handle: transliteration between scripts. "അര്‍ജുന്‍" and "Arjun" are
    different strings here and will not raise a candidate, which is why a human
    reviews rather than this function deciding.
    """
    return " ".join(raw.split())


def find_candidates(
    proposed: CandidateInput, existing: tuple[ExistingStudent, ...]
) -> tuple[Candidate, ...]:
    """Return every stored student the proposed admission may duplicate.

    Admission-number matches come first, because the caller refuses on those
    without consulting the rest. Ordering is otherwise the caller's row order,
    which is stable by id.

    Assumes ``proposed`` and ``existing`` are already normalised by the two
    functions above. Does not handle: authorisation, or hiding candidates the
    actor may not read -- the caller filters before showing identities.
    """
    admission_matches = tuple(
        Candidate(row.student_id, row.version, REASON_ADMISSION_NO)
        for row in existing
        if row.admission_no == proposed.admission_no
    )
    name_matches = tuple(
        Candidate(row.student_id, row.version, REASON_NAME_AND_BIRTH_DATE)
        for row in existing
        if proposed.date_of_birth is not None
        and row.date_of_birth == proposed.date_of_birth
        and row.display_name == proposed.display_name
    )
    return admission_matches + name_matches


def has_admission_collision(candidates: tuple[Candidate, ...]) -> bool:
    """Return whether any candidate is an exact admission-number collision.

    A true result means refuse outright: this is the one duplicate outcome an
    acknowledgement cannot clear.
    """
    return any(candidate.reason == REASON_ADMISSION_NO for candidate in candidates)


def input_digest(proposed: CandidateInput) -> str:
    """Return a stable digest of the canonical input a review was issued for.

    Binding the token to this digest is what stops a reviewer acknowledging one
    admission and the acknowledgement being replayed for a different child.

    The separator cannot appear in a date or be produced by normalisation, so
    two different inputs cannot collide by concatenation.
    """
    birth = proposed.date_of_birth.isoformat() if proposed.date_of_birth else ""
    material = "\x1f".join((proposed.admission_no, proposed.display_name, birth))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def candidates_are_unchanged(
    shown: tuple[Candidate, ...], current: tuple[Candidate, ...]
) -> bool:
    """Return whether the candidates now match exactly what the reviewer saw.

    Compares ids AND versions as a set: a candidate that changed, vanished or
    appeared since the review means the human judged a different picture, so the
    token is stale. Order is not significant; membership and version are.
    """

    def key(items: tuple[Candidate, ...]) -> set[tuple[UUID, int, str]]:
        return {(item.student_id, item.version, item.reason) for item in items}

    return key(shown) == key(current)
