"""Machine-readable run records.

``dev.py check`` writes one JSON report per suite; ``dev.py evidence`` gathers
them into a bundle a reviewer can read without re-running anything.

Every record states which backend produced it. A SQLite local run and a
PostgreSQL container run are not interchangeable, and a bundle that did not say
which one it was would let an unverified claim look verified.
"""

from __future__ import annotations

import json
import pathlib
import platform
import subprocess
from datetime import UTC, datetime

EVIDENCE_DIRNAME = "dev/evidence"


def utc_now_iso() -> str:
    """Return the current instant as an ISO 8601 UTC string."""
    return datetime.now(UTC).isoformat()


def source_identity(repo_root: pathlib.Path) -> dict[str, str]:
    """Return the exact commit and tree state this evidence describes.

    ``dirty`` matters: evidence produced from an uncommitted tree cannot be
    reproduced from the recorded commit, and a reviewer must be told.
    """

    def git(*arguments: str) -> str:
        try:
            result = subprocess.run(
                ["git", *arguments],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except (OSError, subprocess.SubprocessError):
            return "unknown"

    status = git("status", "--porcelain")
    return {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": "true" if status and status != "unknown" else "false",
        "recorded_at": utc_now_iso(),
    }


def environment() -> dict[str, str]:
    """Return host facts relevant to reproducing a result."""
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
    }


def report_path(repo_root: pathlib.Path, stem: str, suite: str) -> pathlib.Path:
    """Return where a suite's report for one namespace is written."""
    return repo_root / EVIDENCE_DIRNAME / stem / f"{suite}.json"


def write_report(
    *,
    repo_root: pathlib.Path,
    stem: str,
    suite: str,
    module_id: str,
    passed: bool,
    backend: str,
    details: dict[str, object],
) -> pathlib.Path:
    """Write one suite report and return its path.

    ``backend`` names what the suite actually ran against ("postgres-container",
    "sqlite-local-only", "not-run"). ``passed`` is never inferred from absence:
    a suite that did not run is recorded as not run, not as passing.
    """
    path = report_path(repo_root, stem, suite)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "suite": suite,
        "module_id": module_id,
        "passed": passed,
        "backend": backend,
        "source": source_identity(repo_root),
        "environment": environment(),
        "details": details,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def collect_bundle(repo_root: pathlib.Path, stem: str, module_id: str) -> dict[str, object]:
    """Gather every suite report for one namespace into a bundle.

    Suites with no report are listed as ``not_run`` rather than omitted, so a
    reviewer sees the gap instead of having to notice an absence.
    """
    directory = repo_root / EVIDENCE_DIRNAME / stem
    expected = ("standalone", "contracts", "browser")
    suites: dict[str, object] = {}
    for suite in expected:
        path = directory / f"{suite}.json"
        if path.exists():
            suites[suite] = json.loads(path.read_text())
        else:
            suites[suite] = {
                "suite": suite,
                "module_id": module_id,
                "passed": False,
                "backend": "not-run",
                "details": {"reason": "no report; this suite was never run"},
            }
    all_passed = all(
        isinstance(report, dict) and report.get("passed") for report in suites.values()
    )
    return {
        "module_id": module_id,
        "namespace": stem,
        "generated_at": utc_now_iso(),
        "source": source_identity(repo_root),
        "all_suites_passed": all_passed,
        "suites": suites,
    }
