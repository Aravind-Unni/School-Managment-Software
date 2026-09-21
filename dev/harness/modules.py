"""Reads each module's declared development resources.

``dev/modules/<ID>/module.json`` declares which containers a module needs.
``scripts/dev.py up`` starts ONLY what is declared -- a module with no
asynchronous work runs no broker and no worker, which keeps a standalone stack
small enough to run several at once.

The declaration is data, not code, so adding a module means adding a JSON file.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

#: Resources the harness knows how to start.
KNOWN_RESOURCES = ("postgres", "broker", "worker", "object_storage", "frontend")

#: Every module id, M00 (placeholder) plus the fourteen business modules.
#: Duplicated from backend/shared/module_catalog.py deliberately: the harness must
#: work with no virtual environment, so it cannot import the backend package.
#: tests/integration/test_dev_cli.py asserts the two stay identical.
KNOWN_MODULE_IDS = tuple(f"M{index:02d}" for index in range(0, 15))


class ModuleDeclarationError(RuntimeError):
    """Raised when a module's development declaration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class ModuleDeclaration:
    """One module's development resource declaration."""

    module_id: str
    slug: str
    resources: frozenset[str]
    seed_scenarios: tuple[str, ...]
    implemented: bool

    @property
    def needs_broker(self) -> bool:
        """Return whether a real broker must be started.

        A worker implies a broker: running a worker with no broker would make
        asynchronous tests pass vacuously.
        """
        return "broker" in self.resources or "worker" in self.resources

    @property
    def needs_worker(self) -> bool:
        """Return whether a real worker must be started."""
        return "worker" in self.resources

    @property
    def needs_object_storage(self) -> bool:
        """Return whether S3-compatible storage must be started."""
        return "object_storage" in self.resources

    @property
    def needs_frontend(self) -> bool:
        """Return whether the Vite dev server must be started."""
        return "frontend" in self.resources


def declaration_path(repo_root: pathlib.Path, module_id: str) -> pathlib.Path:
    """Return the path to a module's development declaration."""
    return repo_root / "dev" / "modules" / module_id.upper() / "module.json"


def load(repo_root: pathlib.Path, module_id: str) -> ModuleDeclaration:
    """Load and validate one module's declaration.

    Raises ModuleDeclarationError with an actionable message when the file is
    absent or names an unknown resource. ``implemented`` reflects whether the
    backend package actually has a ``registration.py``: a declaration alone does
    not mean there is code, and ``up`` must say so rather than booting an empty
    app.
    """
    normalised = module_id.upper()
    path = declaration_path(repo_root, normalised)
    if not path.exists():
        raise ModuleDeclarationError(
            f"{normalised} has no development declaration at "
            f"{path.relative_to(repo_root)}. Create it from "
            "dev/modules/TEMPLATE.module.json."
        )
    try:
        data = json.loads(path.read_text())
    except ValueError as exc:
        raise ModuleDeclarationError(f"{path} is not valid JSON: {exc}") from exc

    declared = data.get("resources") or {}
    if not isinstance(declared, dict):
        raise ModuleDeclarationError(f"{path}: 'resources' must be an object")
    unknown = sorted(set(declared) - set(KNOWN_RESOURCES))
    if unknown:
        raise ModuleDeclarationError(
            f"{path}: unknown resources {unknown}; known are {list(KNOWN_RESOURCES)}"
        )
    enabled = frozenset(name for name, on in declared.items() if on)
    if "postgres" not in enabled:
        raise ModuleDeclarationError(
            f"{path}: every module needs postgres; a standalone profile applies "
            "its real migrations to an isolated PostgreSQL database."
        )

    slug = data.get("slug")
    if not slug:
        raise ModuleDeclarationError(f"{path}: 'slug' is required")

    if normalised == "ALL":
        # C02 integrated host: implemented when every M00–M14 registration exists.
        missing = []
        for mid in KNOWN_MODULE_IDS:
            mid_path = declaration_path(repo_root, mid)
            mid_slug = json.loads(mid_path.read_text())["slug"]
            if not (repo_root / "backend" / "modules" / mid_slug / "registration.py").exists():
                missing.append(mid)
        implemented = not missing
    else:
        registration = repo_root / "backend" / "modules" / slug / "registration.py"
        implemented = registration.exists()

    return ModuleDeclaration(
        module_id=normalised,
        slug=slug,
        resources=enabled,
        seed_scenarios=tuple(data.get("seed_scenarios") or ()),
        implemented=implemented,
    )
