"""Resolves ``(dataset, direction)`` to the one adapter that owns it.

Adapters are built ONCE per process and reused, so an adapter's recorded calls
and its ``applied_batches`` survive between the HTTP request that starts a
commit and the worker call that resumes it. That is what makes the
resume-without-duplicating test meaningful: a fresh adapter per call would
"pass" it by forgetting.

Does not handle: the real domain write path. Every adapter here is a
deterministic fake and review-decisions item 16 records the real ones as
PENDING.
"""

from __future__ import annotations

from contracts.errors import ValidationFailed

from .at_risk import AtRiskAdapter
from .attendance_summary import AttendanceSummaryAdapter
from .base import AdapterBase, ExportPorts
from .class_roster import ClassRosterAdapter
from .enrolments import EnrolmentsAdapter
from .library_loans import LibraryLoansAdapter
from .opening_balances import OpeningBalancesAdapter
from .progress import ProgressAdapter
from .ptm_summary import PtmSummaryAdapter
from .results import ResultsAdapter
from .subject_summary import SubjectSummaryAdapter

#: Message key for a dataset outside the frozen allowlist.
UNKNOWN_DATASET = "exchange.error.unknown_dataset"

IMPORT_ADAPTERS: dict[str, type[AdapterBase]] = {
    "enrolments": EnrolmentsAdapter,
    "opening_balances": OpeningBalancesAdapter,
    "results": ResultsAdapter,
    "library_loans": LibraryLoansAdapter,
}

EXPORT_ADAPTERS: dict[str, type[AdapterBase]] = {
    "attendance_summary": AttendanceSummaryAdapter,
    "progress": ProgressAdapter,
    "at_risk": AtRiskAdapter,
    "ptm_summary": PtmSummaryAdapter,
    "class_roster": ClassRosterAdapter,
    "subject_summary": SubjectSummaryAdapter,
}

_INSTANCES: dict[tuple[str, str], AdapterBase] = {}


def import_datasets() -> tuple[str, ...]:
    """Return the frozen import dataset allowlist, sorted."""
    return tuple(sorted(IMPORT_ADAPTERS))


def export_datasets() -> tuple[str, ...]:
    """Return the frozen export/report dataset allowlist, sorted."""
    return tuple(sorted(EXPORT_ADAPTERS))


def adapter_for(
    dataset: str,
    direction: str,
    *,
    ports: ExportPorts | None = None,
) -> AdapterBase:
    """Return the process-wide adapter owning ``(dataset, direction)``.

    ``direction`` is ``"import"`` or ``"export"``. Export adapters are rebound
    to the supplied ports on every call, because the host may rebuild the port
    registry between requests while the adapter's recorded state must survive.

    Raises ValidationFailed carrying ``exchange.error.unknown_dataset`` (422)
    for a dataset outside the frozen allowlist, which is the same answer for a
    typo and for a dataset this module deliberately does not own.
    """
    table = IMPORT_ADAPTERS if direction == "import" else EXPORT_ADAPTERS
    if direction not in ("import", "export") or dataset not in table:
        raise ValidationFailed(UNKNOWN_DATASET)
    key = (direction, dataset)
    instance = _INSTANCES.get(key)
    if instance is None:
        instance = table[dataset]()
        _INSTANCES[key] = instance
    if direction == "export" and ports is not None:
        instance.ports = ports
    return instance


def reset_adapters() -> None:
    """Drop every cached adapter. Used by the baseline seed for determinism."""
    _INSTANCES.clear()
