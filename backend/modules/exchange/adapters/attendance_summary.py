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
        rows = []
        for entry in roster.students:
            summary = self._summary_or_none(ctx, entry.student_id, effective)
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
                    "percentage": "" if summary.percentage is None else summary.percentage,
                    "medical_note": f"synthetic-note-{entry.student_id}",
                }
            )
        return export_page(self.schema_version, rows)

    def _summary_or_none(self, ctx: RequestContext, student_id, effective):
        """Return one pupil's summary, or None when M04 has no inputs for them."""
        try:
            return self.ports.attendance.get_summary(ctx, student_id, effective, effective)
        except ObjectInaccessible:
            return None
