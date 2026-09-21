"""Module-local dataset adapters. One per import/export dataset family.

Nothing here imports another business module's ORM. Each adapter satisfies the
module-local ``DomainExchangePort`` Protocol in ``base.py`` and reaches domain
facts only through the service ports the host bound.
"""

from .base import (
    DomainExchangePort,
    ExplicitlyUnused,
    ExportPorts,
    RowError,
    apply_result,
    export_page,
    validate_result,
)
from .registry import adapter_for, export_datasets, import_datasets

__all__ = [
    "DomainExchangePort",
    "ExplicitlyUnused",
    "ExportPorts",
    "RowError",
    "adapter_for",
    "apply_result",
    "export_datasets",
    "export_page",
    "import_datasets",
    "validate_result",
]
