"""In-memory FakeAssessment validating AssessmentPort response shapes.

Seedable published results and assignment summaries. Records calls. Unused
methods raise AttributeError only if absent from the Protocol — every Protocol
method is implemented. Missing students raise ObjectInaccessible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext

from .failures import FailureInjector


@dataclass
class FakeAssessment:
    """Dictionary-backed AssessmentPort for M06 standalone and tests."""

    failures: FailureInjector = field(default_factory=FailureInjector)
    calls: list[tuple[str, tuple, dict]] = field(default_factory=list)
    _results: dict[tuple[UUID, UUID], list[dict[str, object]]] = field(default_factory=dict)
    _summaries: dict[UUID, dict[str, object]] = field(default_factory=dict)
    _school_by_student: dict[UUID, UUID] = field(default_factory=dict)

    def seed_published_results(
        self,
        *,
        student_id: UUID,
        school_id: UUID,
        term_id: UUID,
        items: list[dict[str, object]],
    ) -> None:
        """Install published ResultDTO-shaped rows for one pupil/term."""
        self._school_by_student[student_id] = school_id
        self._results[(student_id, term_id)] = list(items)

    def seed_assignment_summary(
        self,
        *,
        student_id: UUID,
        school_id: UUID,
        summary: dict[str, object],
    ) -> None:
        """Install an assignment summary for one pupil."""
        self._school_by_student[student_id] = school_id
        self._summaries[student_id] = dict(summary)

    def get_published_results(
        self,
        context: RequestContext,
        student_id: UUID,
        term_id: UUID,
        cursor: str | None = None,
    ) -> dict[str, object]:
        """Return published results page. Cross-school ids are inaccessible."""
        self.calls.append(("get_published_results", (student_id, term_id, cursor), {}))
        self.failures.maybe_fail("assessment.get_published_results")
        school = self._school_by_student.get(student_id)
        if school is None or school != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        items = self._results.get((student_id, term_id), [])
        return {"items": list(items), "next_cursor": None}

    def get_assignment_summary(
        self,
        context: RequestContext,
        student_id: UUID,
        window_from: datetime,
        window_to: datetime,
    ) -> dict[str, object]:
        """Return assignment counts. Missing seed → zeros with updated_at None."""
        self.calls.append(("get_assignment_summary", (student_id, window_from, window_to), {}))
        self.failures.maybe_fail("assessment.get_assignment_summary")
        school = self._school_by_student.get(student_id)
        if school is None or school != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        if student_id in self._summaries:
            return dict(self._summaries[student_id])
        return {
            "assigned": 0,
            "due": 0,
            "submitted": 0,
            "missing": 0,
            "updated_at": None,
        }
