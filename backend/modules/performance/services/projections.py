"""Build and rebuild student projections from Assessment and Attendance ports."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from django.db import transaction

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.values import school_date

from ..models import MetricDefinition, MetricStatus, Projection
from .metrics import attendance_metric_status, simple_mean_percent

WINDOW_TERM = "term"


@dataclass(frozen=True, slots=True)
class ProjectionService:
    """Materialise dashboard metrics for one or all pupils."""

    assessment: object
    attendance: object
    clock: object
    platform: object
    #: RegistryPort; supplies the current term and the list of pupils.
    registry: object = None

    def rebuild_student(
        self,
        context: RequestContext,
        student_id: UUID,
        *,
        window: str = WINDOW_TERM,
        subject_id: UUID | None = None,
    ) -> Projection:
        """Rebuild one student's projection from upstream ports.

        Does not open warnings — caller runs WarningService.evaluate after.
        """
        now = self.clock.now()
        definition = (
            MetricDefinition.objects.filter(school_id=context.school_id, code="overall_mean")
            .order_by("-version")
            .first()
        )
        def_version = definition.version if definition else 1
        denominator = definition.denominator if definition else "100"

        today = school_date(now)
        term = self.registry.current_term(context, today) if self.registry else None
        if term is not None:
            results_page = self.assessment.get_published_results(
                context, student_id, term.id, None
            )
            items = list(results_page.get("items") or [])
        else:
            # Between terms there is no term window to measure.
            items = []
        score_tuples = [
            (str(row["score"]), str(row["max_score"]), str(row["policy_version"]))
            for row in items
            if row.get("score") is not None and row.get("max_score") is not None
        ]
        mean_value, mean_status = simple_mean_percent(score_tuples)

        from_date = term.start if term is not None else today
        to_date = min(today, term.end) if term is not None else today
        attendance = self.attendance.get_summary(
            context, student_id, from_date, to_date, subject_id
        )
        att_value, att_status = attendance_metric_status(
            percentage=attendance.percentage,
            eligible=attendance.eligible,
            unmarked=attendance.unmarked,
            minimum_samples=1,
        )

        metrics = {
            "overall_mean": {
                "code": "overall_mean",
                "value": mean_value,
                "denominator": denominator,
                "definition_version": def_version,
                "status": mean_status,
                "window_label": window,
                "cohort_label": None,
            },
            "attendance_percentage": {
                "code": "attendance_percentage",
                "value": att_value,
                "denominator": "100" if att_value is not None else None,
                "definition_version": 1,
                "status": att_status,
                "window_label": window,
                "cohort_label": None,
            },
            "topic_weakness": {
                "code": "topic_weakness",
                "value": None,
                "denominator": None,
                "definition_version": 1,
                "status": MetricStatus.INSUFFICIENT_DATA,
                "window_label": window,
                "cohort_label": None,
            },
        }
        assessment_updated = None
        if items:
            assessment_updated = max(
                (row.get("updated_at") for row in items if row.get("updated_at")),
                default=None,
            )
            if assessment_updated is None:
                assessment_updated = now.isoformat()
        elif mean_status == "ok":
            assessment_updated = now.isoformat()

        attendance_updated = None
        if attendance.eligible > 0 or attendance.percentage is not None:
            attendance_updated = attendance.updated_at.isoformat()

        source_versions = {
            "assessment_count": len(items),
            "attendance_policy_version": attendance.policy_version,
            "assessment_updated_at": assessment_updated,
            "attendance_updated_at": attendance_updated,
        }

        with transaction.atomic():
            projection, _created = Projection.objects.update_or_create(
                school_id=context.school_id,
                student_id=student_id,
                window=window,
                subject_id=subject_id,
                defaults={
                    "metrics_json": metrics,
                    "source_versions": source_versions,
                    "updated_at": now,
                },
            )
            if projection.id is None:
                projection.id = uuid4()
                projection.save()
        return projection

    def rebuild_school(self, context: RequestContext, student_ids: list[UUID]) -> int:
        """Rebuild projections for every listed pupil. Returns how many succeeded.

        A pupil the caller cannot see (another school, or a relationship the
        upstream port refuses) is skipped, so one record does not abort a
        school-wide nightly rebuild.
        """
        count = 0
        for student_id in student_ids:
            try:
                self.rebuild_student(context, student_id)
            except ObjectInaccessible:
                continue
            count += 1
        return count
