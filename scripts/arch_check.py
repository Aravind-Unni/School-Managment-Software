#!/usr/bin/env python3
"""Static architecture checks. Standard library only; no imports of the app.

Fails CI on the structural mistakes that tests cannot catch because they are
about *shape*, not behaviour:

  1. cross-module imports        -- modules.<a> importing modules.<b>
  2. contracts purity            -- backend/contracts importing Django or modules
  3. shared purity               -- backend/shared importing any business module
  4. fake adapters in production -- a production config selecting a fake
  5. unimplemented imports       -- importing a module with no registration.py
  6. layout completeness         -- every module id has its required directories
  7. module size                 -- no source file over the size ceiling

Every failure prints the file, the line and why it matters. Exit status is
nonzero when any check fails.
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import sys
from dataclasses import dataclass, field

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"

MODULE_SLUGS = {
    "M00": "demo",
    "M01": "access",
    "M02": "registry",
    "M03": "timetable",
    "M04": "attendance",
    "M05": "assessment",
    "M06": "performance",
    "M07": "fees",
    "M08": "transport",
    "M09": "library",
    "M10": "alumni",
    "M11": "communications",
    "M12": "files",
    "M13": "exchange",
    "M14": "platform",
}
BUSINESS_IDS = tuple(mid for mid in sorted(MODULE_SLUGS) if mid != "M00")
ALL_SLUGS = frozenset(MODULE_SLUGS.values())

#: Ceiling on a single source file. Not a style preference: a module that needs
#: more than this is doing more than one job, and the next agent reading it cold
#: cannot hold it in context.
MAX_FILE_LINES = 500

#: An explicit, auditable opt-out for a line that NAMES a development component
#: in order to REFUSE it. Assertions like `if "shared.harness" in INSTALLED_APPS:
#: raise ProductionSafetyError` must mention the thing they forbid. The marker is
#: required to carry a reason, so every exemption is reviewable in the diff.
ALLOW_MARKER = "# arch-allow: production-safety --"

#: Names that identify a fake/test adapter. A production settings module must
#: not reference any of them.
FAKE_MARKERS = (
    "FakeAccess",
    "FakeRegistry",
    "FakeNotifications",
    "FakeObjectStorage",
    "TestPlatformAdapter",
    "FixedClock",
    "build_fake_registry",
    "DevPersona",
    "shared.fakes",
    "shared.harness",
)


@dataclass
class Findings:
    """Accumulated violations, grouped by check name."""

    problems: list[str] = field(default_factory=list)

    def add(self, check: str, path: pathlib.Path, line: int, message: str) -> None:
        """Record one violation with a clickable location."""
        relative = path.relative_to(REPO_ROOT)
        self.problems.append(f"[{check}] {relative}:{line}: {message}")

    @property
    def ok(self) -> bool:
        """Return whether no violation was recorded."""
        return not self.problems


def python_files(root: pathlib.Path) -> list[pathlib.Path]:
    """Return every .py file under a root, skipping migrations and caches."""
    return [
        path
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts and "migrations" not in path.parts
    ]


def imported_names(tree: ast.AST) -> list[tuple[str, int]]:
    """Return (dotted_name, lineno) for every import in a parsed module.

    Handles ``import a.b``, ``from a.b import c`` and relative imports (which
    are returned with leading dots so the caller can ignore them).
    """
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * (node.level or 0)
            found.append((prefix + (node.module or ""), node.lineno))
    return found


def owning_module_slug(path: pathlib.Path) -> str | None:
    """Return the module slug a file belongs to, or None if outside modules/."""
    try:
        parts = path.relative_to(BACKEND / "modules").parts
    except ValueError:
        return None
    return parts[0] if parts else None


def check_cross_module_imports(findings: Findings) -> None:
    """No business module may import another business module.

    Collaboration goes through the typed service ports the host binds. A direct
    import couples migrations, deploy order and test setup, and it silently
    defeats standalone mode.
    """
    for path in python_files(BACKEND / "modules"):
        owner = owning_module_slug(path)
        if owner is None:
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for name, line in imported_names(tree):
            if not name.startswith("modules."):
                continue
            target = name.split(".")[1] if len(name.split(".")) > 1 else ""
            if target in ALL_SLUGS and target != owner:
                findings.add(
                    "cross-module-import",
                    path,
                    line,
                    f"module {owner!r} imports module {target!r}. Use a service "
                    f"port from contracts.ports, bound by the host, instead.",
                )


def check_contracts_purity(findings: Findings) -> None:
    """backend/contracts must import neither Django nor any business module.

    It is the one package every module and the generated TypeScript client
    depend on. A Django import there would make the contracts untestable without
    a settings module and would invite ORM models to creep in.
    """
    for path in python_files(BACKEND / "contracts"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for name, line in imported_names(tree):
            if name.startswith("django"):
                findings.add(
                    "contracts-purity",
                    path,
                    line,
                    f"contracts must not import Django ({name}). Keep DTOs and "
                    "Protocols framework-free; never put an ORM model here.",
                )
            if name.startswith("modules."):
                findings.add(
                    "contracts-purity",
                    path,
                    line,
                    f"contracts must not import a business module ({name}); "
                    "the dependency runs the other way.",
                )


def check_shared_purity(findings: Findings) -> None:
    """backend/shared must not import any business module.

    The harness is shared by all fourteen; depending on one of them would make
    standalone mode load code it claims to exclude.
    """
    for path in python_files(BACKEND / "shared"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for name, line in imported_names(tree):
            if name.startswith("modules."):
                findings.add(
                    "shared-purity",
                    path,
                    line,
                    f"shared harness must not import a business module ({name}).",
                )


def _refusal_line_numbers(tree: ast.AST) -> set[int]:
    """Return the lines of every statement that RAISES ProductionSafetyError.

    A guard such as ``if "shared.harness" in INSTALLED_APPS: raise
    ProductionSafetyError(...)`` has to name the thing it forbids. Deriving the
    exemption from the AST rather than from a trailing comment makes it immune to
    the formatter moving that comment onto another line -- which is exactly how
    the comment-based version of this check broke.
    """
    exempt: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.Assert)):
            continue
        raises_refusal = any(
            isinstance(inner, ast.Raise) and "ProductionSafetyError" in ast.dump(inner)
            for inner in ast.walk(node)
        )
        if raises_refusal:
            end = getattr(node, "end_lineno", node.lineno) or node.lineno
            exempt.update(range(node.lineno, end + 1))
    return exempt


def check_production_has_no_fakes(findings: Findings) -> None:
    """Fail when a production settings module selects a development component.

    This is the static half of the guarantee; PortRegistry.register enforces the
    runtime half. Both exist because each catches a different mistake: a config
    committed to the repository, and a factory wired at boot.

    Two exemptions, both narrow: a statement that raises ProductionSafetyError
    (detected structurally), and an explicit ALLOW_MARKER that must carry a
    reason.
    """
    production = BACKEND / "config" / "settings" / "production.py"
    if not production.exists():
        findings.add(
            "production-safety",
            production,
            0,
            "no production settings module exists; the fake-refusal path cannot be verified.",
        )
        return

    source = production.read_text()
    tree = ast.parse(source, filename=str(production))

    for name, line in imported_names(tree):
        for marker in FAKE_MARKERS:
            if marker in name:
                findings.add(
                    "production-safety",
                    production,
                    line,
                    f"production settings import a development component "
                    f"({name}). Production must refuse fake adapters, test "
                    "personas and demo fixtures.",
                )

    exempt = _refusal_line_numbers(tree)

    for number, text in enumerate(source.splitlines(), start=1):
        stripped = text.strip()
        if stripped.startswith("#") or number in exempt:
            continue
        if ALLOW_MARKER in stripped:
            _, _, reason = stripped.partition(ALLOW_MARKER)
            if not reason.strip():
                findings.add(
                    "production-safety",
                    production,
                    number,
                    "arch-allow marker carries no reason; state why this line "
                    "must name a development component.",
                )
            continue
        for marker in FAKE_MARKERS:
            # `DEV_PERSONA = None` is an explicit disabling, not a usage.
            if marker in stripped and "None" not in stripped:
                findings.add(
                    "production-safety",
                    production,
                    number,
                    f"production settings reference {marker!r}. If this line "
                    "exists to refuse it, raise ProductionSafetyError from the "
                    f"enclosing guard, or append '{ALLOW_MARKER} <reason>'.",
                )


def check_no_imports_of_unimplemented_modules(findings: Findings) -> None:
    """Nothing may import a module that has no registration.py.

    Because a directory without __init__.py is still a namespace package, such
    an import succeeds and yields an empty module. That is exactly the silent
    half-dependency this check exists to prevent.
    """
    implemented = {
        slug for slug in ALL_SLUGS if (BACKEND / "modules" / slug / "registration.py").exists()
    }
    unimplemented = ALL_SLUGS - implemented
    roots = [BACKEND, REPO_ROOT / "tests"]
    for root in roots:
        if not root.exists():
            continue
        for path in python_files(root):
            tree = ast.parse(path.read_text(), filename=str(path))
            for name, line in imported_names(tree):
                if not name.startswith("modules."):
                    continue
                pieces = name.split(".")
                if len(pieces) > 1 and pieces[1] in unimplemented:
                    findings.add(
                        "unimplemented-import",
                        path,
                        line,
                        f"imports {name!r}, but module {pieces[1]!r} has no "
                        "registration.py. It resolves as an empty namespace "
                        "package, which hides the missing dependency.",
                    )


def check_layout(findings: Findings) -> None:
    """Every module id must have its contract, dev and docs directories."""
    for module_id, slug in sorted(MODULE_SLUGS.items()):
        required = [
            REPO_ROOT / "contracts" / module_id,
            REPO_ROOT / "dev" / "modules" / module_id,
            REPO_ROOT / "docs" / "modules" / module_id,
            BACKEND / "modules" / slug,
            REPO_ROOT / "frontend" / "src" / "features" / slug,
        ]
        for directory in required:
            if not directory.is_dir():
                findings.add(
                    "layout",
                    directory,
                    0,
                    f"required directory for {module_id} is missing.",
                )
    for module_id in BUSINESS_IDS:
        packet = REPO_ROOT / "contracts" / module_id / "PACKET.md"
        if not packet.exists():
            findings.add(
                "layout",
                packet,
                0,
                f"{module_id} has no contract packet; contract approval precedes "
                "module coding.",
            )


def check_file_sizes(findings: Findings) -> None:
    """No source file may exceed MAX_FILE_LINES."""
    for path in python_files(BACKEND):
        lines = len(path.read_text().splitlines())
        if lines > MAX_FILE_LINES:
            findings.add(
                "file-size",
                path,
                lines,
                f"{lines} lines exceeds the {MAX_FILE_LINES}-line ceiling; split "
                "it by responsibility.",
            )


CHECKS = (
    ("cross-module-import", check_cross_module_imports),
    ("contracts-purity", check_contracts_purity),
    ("shared-purity", check_shared_purity),
    ("production-safety", check_production_has_no_fakes),
    ("unimplemented-import", check_no_imports_of_unimplemented_modules),
    ("layout", check_layout),
    ("file-size", check_file_sizes),
)


def main() -> int:
    """Run every check and report. Returns nonzero on any violation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="run a single named check")
    arguments = parser.parse_args()

    findings = Findings()
    selected = [
        (name, function)
        for name, function in CHECKS
        if arguments.only is None or name == arguments.only
    ]
    if not selected:
        print(f"no such check: {arguments.only}", file=sys.stderr)
        print(f"available: {', '.join(name for name, _ in CHECKS)}", file=sys.stderr)
        return 2

    for _name, function in selected:
        function(findings)

    if findings.ok:
        print(f"OK: {len(selected)} architecture checks passed")
        return 0

    print(f"FAIL: {len(findings.problems)} architecture violation(s)", file=sys.stderr)
    for problem in findings.problems:
        print(f"  {problem}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
