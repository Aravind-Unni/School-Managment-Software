"""Permission codes M13 owns, per contracts/M13/review-decisions.md item 2."""

from __future__ import annotations

PERMISSION_CODES: tuple[str, ...] = (
    "imports.validate",
    "imports.commit",
    "reports.read",
    "reports.export",
    "reportcards.generate",
)
