"""Tests for scripts/dev.py and the dev/harness modules.

Two things get special attention because they are duplicated on purpose -- the
harness must run with no virtual environment, so it cannot import the backend --
and duplication rots silently: the module catalogue and the redaction rules.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV_PY = REPO_ROOT / "scripts" / "dev.py"
sys.path.insert(0, str(REPO_ROOT / "dev"))


def run_dev(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Invoke dev.py as a subprocess, exactly as a developer or CI would."""
    return subprocess.run(
        [sys.executable, str(DEV_PY), *arguments],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


# --- duplication that must not drift --------------------------------------


def test_the_harness_module_ids_match_the_backend_catalogue():
    from harness.modules import KNOWN_MODULE_IDS

    from shared.module_catalog import MODULE_SLUGS

    assert set(KNOWN_MODULE_IDS) == set(MODULE_SLUGS)


def test_every_declaration_slug_matches_the_backend_catalogue():
    from harness.modules import KNOWN_MODULE_IDS, load

    from shared.module_catalog import MODULE_SLUGS

    for module_id in KNOWN_MODULE_IDS:
        assert load(REPO_ROOT, module_id).slug == MODULE_SLUGS[module_id]


def test_only_m00_is_reported_as_implemented():
    from harness.modules import KNOWN_MODULE_IDS, load

    implemented = [
        module_id for module_id in KNOWN_MODULE_IDS if load(REPO_ROOT, module_id).implemented
    ]
    assert implemented == ["M00"]


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SESSION_SECRET", "hunter2"),
        ("TOTP_ENCRYPTION_KEY", "key-material"),
        ("OBJECT_STORAGE_SECRET_KEY", "secret"),
        ("DATABASE_URL", "postgresql://u:pw@127.0.0.1:5432/school_x"),
        ("APP_ENV", "standalone"),
    ],
)
def test_dev_py_redaction_agrees_with_the_backend_implementation(monkeypatch, name, value):
    """dev.py reimplements redaction so doctor works with no venv.

    The two implementations must agree, or doctor could print something the
    backend considers secret.
    """
    import importlib.util

    from config.env import redact

    spec = importlib.util.spec_from_file_location("dev_cli", DEV_PY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    monkeypatch.setenv(name, value)
    assert module._redacted_environment()[name] == redact(name, value)


def test_no_secret_value_survives_doctor_output(monkeypatch):
    result = subprocess.run(
        [sys.executable, str(DEV_PY), "doctor"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "SESSION_SECRET": "SUPERSECRETVALUE",
            "TOTP_ENCRYPTION_KEY": "ANOTHERSECRET",
            "DATABASE_URL": "postgresql://u:PASSWORDLEAK@127.0.0.1:5432/school_x",
        },
    )
    combined = result.stdout + result.stderr
    assert "SUPERSECRETVALUE" not in combined
    assert "ANOTHERSECRET" not in combined
    assert "PASSWORDLEAK" not in combined
    assert "<set>" in combined


# --- honest failure -------------------------------------------------------


def test_an_unimplemented_module_is_refused_with_its_own_exit_code():
    result = run_dev("up", "M04")
    assert result.returncode == 3
    assert "not implemented" in result.stderr
    assert "contracts/M04/PACKET.md" in result.stderr


def test_an_unknown_module_id_is_refused():
    result = run_dev("up", "M99")
    assert result.returncode == 2
    assert "no development declaration" in result.stderr


def test_an_undeclared_seed_scenario_is_refused_and_lists_the_real_ones():
    result = run_dev("seed", "M00", "--scenario", "does-not-exist")
    assert result.returncode == 4
    assert "baseline" in result.stderr


def test_down_reports_cleanly_when_nothing_is_running():
    result = run_dev("down", "M00")
    assert result.returncode == 0


def test_the_contracts_suite_runs_without_any_container():
    # This is the suite that must always work, so a developer is never blocked.
    result = run_dev("check", "M00", "--suite", "contracts")
    assert result.returncode == 0, result.stderr
    assert "report" in result.stdout


def test_a_suite_that_cannot_run_is_recorded_as_not_run_not_as_passing():
    result = run_dev("check", "M00", "--suite", "standalone")
    assert result.returncode == 2
    assert "did not run" in result.stderr
    from harness.naming import ResourceNames

    names = ResourceNames(module_id="M00", repo_root=REPO_ROOT)
    report = json.loads(
        (REPO_ROOT / "dev" / "evidence" / names.stem / "standalone.json").read_text()
    )
    assert report["passed"] is False
    assert report["backend"] == "not-run"


def test_evidence_fails_when_a_suite_did_not_pass():
    result = run_dev("evidence", "M00")
    assert result.returncode == 1
    assert "not ready for review" in result.stderr


# --- seed refusal ---------------------------------------------------------


def test_seed_refuses_targets_that_are_not_development_databases():
    import importlib.util

    from harness.naming import ResourceNames

    spec = importlib.util.spec_from_file_location("dev_cli_seed", DEV_PY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    names = ResourceNames(module_id="M00", repo_root=REPO_ROOT)
    safe = f"postgresql://u:p@127.0.0.1:5432/{names.database}"
    assert module.refuse_non_development_target(safe, names) == ""

    # A database that is not harness-created at all.
    assert "not a harness-created" in module.refuse_non_development_target(
        "postgresql://u:p@127.0.0.1:5432/production_db", names
    )
    # A name that happens to share the 'school_' prefix but is not this
    # namespace. Caught by the exact-match check rather than the prefix check --
    # which is why both checks exist.
    assert "does not match this namespace" in module.refuse_non_development_target(
        "postgresql://u:p@127.0.0.1:5432/school_production", names
    )
    # Another developer's namespace.
    assert "does not match this namespace" in module.refuse_non_development_target(
        "postgresql://u:p@127.0.0.1:5432/school_someoneelse_wt_m00", names
    )
    # A remote host, with an otherwise correct database name.
    assert "not loopback" in module.refuse_non_development_target(
        f"postgresql://u:p@db.school.example.com:5432/{names.database}", names
    )

    # Every one of the above is refused; none returns an empty string.
    for unsafe in (
        "postgresql://u:p@127.0.0.1:5432/production_db",
        "postgresql://u:p@127.0.0.1:5432/school_production",
        "postgresql://u:p@127.0.0.1:5432/school_someoneelse_wt_m00",
        f"postgresql://u:p@db.school.example.com:5432/{names.database}",
    ):
        assert module.refuse_non_development_target(unsafe, names) != ""


# --- namespacing and isolation -------------------------------------------


def test_two_modules_get_entirely_separate_resources():
    from harness.naming import ResourceNames

    first = ResourceNames(module_id="M00", repo_root=REPO_ROOT)
    second = ResourceNames(module_id="M04", repo_root=REPO_ROOT)
    for attribute in ("compose_project", "database", "bucket", "queue", "volume_prefix"):
        assert getattr(first, attribute) != getattr(second, attribute), attribute


def test_two_worktrees_of_one_repo_get_separate_resources(tmp_path):
    from harness.naming import ResourceNames

    here = ResourceNames(module_id="M00", repo_root=REPO_ROOT)
    elsewhere = ResourceNames(module_id="M00", repo_root=tmp_path / "aumspro")
    assert here.database != elsewhere.database


def test_bucket_names_avoid_underscores_which_s3_forbids():
    from harness.naming import ResourceNames

    names = ResourceNames(module_id="M00", repo_root=REPO_ROOT)
    assert "_" not in names.bucket


def test_database_identifiers_stay_within_postgres_limits():
    from harness.naming import ResourceNames

    names = ResourceNames(module_id="M14", repo_root=REPO_ROOT)
    assert len(names.database) <= 63


# --- compose rendering ---------------------------------------------------


def test_a_module_with_no_async_work_starts_no_broker():
    import yaml
    from harness import compose
    from harness.modules import load
    from harness.naming import ResourceNames

    declaration = load(REPO_ROOT, "M00")
    names = ResourceNames(module_id="M00", repo_root=REPO_ROOT)
    allocated = {
        name: 50000 + index
        for index, name in enumerate(compose.required_port_names(declaration))
    }
    spec = yaml.safe_load(
        compose.render(
            repo_root=REPO_ROOT,
            declaration=declaration,
            names=names,
            ports=allocated,
            profile="standalone",
        )
    )
    # api and frontend are always present; broker/worker must not be.
    assert sorted(spec["services"]) == ["api", "frontend", "postgres"]
    assert "broker" not in spec["services"]
    assert "worker" not in spec["services"]


def test_a_module_declaring_a_worker_gets_a_broker():
    import yaml
    from harness import compose
    from harness.modules import load
    from harness.naming import ResourceNames

    declaration = load(REPO_ROOT, "M11")
    names = ResourceNames(module_id="M11", repo_root=REPO_ROOT)
    allocated = {
        name: 50000 + index
        for index, name in enumerate(compose.required_port_names(declaration))
    }
    spec = yaml.safe_load(
        compose.render(
            repo_root=REPO_ROOT,
            declaration=declaration,
            names=names,
            ports=allocated,
            profile="standalone",
        )
    )
    assert "broker" in spec["services"]
    assert "worker" in spec["services"]


@pytest.mark.parametrize("module_id", ["M00", "M11", "M12", "M14"])
def test_every_image_is_pinned_by_digest_and_bound_to_loopback(module_id):
    import yaml
    from harness import compose
    from harness.modules import load
    from harness.naming import ResourceNames

    declaration = load(REPO_ROOT, module_id)
    names = ResourceNames(module_id=module_id, repo_root=REPO_ROOT)
    allocated = {
        name: 50000 + index
        for index, name in enumerate(compose.required_port_names(declaration))
    }
    spec = yaml.safe_load(
        compose.render(
            repo_root=REPO_ROOT,
            declaration=declaration,
            names=names,
            ports=allocated,
            profile="standalone",
        )
    )
    for service, body in spec["services"].items():
        if "image" in body:
            assert "@sha256:" in body["image"], (module_id, service)
        else:
            # A built service pins its BASE image by digest through a build arg.
            args = body["build"]["args"]
            pinned = [value for value in args.values() if "@sha256:" in str(value)]
            assert pinned, (module_id, service, args)
        for mapping in body.get("ports", []):
            assert mapping.startswith("127.0.0.1:"), (module_id, service, mapping)


@pytest.mark.parametrize("module_id", ["M00", "M11", "M12", "M14"])
def test_no_secret_value_is_written_into_a_generated_compose_file(module_id, tmp_path):
    """Generated files live beside the checkout; a secret there is a secret on disk.

    The file must reference secrets as ${VAR} for Compose to interpolate from the
    environment, never embed the value.
    """
    from harness import compose
    from harness.modules import load
    from harness.naming import ResourceNames
    from harness.secrets import LocalSecrets

    real = LocalSecrets(repo_root=tmp_path, stem="probe").ensure()
    declaration = load(REPO_ROOT, module_id)
    names = ResourceNames(module_id=module_id, repo_root=REPO_ROOT)
    allocated = {
        name: 50000 + index
        for index, name in enumerate(compose.required_port_names(declaration))
    }
    text = compose.render(
        repo_root=REPO_ROOT,
        declaration=declaration,
        names=names,
        ports=allocated,
        profile="standalone",
    )
    for value in real.values():
        assert value not in text
    assert "${SESSION_SECRET}" in text
    assert "${TOTP_ENCRYPTION_KEY}" in text


@pytest.mark.parametrize("module_id", ["M00", "M11", "M12"])
def test_the_api_service_waits_for_a_healthy_database(module_id):
    import yaml
    from harness import compose
    from harness.modules import load
    from harness.naming import ResourceNames

    declaration = load(REPO_ROOT, module_id)
    names = ResourceNames(module_id=module_id, repo_root=REPO_ROOT)
    allocated = {
        name: 50000 + index
        for index, name in enumerate(compose.required_port_names(declaration))
    }
    spec = yaml.safe_load(
        compose.render(
            repo_root=REPO_ROOT,
            declaration=declaration,
            names=names,
            ports=allocated,
            profile="standalone",
        )
    )
    assert spec["services"]["api"]["depends_on"]["postgres"]["condition"] == "service_healthy"


def test_a_worker_module_never_configures_eager_execution():
    """Eager mode cannot demonstrate crash or retry behaviour."""
    celery = (REPO_ROOT / "backend" / "config" / "celery.py").read_text()
    assert "task_always_eager = False" in celery
    assert "task_always_eager = True" not in celery


def test_images_are_pinned_from_the_committed_record():
    from harness.compose import load_images

    images = load_images(REPO_ROOT)
    assert set(images) >= {"postgres", "redis", "python", "node", "minio"}
    for name, reference in images.items():
        assert reference.count("@sha256:") == 1, name
        assert len(reference.split("@sha256:")[1]) == 64, name


# --- ports and secrets ---------------------------------------------------


def test_allocated_ports_are_distinct_and_reused_across_calls(tmp_path):
    from harness.ports import PortAllocation

    allocation = PortAllocation(repo_root=tmp_path, stem="test_ns")
    first = allocation.allocate(("api", "frontend", "postgres"))
    assert len(set(first.values())) == 3
    assert allocation.allocate(("api", "frontend", "postgres")) == first


def test_clearing_an_allocation_does_not_touch_data(tmp_path):
    from harness.ports import PortAllocation

    allocation = PortAllocation(repo_root=tmp_path, stem="test_ns")
    allocation.allocate(("api",))
    assert allocation.path.exists()
    allocation.clear()
    assert not allocation.path.exists()


def test_generated_secrets_are_owner_only_and_stable(tmp_path):
    import stat

    from harness.secrets import GENERATED_NAMES, LocalSecrets

    store = LocalSecrets(repo_root=tmp_path, stem="test_ns")
    first = store.ensure()
    assert set(GENERATED_NAMES) <= set(first)
    mode = stat.S_IMODE(store.path.stat().st_mode)
    assert mode == 0o600, oct(mode)
    # Regenerating must not rotate: that would invalidate enrolled TOTP seeds.
    assert store.ensure() == first


def test_the_totp_key_is_fernet_shaped(tmp_path):
    import base64

    from harness.secrets import LocalSecrets

    values = LocalSecrets(repo_root=tmp_path, stem="test_ns").ensure()
    assert len(base64.urlsafe_b64decode(values["TOTP_ENCRYPTION_KEY"])) == 32


def test_secret_and_state_directories_are_git_ignored():
    ignore = (REPO_ROOT / ".gitignore").read_text()
    assert "dev/secrets/" in ignore
    assert "dev/evidence/" in ignore
    tracked = subprocess.run(
        ["git", "ls-files", "dev/secrets", "dev/state", "dev/evidence"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    ).stdout.strip()
    assert tracked == "", f"secrets or state are tracked: {tracked}"
