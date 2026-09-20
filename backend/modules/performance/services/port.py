"""In-process PerformancePort implementation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contracts.identity import RequestContext
from contracts.performance import DashboardDTO, InterventionPage

from .dashboard import DashboardService
from .interventions import InterventionService


@dataclass(frozen=True, slots=True)
class PerformanceService:
    """Facade matching PerformancePort."""

    dashboard: DashboardService
    interventions: InterventionService

    def get_dashboard(
        self,
        context: RequestContext,
        subject_id: UUID | None,
        scope: str,
        window: str,
        *,
        student_id: UUID | None = None,
        section_id: UUID | None = None,
    ) -> DashboardDTO:
        """Delegate to DashboardService."""
        return self.dashboard.get_dashboard(
            context,
            subject_id=subject_id,
            scope=scope,
            window=window,
            student_id=student_id,
            section_id=section_id,
        )

    def get_interventions(
        self,
        context: RequestContext,
        student_id: UUID,
        cursor: str | None = None,
    ) -> InterventionPage:
        """Delegate to InterventionService."""
        return self.interventions.list_for_student(context, student_id, cursor)
