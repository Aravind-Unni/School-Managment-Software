"""Parent-meeting summary export adapter.

Reads a fee BALANCE only. ``raise_charge`` and ``credit_charge`` are refused
outright by ``refuse_ledger_write``: review-decisions item 14 says a report may
read the ledger and must never post to it, and a fake that quietly accepted a
charge from reporting code would hide exactly that mistake.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext

from .base import AdapterBase, ExplicitlyUnused, ExportPorts, export_page


@dataclass
class PtmSummaryAdapter(AdapterBase):
    """Pages the per-pupil lines a parent-teacher meeting sheet carries."""

    dataset: str = "ptm_summary"
    schema_version: str = "ptm-summary-schema-v1"
    export_fields: tuple[str, ...] = (
        "student_id",
        "display_name",
        "outstanding_paise",
        "overdue_paise",
        "attendance_marked",
        "guardian_phone",
    )
    forbidden_fields: tuple[str, ...] = ("guardian_phone",)
    ports: ExportPorts = field(default_factory=ExportPorts)

    def export_rows(
        self,
        ctx: RequestContext,
        dataset: str,
        filters: dict,
        cursor: str | None,
    ) -> dict:
        """Return one meeting row per pupil in the filtered section."""
        self.record("export_rows", dataset=dataset, filters=filters, cursor=cursor)
        section_id = filters.get("section_id")
        if section_id is None:
            return export_page(self.schema_version, [])
        effective = self.ports.clock.now().date()
        roster = self.ports.registry.get_roster(ctx, UUID(str(section_id)), effective)
        rows = []
        for entry in roster.students:
            balance = self.ports.fees.get_balance(ctx, entry.student_id, effective)
            rows.append(
                {
                    "student_id": str(entry.student_id),
                    "display_name": entry.display_name,
                    "outstanding_paise": balance.outstanding_paise,
                    "overdue_paise": balance.overdue_paise,
                    "attendance_marked": self._marked(ctx, entry.student_id, effective),
                    "guardian_phone": f"synthetic-phone-{entry.student_id}",
                }
            )
        return export_page(self.schema_version, rows)

    def refuse_ledger_write(self, operation: str) -> None:
        """Refuse any attempt to post to the ledger from reporting code.

        Exists so the refusal is a named, testable call site rather than an
        absence. Always raises.
        """
        raise ExplicitlyUnused(
            f"exchange must not call fees.{operation}; reports read get_balance only"
        )

    def _marked(self, ctx: RequestContext, student_id, effective) -> int | str:
        """Return marked period count, or empty when M04 has no inputs."""
        try:
            return self.ports.attendance.get_summary(
                ctx, student_id, effective, effective
            ).marked
        except ObjectInaccessible:
            return ""
