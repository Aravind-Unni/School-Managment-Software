"""In-process AttendancePort implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.identity import RequestContext
from contracts.timetable import AttendanceSummaryDTO

from .summary import SummaryService


@dataclass(frozen=True, slots=True)
class AttendanceService:
    """The attendance facts another module consumes in-process."""

    summary: SummaryService

    def get_summary(
        self,
        context: RequestContext,
        student_id: UUID,
        from_date: date,
        to_date: date,
        subject_id: UUID | None = None,
    ) -> AttendanceSummaryDTO:
        """Delegate to SummaryService."""
        return self.summary.get_summary(
            context, student_id, from_date, to_date, subject_id=subject_id
        )
