"""Performance dashboard and intervention DTOs. Owned by M06.

Frozen under school-contracts-v7. No Django imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MetricDTO:
    """One labelled metric with optional value and status."""

    code: str
    definition_version: int
    status: str
    value: str | None = None
    denominator: str | None = None
    window_label: str = "term"
    cohort_label: str | None = None


@dataclass(frozen=True, slots=True)
class WarningSummaryDTO:
    """Warning row shown on a dashboard."""

    id: UUID
    rule_id: UUID
    state: str
    explanation_key: str
    student_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class SourceFreshnessDTO:
    """When upstream assessment/attendance facts last updated."""

    assessment_updated_at: datetime | None
    attendance_updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class DashboardDTO:
    """Dashboard payload for Performance.get_dashboard."""

    metrics: tuple[MetricDTO, ...]
    warnings: tuple[WarningSummaryDTO, ...]
    source_freshness: SourceFreshnessDTO
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class InterventionDTO:
    """One intervention visible to the caller."""

    id: UUID
    school_id: UUID
    student_id: UUID
    goal: str
    owner_id: UUID
    review_date: date
    state: str
    visibility: str
    version: int
    resource_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class InterventionPage:
    """Cursor page of interventions."""

    items: tuple[InterventionDTO, ...]
    next_cursor: str | None = None
