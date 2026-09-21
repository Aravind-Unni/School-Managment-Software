"""Class-roster export adapter, reading section membership through RegistryPort.

The row dictionaries deliberately CONTAIN ``guardian_contact`` and
``date_of_birth`` even though neither is exportable. Producing them and then
withholding them is what makes the allowlist testable: an adapter that simply
never built the value would pass the same assertion while proving nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from contracts.identity import RequestContext

from .base import AdapterBase, ExportPorts, export_page


@dataclass
class ClassRosterAdapter(AdapterBase):
    """Pages the pupils of one section on the effective date."""

    dataset: str = "class_roster"
    schema_version: str = "class-roster-schema-v1"
    export_fields: tuple[str, ...] = (
        "student_id",
        "display_name",
        "section_id",
        "enrolment_id",
        "guardian_contact",
        "date_of_birth",
    )
    forbidden_fields: tuple[str, ...] = ("guardian_contact", "date_of_birth")
    ports: ExportPorts = field(default_factory=ExportPorts)

    def export_rows(
        self,
        ctx: RequestContext,
        dataset: str,
        filters: dict,
        cursor: str | None,
    ) -> dict:
        """Return one page of roster rows for ``filters['section_id']``.

        Raises ObjectInaccessible when the section belongs to another school,
        because RegistryPort conflates unknown and other-school on purpose.

        Does not handle: paging. The fixture sections are small enough to fit
        one page, so ``next_cursor`` is always None.
        """
        self.record("export_rows", dataset=dataset, filters=filters, cursor=cursor)
        section_id = filters.get("section_id")
        if section_id is None:
            return export_page(self.schema_version, [])
        effective = self.ports.clock.now().date()
        roster = self.ports.registry.get_roster(ctx, UUID(str(section_id)), effective)
        rows = [
            {
                "student_id": str(entry.student_id),
                "display_name": entry.display_name,
                "section_id": str(roster.section_id),
                "enrolment_id": str(entry.enrolment_id),
                "guardian_contact": f"synthetic-contact-{entry.student_id}",
                "date_of_birth": "2014-01-01",
            }
            for entry in roster.students
        ]
        return export_page(self.schema_version, rows)
