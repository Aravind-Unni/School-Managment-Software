"""The architecture checks must actually reject violations.

A guard that has never been seen to fail is not a guard. Each test here
introduces one real violation into the working tree, runs the checker as a
subprocess exactly as CI does, and restores the tree in a finally block.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ARCH_CHECK = REPO_ROOT / "scripts" / "arch_check.py"
MANIFEST_SCRIPT = REPO_ROOT / "scripts" / "contract_manifest.py"


def run(script: pathlib.Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run a check script the way CI does and capture its output."""
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_the_checker_passes_on_the_clean_tree():
    result = run(ARCH_CHECK)
    assert result.returncode == 0, result.stderr
    assert "architecture checks passed" in result.stdout


def test_a_cross_module_import_is_rejected():
    """A module importing another module must fail CI."""
    offender = REPO_ROOT / "backend" / "modules" / "demo" / "_tmp_violation.py"
    offender.write_text(
        '"""Temporary file introducing a deliberate violation."""\n'
        "from modules.attendance import models  # noqa: F401\n"
    )
    try:
        result = run(ARCH_CHECK)
        assert result.returncode == 1
        assert "cross-module-import" in result.stderr
        assert "Use a service port" in result.stderr
    finally:
        offender.unlink()
    # The tree must be clean again, or this test poisons every later one.
    assert run(ARCH_CHECK).returncode == 0


def test_importing_an_unimplemented_module_is_rejected():
    """Namespace packages make this import succeed, so it needs a static check."""
    offender = REPO_ROOT / "backend" / "shared" / "_tmp_violation.py"
    offender.write_text(
        '"""Temporary file introducing a deliberate violation."""\n'
        "import modules.fees  # noqa: F401\n"
    )
    try:
        result = run(ARCH_CHECK)
        assert result.returncode == 1
        assert "unimplemented-import" in result.stderr
        assert "empty namespace" in result.stderr
    finally:
        offender.unlink()
    assert run(ARCH_CHECK).returncode == 0


def test_the_shared_harness_may_not_import_a_business_module():
    offender = REPO_ROOT / "backend" / "shared" / "_tmp_shared_violation.py"
    offender.write_text(
        '"""Temporary file introducing a deliberate violation."""\n'
        "from modules.demo import models  # noqa: F401\n"
    )
    try:
        result = run(ARCH_CHECK)
        assert result.returncode == 1
        assert "shared-purity" in result.stderr
    finally:
        offender.unlink()
    assert run(ARCH_CHECK).returncode == 0


def test_a_django_import_in_the_contracts_package_is_rejected():
    offender = REPO_ROOT / "backend" / "contracts" / "_tmp_violation.py"
    offender.write_text(
        '"""Temporary file introducing a deliberate violation."""\n'
        "from django.db import models  # noqa: F401\n"
    )
    try:
        result = run(ARCH_CHECK)
        assert result.returncode == 1
        assert "contracts-purity" in result.stderr
        assert "ORM model" in result.stderr
    finally:
        offender.unlink()
    assert run(ARCH_CHECK).returncode == 0


def test_a_fake_adapter_in_the_production_config_is_rejected():
    """The acceptance criterion: CI rejects a production fake configuration."""
    production = REPO_ROOT / "backend" / "config" / "settings" / "production.py"
    original = production.read_text()
    production.write_text(
        original
        + "\n# Deliberate violation introduced by a test.\n"
        + "from shared.fakes import FakeAccess\n"
        + "SOME_PORT = FakeAccess\n"
    )
    try:
        result = run(ARCH_CHECK)
        assert result.returncode == 1
        assert "production-safety" in result.stderr
        assert "FakeAccess" in result.stderr
    finally:
        production.write_text(original)
    assert run(ARCH_CHECK).returncode == 0


def test_an_unjustified_allow_marker_is_rejected():
    """The opt-out must carry a reason, or it is just a way to silence the check."""
    production = REPO_ROOT / "backend" / "config" / "settings" / "production.py"
    original = production.read_text()
    production.write_text(original + "\nFOO = FixedClock  # arch-allow: production-safety --\n")
    try:
        result = run(ARCH_CHECK)
        assert result.returncode == 1
        assert "carries no reason" in result.stderr
    finally:
        production.write_text(original)
    assert run(ARCH_CHECK).returncode == 0


def test_schema_drift_is_rejected():
    """A contract file changing without a manifest update must fail CI."""
    schema = REPO_ROOT / "contracts" / "common" / "error-envelope.schema.json"
    original = schema.read_text()
    schema.write_text(original.replace('"title": "ErrorEnvelope"', '"title": "Drifted"'))
    try:
        result = run(MANIFEST_SCRIPT, "--check")
        assert result.returncode == 1
        assert "schema drift detected" in result.stderr
        assert "error-envelope.schema.json" in result.stderr
    finally:
        schema.write_text(original)
    assert run(MANIFEST_SCRIPT, "--check").returncode == 0


def test_the_manifest_is_current_and_names_an_owner_for_every_entry():
    import json

    result = run(MANIFEST_SCRIPT, "--check")
    assert result.returncode == 0, result.stderr

    manifest = json.loads((REPO_ROOT / "contracts" / "manifest.json").read_text())
    assert manifest["revision"] == "school-contracts-v3-draft"
    entries = list(manifest["common"])
    for module in manifest["modules"].values():
        entries.extend(module["artefacts"])
        entries.extend(module["fixtures"])
    assert entries, "manifest records no contract artefacts at all"
    for entry in entries:
        assert entry["owner"], entry
        assert len(entry["sha256"]) == 64, entry


def test_no_business_module_contract_is_frozen_yet():
    """Only the placeholder may be frozen in B00.

    A frozen business contract here would mean a module's interface was approved
    without passing its human review gate.
    """
    import json

    manifest = json.loads((REPO_ROOT / "contracts" / "manifest.json").read_text())
    for module_id, module in manifest["modules"].items():
        if module_id == "M00":
            assert module["status"] == "frozen"
            continue
        assert module["status"] == "not_started", module_id
        assert module["artefacts"] == [], module_id


@pytest.mark.parametrize("module_id", [f"M{index:02d}" for index in range(1, 15)])
def test_every_business_module_has_a_contract_packet(module_id):
    """Every business module carries a packet, and states its real status.

    M01 is legitimately in progress, so "NOT STARTED" is asserted only for the
    modules that have not begun. Asserting it unconditionally would force a false
    status onto a module that had started.
    """
    packet = REPO_ROOT / "contracts" / module_id / "PACKET.md"
    assert packet.exists()
    text = packet.read_text()
    assert "school-contracts-v3-draft" in text
    if module_id == "M01":
        assert "CONTRACT PROPOSED" in text
    else:
        assert "NOT STARTED" in text
