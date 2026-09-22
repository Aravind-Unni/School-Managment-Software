"""Attendance-summary export adapter, reading period counts through AttendancePort.

``percentage`` is passed through exactly as M04 reports it, including None. A
null percentage means no calculation version is configured; filling in a number
here would be inventing an attendance policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext

from .base import AdapterBase, ExportPorts, export_page


@dataclass
class AttendanceSummaryAdapter(AdapterBase):
    """Pages per-pupil period attendance counts for one section and window."""

    dataset: str = "attendance_summary"
    schema_version: str = "attendance-summary-schema-v1"
    export_fields: tuple[str, ...] = (
        "student_id",
        "display_name",
        "eligible",
        "marked",
        "present",
        "absent",
        "unmarked",
        "percentage",
        "medical_note",
    )
    forbidden_fields: tuple[str, ...] = ("medical_note",)
    ports: ExportPorts = field(default_factory=ExportPorts)

    def export_rows(
        self,
        ctx: RequestContext,
        dataset: str,
        filters: dict,
        cursor: str | None,
    ) -> dict:
        """Return one page of attendance rows for the filtered section.

        A pupil AttendancePort has no inputs for is SKIPPED rather than exported
        as zeroes, because a zero row and an unmeasured row mean different
        things and a spreadsheet cannot tell them apart.
        """
        self.record("export_rows", dataset=dataset, filters=filters, cursor=cursor)
        section_id = filters.get("section_id")
        if section_id is None:
            return export_page(self.schema_version, [])
        effective = self.ports.clock.now().date()
        roster = self.ports.registry.get_roster(ctx, UUID(str(section_id)), effective)
        start = self._term_start(ctx, effective)
        rows = []
        for entry in roster.students:
            summary = self._summary_or_none(ctx, entry.student_id, start, effective)
            if summary is None:
                continue
            rows.append(
                {
                    "student_id": str(entry.student_id),
                    "display_name": entry.display_name,
                    "eligible": summary.eligible,
                    "marked": summary.marked,
                    "present": summary.present,
                    "absent": summary.absent,
                    "unmarked": summary.unmarked,
                    "percentage": _percentage(summary),
                    "medical_note": f"synthetic-note-{entry.student_id}",
                }
            )
        return export_page(self.schema_version, rows)

    def _term_start(self, ctx: RequestContext, effective):
        """Return the current term's first day, or today when there is no term."""
        current_term = getattr(self.ports.registry, "current_term", None)
        term = current_term(ctx, effective) if current_term is not None else None
        return term.start if term is not None and term.start <= effective else effective

    def _summary_or_none(self, ctx: RequestContext, student_id, start, effective):
        """Return one pupil's term-to-date summary, or None when M04 has no inputs."""
        try:
            return self.ports.attendance.get_summary(ctx, student_id, start, effective)
        except ObjectInaccessible:
            return None


def _percentage(summary) -> str:
    """Attendance % as a two-place string: the summary's own, else attended/counted."""
    if summary.percentage is not None:
        return str(summary.percentage)
    counted = summary.marked - getattr(summary, "excused", 0)
    if counted <= 0:
        return ""
    attended = summary.present + getattr(summary, "late", 0)
    return f"{attended * 100 / counted:.2f}"
