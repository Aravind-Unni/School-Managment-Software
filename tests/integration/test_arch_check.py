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
        "import modules.communications  # noqa: F401\n"
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
    revision_record = json.loads((REPO_ROOT / "contracts" / "revision.json").read_text())
    # The revision is data now, not a constant in the generator. Asserting the
    # two agree is the useful check; asserting a literal string would have to be
    # edited by every reviewed revision and would prove nothing about either.
    assert manifest["revision"] == revision_record["revision"]
    entries = list(manifest["common"])
    for module in manifest["modules"].values():
        entries.extend(module["artefacts"])
        entries.extend(module["fixtures"])
    assert entries, "manifest records no contract artefacts at all"
    for entry in entries:
        assert entry["owner"], entry
        assert len(entry["sha256"]) == 64, entry


def test_nothing_is_frozen_without_a_recorded_human_review():
    """A frozen contract must name the review that froze it.

    Replaces an earlier assertion that NO business module was frozen yet. That
    was true at B00 and stopped being true the moment a packet passed its gate,
    so as a permanent guard it could only ever be deleted. This asserts the rule
    the original was reaching for, and is strictly stronger: freezing is a human
    review gate, so a frozen module must carry the reviewer and date that closed
    it, and an unreviewed module must have nothing frozen.
    """
    import json

    manifest = json.loads((REPO_ROOT / "contracts" / "manifest.json").read_text())
    reviews = json.loads((REPO_ROOT / "contracts" / "revision.json").read_text())[
        "frozen_modules"
    ]

    for module_id, module in manifest["modules"].items():
        entries = module["artefacts"] + module["fixtures"]
        if module_id in reviews:
            assert module["status"] == "frozen", module_id
            assert reviews[module_id]["reviewer"], module_id
            assert reviews[module_id]["reviewed_on"], module_id
            for entry in entries:
                assert entry["frozen"] is True, (module_id, entry["id"])
        else:
            # An unreviewed module may legitimately have artefacts in progress;
            # what it may not have is any of them frozen.
            for entry in entries:
                assert entry["frozen"] is False, (module_id, entry["id"])
            assert module["status"] in {"not_started", "in_progress"}, module_id


@pytest.mark.parametrize("module_id", [f"M{index:02d}" for index in range(1, 15)])
def test_every_business_module_has_a_contract_packet(module_id):
    """Every business module carries a packet, and states its real status.

    M01 is legitimately in progress, so "NOT STARTED" is asserted only for the
    modules that have not begun. Asserting it unconditionally would force a false
    status onto a module that had started.
    """
    import json

    packet = REPO_ROOT / "contracts" / module_id / "PACKET.md"
    assert packet.exists()
    text = packet.read_text()
    reviews = json.loads((REPO_ROOT / "contracts" / "revision.json").read_text())[
        "frozen_modules"
    ]

    if module_id in reviews:
        # An approved packet must say so and name the revision that froze it,
        # so a reader of the file alone cannot mistake it for a proposal.
        assert "APPROVED AND FROZEN" in text, module_id
        assert reviews[module_id]["reviewed_on"] in text, module_id
    elif module_id == "M01":
        assert "CONTRACT PROPOSED" in text
    else:
        assert "school-contracts-v3-draft" in text
        assert "NOT STARTED" in text
