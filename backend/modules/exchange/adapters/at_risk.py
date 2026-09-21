"""At-risk export adapter.

Like ``progress``, this synthesises rather than reading M06, which is not an
M13 consumer. The important restraint: it does NOT decide who is at risk. No
attendance threshold and no mark boundary has been supplied by a school, so
inventing one here would be inventing a domain fact.

Instead every row carries the raw counts and ``risk_status='not_assessed'``
with ``threshold_policy_version=''``. A reader can sort the sheet; the system
does not label a child.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext

from .base import AdapterBase, ExportPorts, export_page

#: What the adapter reports in place of a verdict it has no policy to give.
RISK_STATUS_UNASSESSED = "not_assessed"


@dataclass
class AtRiskAdapter(AdapterBase):
    """Pages raw attendance and result counts with no risk verdict attached."""

    dataset: str = "at_risk"
    schema_version: str = "at-risk-schema-v1"
    export_fields: tuple[str, ...] = (
        "student_id",
        "display_name",
        "unmarked_periods",
        "absent_periods",
        "published_results",
        "risk_status",
        "threshold_policy_version",
        "counsellor_note",
    )
    forbidden_fields: tuple[str, ...] = ("counsellor_note",)
    ports: ExportPorts = field(default_factory=ExportPorts)

    def export_rows(
        self,
        ctx: RequestContext,
        dataset: str,
        filters: dict,
        cursor: str | None,
    ) -> dict:
        """Return one unlabelled counts row per pupil in the filtered section."""
        self.record("export_rows", dataset=dataset, filters=filters, cursor=cursor)
        section_id = filters.get("section_id")
        if section_id is None:
            return export_page(self.schema_version, [])
        effective = self.ports.clock.now().date()
        roster = self.ports.registry.get_roster(ctx, UUID(str(section_id)), effective)
        publication_id = filters.get("publication_id")
        rows = []
        for entry in roster.students:
            summary = self._summary(ctx, entry.student_id, effective)
            rows.append(
                {
                    "student_id": str(entry.student_id),
                    "display_name": entry.display_name,
                    "unmarked_periods": "" if summary is None else summary.unmarked,
                    "absent_periods": "" if summary is None else summary.absent,
                    "published_results": self._result_count(
                        ctx, entry.student_id, publication_id
                    ),
                    "risk_status": RISK_STATUS_UNASSESSED,
                    "threshold_policy_version": "",
                    "counsellor_note": f"synthetic-note-{entry.student_id}",
                }
            )
        return export_page(self.schema_version, rows)

    def _summary(self, ctx: RequestContext, student_id, effective):
        """Return one pupil's attendance summary, or None when unmeasured."""
        try:
            return self.ports.attendance.get_summary(ctx, student_id, effective, effective)
        except ObjectInaccessible:
            return None

    def _result_count(self, ctx: RequestContext, student_id, publication_id) -> int | str:
        """Return how many published results a pupil has, or empty when unknown."""
        if publication_id is None:
            return ""
        try:
            page = self.ports.assessment.get_published_results(
                ctx, student_id, UUID(str(publication_id))
            )
        except ObjectInaccessible:
            return ""
        return len(page.get("items", []))
