"""In-memory FakeAttendance validating AttendancePort get_summary shapes.

Seedable period summaries. Records calls. Distinguishes incomplete (unmarked)
from configured percentage. Missing students raise ObjectInaccessible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.timetable import AttendanceSummaryDTO

from .failures import FailureInjector


@dataclass
class FakeAttendance:
    """Dictionary-backed AttendancePort for M06 standalone and tests."""

    failures: FailureInjector = field(default_factory=FailureInjector)
    calls: list[tuple[str, tuple, dict]] = field(default_factory=list)
    _summaries: dict[tuple[UUID, UUID | None], AttendanceSummaryDTO] = field(
        default_factory=dict
    )
    _school_by_student: dict[UUID, UUID] = field(default_factory=dict)
    _missing: set[UUID] = field(default_factory=set)

    def seed_summary(self, summary: AttendanceSummaryDTO, *, school_id: UUID) -> None:
        """Install one period summary keyed by student and optional subject."""
        self._school_by_student[summary.student_id] = school_id
        self._summaries[(summary.student_id, summary.subject_id)] = summary
        self._missing.discard(summary.student_id)

    def seed_missing(self, *, student_id: UUID, school_id: UUID) -> None:
        """Mark a pupil as having no attendance inputs (incomplete path)."""
        self._school_by_student[student_id] = school_id
        self._missing.add(student_id)

    def get_summary(
        self,
        context: RequestContext,
        student_id: UUID,
        from_date: date,
        to_date: date,
        subject_id: UUID | None = None,
    ) -> AttendanceSummaryDTO:
        """Return seeded counts or raise when the pupil is unknown/other-school."""
        self.calls.append(("get_summary", (student_id, from_date, to_date, subject_id), {}))
        self.failures.maybe_fail("attendance.get_summary")
        school = self._school_by_student.get(student_id)
        if school is None or school != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        if student_id in self._missing:
            from datetime import UTC, datetime

            return AttendanceSummaryDTO(
                unit="period",
                student_id=student_id,
                from_date=from_date,
                to_date=to_date,
                eligible=10,
                marked=0,
                present=0,
                absent=0,
                late=0,
                excused=0,
                unmarked=10,
                updated_at=datetime(1970, 1, 1, tzinfo=UTC),
                subject_id=subject_id,
                percentage=None,
                policy_version=None,
            )
        key = (student_id, subject_id)
        if key not in self._summaries and subject_id is not None:
            key = (student_id, None)
        if key not in self._summaries:
            raise ObjectInaccessible("error.object_inaccessible")
        return self._summaries[key]
