"""Dashboard and scoped export assembly from projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from contracts.errors import ActionDenied, ObjectInaccessible
from contracts.identity import RequestContext
from contracts.performance import (
    DashboardDTO,
    MetricDTO,
    SourceFreshnessDTO,
    WarningSummaryDTO,
)

from ..models import (
    Observation,
    Projection,
    Visibility,
    WarningState,
)
from ..models import (
    Warning as WarningRow,
)
from .authority import AuthorityGate


@dataclass(frozen=True, slots=True)
class DashboardService:
    """Assemble dashboard and guardian-safe exports."""

    gate: AuthorityGate
    clock: object

    def get_dashboard(
        self,
        context: RequestContext,
        *,
        subject_id: UUID | None,
        scope: str,
        window: str,
        student_id: UUID | None = None,
        section_id: UUID | None = None,
    ) -> DashboardDTO:
        """Return metrics and open warnings for the resolved student scope.

        Cohort/section aggregates hide peer identities — only counts via metrics.
        ``section_id`` is accepted for future cohort bars; baseline uses student.
        """
        _ = section_id
        if student_id is None:
            raise ObjectInaccessible("error.object_inaccessible")
        self.gate.require_student_read(context, student_id)
        projection = Projection.objects.filter(
            school_id=context.school_id,
            student_id=student_id,
            window=window,
            subject_id=subject_id,
        ).first()
        if projection is None and subject_id is not None:
            projection = Projection.objects.filter(
                school_id=context.school_id,
                student_id=student_id,
                window=window,
                subject_id=None,
            ).first()
        now = self.clock.now()
        if projection is None:
            return DashboardDTO(
                metrics=(),
                warnings=(),
                source_freshness=SourceFreshnessDTO(None, None),
                updated_at=now,
            )
        metrics = tuple(
            MetricDTO(
                code=row["code"],
                definition_version=int(row["definition_version"]),
                status=row["status"],
                value=row.get("value"),
                denominator=row.get("denominator"),
                window_label=row.get("window_label") or window,
                cohort_label=row.get("cohort_label"),
            )
            for row in projection.metrics_json.values()
        )
        warning_qs = WarningRow.objects.filter(
            school_id=context.school_id,
            student_id=student_id,
            state__in=[WarningState.OPEN, WarningState.ACKNOWLEDGED],
        )
        # Guardians see warnings only when performance.read already passed.
        warnings = tuple(
            WarningSummaryDTO(
                id=w.id,
                rule_id=w.rule_id,
                state=w.state,
                explanation_key=w.explanation_key,
                student_id=w.student_id,
            )
            for w in warning_qs
        )
        src = projection.source_versions
        freshness = SourceFreshnessDTO(
            assessment_updated_at=_parse_dt(src.get("assessment_updated_at")),
            attendance_updated_at=_parse_dt(src.get("attendance_updated_at")),
        )
        _ = scope
        return DashboardDTO(
            metrics=metrics,
            warnings=warnings,
            source_freshness=freshness,
            updated_at=projection.updated_at,
        )

    def export_summary(
        self,
        context: RequestContext,
        *,
        student_id: UUID,
        window: str,
    ) -> dict[str, object]:
        """Guardian/staff academic export omitting restricted observations."""
        dashboard = self.get_dashboard(
            context,
            subject_id=None,
            scope="student",
            window=window,
            student_id=student_id,
        )
        guardian = self.gate.is_guardian_or_self(context, student_id)
        obs_qs = Observation.objects.filter(school_id=context.school_id, student_id=student_id)
        if guardian:
            obs_qs = obs_qs.exclude(visibility=Visibility.RESTRICTED).exclude(
                visibility=Visibility.STAFF
            )
        else:
            can_sensitive = False
            try:
                self.gate.require_staff_action(context, "observations.read_sensitive")
                can_sensitive = True
            except ActionDenied:
                can_sensitive = False
            if not can_sensitive:
                obs_qs = obs_qs.exclude(visibility=Visibility.RESTRICTED)
        observations = [
            {
                "id": str(o.id),
                "kind": o.kind,
                "body": o.body,
                "visibility": o.visibility,
            }
            for o in obs_qs
        ]
        return {
            "metrics": [
                {
                    "code": m.code,
                    "value": m.value,
                    "denominator": m.denominator,
                    "definition_version": m.definition_version,
                    "status": m.status,
                    "window_label": m.window_label,
                    "cohort_label": m.cohort_label,
                }
                for m in dashboard.metrics
            ],
            "warnings": [
                {
                    "id": str(w.id),
                    "rule_id": str(w.rule_id),
                    "state": w.state,
                    "explanation_key": w.explanation_key,
                    "student_id": str(w.student_id) if w.student_id else None,
                }
                for w in dashboard.warnings
            ],
            "observations": observations,
            "updated_at": dashboard.updated_at.isoformat(),
        }


def _parse_dt(value: object) -> datetime | None:
    """Parse an ISO timestamp from projection source_versions, or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)
