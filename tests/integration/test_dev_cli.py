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


def test_implemented_modules_are_exactly_those_with_a_registration():
    """Implementation status is derived from registration.py, never declared.

    M00 (placeholder), M01 (access), M02 (registry), M03 (timetable), M04
    (attendance), M05 (assessment), M06 (performance), M07 (fees), M08
    (transport), M09 (library) and M10 (alumni) are implemented. Everything
    else must report not-implemented so `dev.py up` fails honestly rather than
    booting an empty app.
    """
    from harness.modules import KNOWN_MODULE_IDS, load

    implemented = [
        module_id for module_id in KNOWN_MODULE_IDS if load(REPO_ROOT, module_id).implemented
    ]
    assert implemented == [
        "M00",
        "M01",
        "M02",
        "M03",
        "M04",
        "M05",
        "M06",
        "M07",
        "M08",
        "M09",
        "M10",
    ]


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
    result = run_dev("up", "M11")
    assert result.returncode == 3
    assert "not implemented" in result.stderr
    assert "contracts/M11/PACKET.md" in result.stderr


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


def test_the_standalone_check_requests_a_machine_readable_report():
    """Regression: --json-report-file alone writes nothing.

    pytest-json-report only activates on --json-report; passing only the file
    path silently produces no report, which would leave "unit/API tests produce
    machine-readable results" unmet while the suite still looked green.
    """
    source = DEV_PY.read_text()
    assert '"--json-report"' in source
    assert "--json-report-file=" in source


def test_the_ci_workflow_also_requests_the_report():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "--json-report --json-report-file=" in workflow


def test_the_ci_workflow_installs_with_require_hashes():
    """The claim of repeatable installation from lockfiles must be literal."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "--require-hashes" in workflow
    assert "npm ci" in workflow


def test_the_ci_workflow_asserts_the_guards_reject_violations():
    """CI must prove rejection, not merely run the checkers on clean code."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "a cross-module import is rejected" in workflow
    assert "a fake adapter in the production config is rejected" in workflow
    assert "contract schema drift is rejected" in workflow


def test_the_ci_workflow_runs_the_suite_against_real_postgres():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "postgres:17.11-alpine" in workflow
    assert "--ds=config.settings.standalone" in workflow


# --- namespace collision regressions --------------------------------------
#
# CI caught a real collision that passed locally: with a long checkout path the
# joined namespace was truncated to a fixed length, chopping the module id off the
# end, so M00 and M04 received the SAME database and Compose project. A short
# local path hid it. These tests pin every part of the fix.


@pytest.mark.parametrize(
    ("developer_name", "checkout_path"),
    [
        ("runner", "/home/runner/work/School-Managment-Software/School-Managment-Software"),
        ("abnvm", "/Users/abnvm/Downloads/aumspro"),
        ("a-very-long-developer-name-that-overflows", "/tmp/an-extremely-long-worktree-dir"),
        ("x", "/a"),
        ("Developer.With-Dots_And-Dashes", "/srv/Some Repo With Spaces"),
    ],
)
def test_every_module_gets_a_distinct_namespace(monkeypatch, developer_name, checkout_path):
    from harness.naming import ResourceNames

    monkeypatch.setenv("SCHOOL_DEV_NAME", developer_name)
    root = pathlib.Path(checkout_path)
    for attribute in ("compose_project", "database", "bucket", "queue", "volume_prefix"):
        values = {
            getattr(ResourceNames(module_id=f"M{index:02d}", repo_root=root), attribute)
            for index in range(0, 15)
        }
        assert len(values) == 15, f"{attribute} collided for {developer_name}"


@pytest.mark.parametrize(
    "checkout_path",
    [
        "/home/runner/work/School-Managment-Software/School-Managment-Software",
        "/tmp/an-extremely-long-worktree-directory-name-goes-right-here",
    ],
)
def test_the_module_id_always_survives_namespacing(monkeypatch, checkout_path):
    from harness.naming import ResourceNames

    monkeypatch.setenv("SCHOOL_DEV_NAME", "a-very-long-developer-name-that-overflows")
    for index in range(0, 15):
        module_id = f"M{index:02d}"
        names = ResourceNames(module_id=module_id, repo_root=pathlib.Path(checkout_path))
        assert names.stem.endswith(module_id.lower()), names.stem


def test_the_worktree_hash_always_survives_namespacing(monkeypatch):
    """Two worktrees sharing a directory name differ only by the hash."""
    from harness.naming import ResourceNames

    monkeypatch.setenv("SCHOOL_DEV_NAME", "a-very-long-developer-name-that-overflows")
    first = ResourceNames(
        module_id="M14", repo_root=pathlib.Path("/home/dev/one/School-Managment-Software")
    )
    second = ResourceNames(
        module_id="M14", repo_root=pathlib.Path("/home/dev/two/School-Managment-Software")
    )
    assert first.database != second.database


@pytest.mark.parametrize(
    "developer_name",
    ["runner", "abnvm", "a-very-long-developer-name-that-overflows", "ci"],
)
def test_every_derived_name_fits_postgres_identifier_limits(monkeypatch, developer_name):
    from harness.naming import ResourceNames

    monkeypatch.setenv("SCHOOL_DEV_NAME", developer_name)
    root = pathlib.Path("/home/runner/work/School-Managment-Software/School-Managment-Software")
    for index in range(0, 15):
        names = ResourceNames(module_id=f"M{index:02d}", repo_root=root)
        # The longest identifier actually created is the postgres volume name.
        assert len(f"{names.volume_prefix}_postgres") <= 63
        assert len(names.database) <= 63


def test_an_over_budget_namespace_raises_rather_than_colliding(monkeypatch):
    """Refusing to start beats two stacks silently sharing one database."""
    from harness import naming

    monkeypatch.setattr(naming, "MAX_STEM_LENGTH", 8)
    monkeypatch.setenv("SCHOOL_DEV_NAME", "developer")
    names = naming.ResourceNames(module_id="M04", repo_root=pathlib.Path("/tmp/some-repo"))
    with pytest.raises(ValueError, match="over the 8 budget"):
        _ = names.stem


# --- interpreter resolution regression ------------------------------------


def test_the_suites_resolve_an_interpreter_without_a_venv():
    """CI installs from the lockfiles into the runner's Python, not into .venv.

    Without a fallback, `check --suite contracts` reported the contract tests as
    "not run" on every CI machine, which failed the build for the wrong reason.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("dev_cli_interp", DEV_PY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    resolved = module.test_interpreter()
    assert resolved is not None
    # Whatever it picked must actually be able to run pytest.
    assert (
        subprocess.run([str(resolved), "-c", "import pytest"], capture_output=True).returncode
        == 0
    )


def test_compose_relative_paths_resolve_from_the_compose_files_own_directory():
    """Regression: Compose resolves relative paths against the FILE's directory.

    The generated file lives at dev/state/<stem>.compose.yaml, two levels below the
    root, so a build context of ".." pointed at dev/ and the first real Compose run
    failed with `lstat .../dev/infra: no such file or directory`. YAML validation
    cannot catch this; only actually building can. This asserts every path a
    generated file references resolves to something that exists.
    """
    import yaml
    from harness import compose
    from harness.modules import KNOWN_MODULE_IDS, load
    from harness.naming import ResourceNames

    # The constant must match the file's real depth below the repo root.
    compose_dir = (REPO_ROOT / "dev" / "state").resolve()
    depth = len(compose_dir.relative_to(REPO_ROOT).parts)
    assert compose.REPO_ROOT_FROM_COMPOSE == "/".join([".."] * depth)

    for module_id in KNOWN_MODULE_IDS:
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
            build = body.get("build")
            if build:
                context = (compose_dir / build["context"]).resolve()
                assert context.is_dir(), (module_id, service, build["context"])
                dockerfile = (context / build["dockerfile"]).resolve()
                assert dockerfile.is_file(), (module_id, service, build["dockerfile"])
            for mount in body.get("volumes", []):
                source = mount.split(":")[0]
                # Named volumes have no path separator; only bind mounts do.
                if source.startswith("."):
                    resolved = (compose_dir / source).resolve()
                    assert resolved.exists(), (module_id, service, source)
