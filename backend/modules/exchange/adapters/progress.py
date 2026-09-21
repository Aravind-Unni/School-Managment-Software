"""Progress export adapter.

M06 performance is NOT an M13 consumer, so there is no PerformancePort to read.
This adapter synthesises its rows from facts M13 may legitimately see — the
section roster and published results — and labels every row with
``source='synthesised'`` so no reader mistakes it for M06's dashboard.

Does not handle: metric definitions. ``simple_mean_v1`` is M06's baseline
metric name, reproduced here only as a label; this adapter computes no trend,
no cohort distribution and no topic gap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext

from .base import AdapterBase, ExportPorts, export_page

#: The metric label these synthesised rows carry. Data, not a computation.
METRIC_LABEL = "simple_mean_v1"


@dataclass
class ProgressAdapter(AdapterBase):
    """Pages a mean-of-published-marks row per pupil in one section."""

    dataset: str = "progress"
    schema_version: str = "progress-schema-v1"
    export_fields: tuple[str, ...] = (
        "student_id",
        "display_name",
        "metric",
        "mean_marks",
        "result_count",
        "source",
        "teacher_comment",
    )
    forbidden_fields: tuple[str, ...] = ("teacher_comment",)
    ports: ExportPorts = field(default_factory=ExportPorts)

    def export_rows(
        self,
        ctx: RequestContext,
        dataset: str,
        filters: dict,
        cursor: str | None,
    ) -> dict:
        """Return one synthesised progress row per pupil in the section."""
        self.record("export_rows", dataset=dataset, filters=filters, cursor=cursor)
        section_id = filters.get("section_id")
        publication_id = filters.get("publication_id")
        if section_id is None or publication_id is None:
            return export_page(self.schema_version, [])
        effective = self.ports.clock.now().date()
        roster = self.ports.registry.get_roster(ctx, UUID(str(section_id)), effective)
        term = UUID(str(publication_id))
        rows = []
        for entry in roster.students:
            marks = self._marks(ctx, entry.student_id, term)
            mean = "" if not marks else str(sum(marks) / len(marks))
            rows.append(
                {
                    "student_id": str(entry.student_id),
                    "display_name": entry.display_name,
                    "metric": METRIC_LABEL,
                    "mean_marks": mean,
                    "result_count": len(marks),
                    "source": "synthesised",
                    "teacher_comment": f"synthetic-comment-{entry.student_id}",
                }
            )
        return export_page(self.schema_version, rows)

    def _marks(self, ctx: RequestContext, student_id, term_id) -> list[Decimal]:
        """Return this pupil's published marks as Decimals, skipping unparsable."""
        try:
            page = self.ports.assessment.get_published_results(ctx, student_id, term_id)
        except ObjectInaccessible:
            return []
        values: list[Decimal] = []
        for item in page.get("items", []):
            try:
                values.append(Decimal(str(item.get("marks_obtained", ""))))
            except (InvalidOperation, ValueError):
                continue
        return values
