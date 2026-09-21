"""Subject-summary export adapter, reading published results through AssessmentPort.

Published rows only: draft, submitted and approved marks never reach an export,
which is M05's rule and not one this module may relax. No grade letter is
derived; the school's grade policy has not been supplied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext

from .base import AdapterBase, ExportPorts, export_page


@dataclass
class SubjectSummaryAdapter(AdapterBase):
    """Pages per-pupil published result rows for one publication."""

    dataset: str = "subject_summary"
    schema_version: str = "subject-summary-schema-v1"
    export_fields: tuple[str, ...] = (
        "student_id",
        "display_name",
        "subject_id",
        "marks_obtained",
        "result_revision_id",
        "internal_remark",
    )
    forbidden_fields: tuple[str, ...] = ("internal_remark",)
    ports: ExportPorts = field(default_factory=ExportPorts)

    def export_rows(
        self,
        ctx: RequestContext,
        dataset: str,
        filters: dict,
        cursor: str | None,
    ) -> dict:
        """Return published result rows for the filtered section and publication."""
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
            for item in self._published(ctx, entry.student_id, term):
                rows.append(
                    {
                        "student_id": str(entry.student_id),
                        "display_name": entry.display_name,
                        "subject_id": str(item.get("subject_id", "")),
                        "marks_obtained": item.get("marks_obtained", ""),
                        "result_revision_id": str(item.get("result_revision_id", "")),
                        "internal_remark": f"synthetic-remark-{entry.student_id}",
                    }
                )
        return export_page(self.schema_version, rows)

    def _published(self, ctx: RequestContext, student_id, term_id) -> list[dict]:
        """Return one pupil's published items, or an empty list when unknown."""
        try:
            page = self.ports.assessment.get_published_results(ctx, student_id, term_id)
        except ObjectInaccessible:
            return []
        return list(page.get("items", []))
