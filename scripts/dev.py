#!/usr/bin/env python3
"""The one command interface for developing a module.

    python scripts/dev.py doctor
    python scripts/dev.py up      <ID> --profile standalone
    python scripts/dev.py migrate <ID> --profile standalone
    python scripts/dev.py seed    <ID> --scenario baseline
    python scripts/dev.py check   <ID> --suite standalone|contracts|browser
    python scripts/dev.py evidence <ID>
    python scripts/dev.py down    <ID>

STANDARD LIBRARY ONLY. This is a host launcher into pinned containers: it must
run on a fresh checkout, before any virtual environment exists, because
``doctor`` is the first thing a new developer runs.

Guarantees these commands make:
  * every command exits nonzero when it fails, and says what to do next
  * ``up`` prints the real allocated API and frontend URLs
  * ``seed`` refuses any target that is not a development database
  * ``down`` stops containers and NEVER deletes a volume
  * a command for a module with no code says so, rather than pretending
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "dev"))

from harness import compose, evidence, modules, naming, ports, secrets  # noqa: E402

#: Exit statuses, so callers and CI can distinguish causes.
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_PREREQUISITE_MISSING = 2
EXIT_NOT_IMPLEMENTED = 3
EXIT_REFUSED = 4

VALID_PROFILES = ("standalone", "integrated")
VALID_SUITES = ("standalone", "contracts", "browser")


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------


def say(message: str) -> None:
    """Print a normal progress line."""
    print(message)


def fail(message: str, *, hint: str = "") -> None:
    """Print a failure and an optional next step, to stderr."""
    print(f"FAIL: {message}", file=sys.stderr)
    if hint:
        for line in hint.splitlines():
            print(f"      {line}", file=sys.stderr)


def docker_command() -> list[str] | None:
    """Return a working ``compose`` invocation, or None if there is none.

    Prefers the ``docker compose`` plugin and falls back to the standalone
    ``docker-compose`` binary, because a developer may have either.
    """
    if shutil.which("docker"):
        probe = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
        if probe.returncode == 0:
            return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def dangling_docker_symlinks() -> list[str]:
    """Return paths that look like a docker CLI but point nowhere.

    Uninstalling Docker Desktop on macOS leaves /usr/local/bin/docker as a broken
    symlink into /Applications/Docker.app. ``shutil.which`` correctly ignores it,
    which makes the state baffling: the file is visibly there, yet every command
    reports "not found". Naming it explicitly saves a long detour.
    """
    found: list[str] = []
    for candidate in ("/usr/local/bin/docker", "/usr/local/bin/docker-compose"):
        path = pathlib.Path(candidate)
        if path.is_symlink() and not path.exists():
            found.append(f"{candidate} -> {os.readlink(candidate)}")
    return found


def docker_engine_state() -> tuple[str, str]:
    """Return (state, detail) describing the container engine.

    States, kept distinct because the remedy differs for each:
      * "ok"           -- a daemon answered
      * "no-cli"       -- no docker CLI on PATH at all
      * "no-daemon"    -- CLI present, daemon not answering
    A compose binary alone is NOT an engine: compose still needs a daemon to talk
    to, so reporting compose's presence as readiness would be a false green.
    """
    if not shutil.which("docker"):
        dangling = dangling_docker_symlinks()
        detail = "no docker CLI on PATH"
        if dangling:
            detail += "; broken leftover symlink(s): " + ", ".join(dangling)
        return "no-cli", detail
    probe = subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return "ok", probe.stdout.strip()
    return "no-daemon", (probe.stderr or probe.stdout).strip().splitlines()[0][:160]


def docker_daemon_running() -> bool:
    """Return whether a container engine is actually usable."""
    return docker_engine_state()[0] == "ok"


def venv_python() -> pathlib.Path | None:
    """Return the project virtual environment's interpreter, if present."""
    candidate = REPO_ROOT / ".venv" / "bin" / "python"
    return candidate if candidate.exists() else None


def resolve(module_id: str) -> modules.ModuleDeclaration:
    """Load a module declaration, exiting cleanly on a bad id."""
    try:
        return modules.load(REPO_ROOT, module_id)
    except modules.ModuleDeclarationError as error:
        fail(str(error))
        raise SystemExit(EXIT_PREREQUISITE_MISSING) from error


def context(module_id: str) -> tuple[modules.ModuleDeclaration, naming.ResourceNames]:
    """Return the declaration and namespaced names for a module."""
    declaration = resolve(module_id)
    return declaration, naming.ResourceNames(
        module_id=declaration.module_id, repo_root=REPO_ROOT
    )


def require_implemented(declaration: modules.ModuleDeclaration) -> None:
    """Exit with a clear message when the module has no code.

    This is the "fail honestly when code is absent" rule. Booting an empty Django
    app would look like success and waste a reviewer's time.
    """
    if declaration.implemented:
        return
    fail(
        f"{declaration.module_id} ({declaration.slug}) is not implemented: "
        f"backend/modules/{declaration.slug}/registration.py does not exist.",
        hint=(
            f"Read contracts/{declaration.module_id}/PACKET.md first. The contract "
            "is reviewed and frozen in contracts/manifest.json BEFORE any code.\n"
            "Only M00 (the placeholder) is implemented in the B00 foundation."
        ),
    )
    raise SystemExit(EXIT_NOT_IMPLEMENTED)


def compose_file_path(names: naming.ResourceNames) -> pathlib.Path:
    """Return where this namespace's generated Compose file lives."""
    return REPO_ROOT / "dev" / "state" / f"{names.stem}.compose.yaml"


def environment_for(
    declaration: modules.ModuleDeclaration,
    names: naming.ResourceNames,
    allocated: dict[str, int],
    *,
    profile: str,
) -> dict[str, str]:
    """Assemble the process environment for a host-run Django command.

    Secrets come from dev/secrets (outside Git); connection strings are derived
    from the namespace and the allocated ports. Only the variables the module
    actually needs are set, so an unused BROKER_URL cannot mislead.
    """
    local = secrets.LocalSecrets(repo_root=REPO_ROOT, stem=names.stem).ensure()
    settings_module = f"config.settings.{profile}"
    merged = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "backend"),
        "DJANGO_SETTINGS_MODULE": settings_module,
        "APP_ENV": profile,
        "MODULE_ID": declaration.module_id,
        "DATABASE_URL": compose.database_url(names, allocated),
        "SESSION_SECRET": local["SESSION_SECRET"],
        "TOTP_ENCRYPTION_KEY": local["TOTP_ENCRYPTION_KEY"],
        "DEV_PERSONA_MODE": "fixed",
    }
    if declaration.needs_broker:
        merged["BROKER_URL"] = compose.broker_url(allocated)
        merged["WORKER_AVAILABLE"] = "true" if declaration.needs_worker else "false"
    if declaration.needs_object_storage:
        merged["OBJECT_STORAGE_ENDPOINT"] = compose.object_storage_endpoint(allocated)
        merged["OBJECT_STORAGE_BUCKET"] = names.bucket
        merged["OBJECT_STORAGE_ACCESS_KEY"] = compose.LOCAL_MINIO_USER
        merged["OBJECT_STORAGE_SECRET_KEY"] = local["OBJECT_STORAGE_SECRET_KEY"]
    return merged


def run_django(
    arguments: list[str],
    *,
    declaration: modules.ModuleDeclaration,
    names: naming.ResourceNames,
    allocated: dict[str, int],
    profile: str,
) -> int:
    """Run a Django management command in the module's environment.

    Returns the child's exit status. Requires the project virtual environment:
    running Django from the system interpreter would ignore the committed
    lockfiles and make a result unreproducible.
    """
    interpreter = venv_python()
    if interpreter is None:
        fail(
            "the project virtual environment is missing (.venv/bin/python).",
            hint=(
                "uv venv --python 3.12 .venv\n"
                "VIRTUAL_ENV=.venv uv pip install -r backend/requirements.txt "
                "-r backend/requirements-dev.txt"
            ),
        )
        return EXIT_PREREQUISITE_MISSING
    return subprocess.run(
        [str(interpreter), "backend/manage.py", *arguments],
        cwd=REPO_ROOT,
        env=environment_for(declaration, names, allocated, profile=profile),
    ).returncode


# --------------------------------------------------------------------------
# doctor
# --------------------------------------------------------------------------


def command_doctor(_arguments: argparse.Namespace) -> int:
    """Report whether this machine can run the stack, and what is missing.

    Prints a redacted configuration view: secrets appear as <set>/<unset> and a
    DSN keeps its host and database but loses its password.

    Exits nonzero when a hard prerequisite is absent, so CI can gate on it.
    """
    say("school platform -- doctor")
    say("")

    problems: list[str] = []
    warnings: list[str] = []

    say("toolchain")
    interpreter = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    supported = sys.version_info >= (3, 12)
    say(f"  python           {interpreter} {'ok' if supported else 'TOO OLD (need >= 3.12)'}")
    if not supported:
        problems.append("Python 3.12 or newer is required.")

    composer = docker_command()
    if composer is None:
        say("  docker compose   MISSING")
    else:
        version = subprocess.run(
            [*composer, "version", "--short"], capture_output=True, text=True
        ).stdout.strip()
        say(f"  docker compose   {version or 'present'} ({' '.join(composer)})")

    state, detail = docker_engine_state()
    if state == "ok":
        say(f"  container engine running (server {detail})")
    elif state == "no-daemon":
        say("  container engine CLI present, DAEMON NOT RESPONDING")
        say(f"                   {detail}")
        problems.append(
            "The docker CLI is installed but no daemon is responding. Start Docker "
            "Desktop (or your engine) and re-run doctor."
        )
    else:
        say("  container engine NOT INSTALLED")
        say(f"                   {detail}")
        problems.append(
            "No container engine is installed. Docker Compose is this project's "
            "development runner, and compose alone cannot start anything without "
            "a daemon: install Docker Desktop, colima, or another engine."
        )

    node = shutil.which("node")
    if node:
        version = subprocess.run(
            [node, "--version"], capture_output=True, text=True
        ).stdout.strip()
        say(f"  node             {version}")
        numeric = version.lstrip("v").split(".")
        if numeric and numeric[0].isdigit() and int(numeric[0]) < 20:
            warnings.append(
                f"Node {version} is older than the container's; CI is authoritative."
            )
    else:
        say("  node             MISSING")
        warnings.append("Node is absent; frontend checks cannot run on the host.")

    interpreter_path = venv_python()
    say(f"  .venv            {'present' if interpreter_path else 'MISSING'}")
    if interpreter_path is None:
        problems.append("Create .venv and install from the committed lockfiles.")

    say("")
    say("repository")
    for relative in (
        "backend/requirements.txt",
        "backend/requirements-dev.txt",
        "contracts/manifest.json",
        "infra/images.json",
        ".env.example",
    ):
        present = (REPO_ROOT / relative).exists()
        say(f"  {relative:32} {'ok' if present else 'MISSING'}")
        if not present:
            problems.append(f"{relative} is missing.")

    say(f"  branch                           {naming.git_branch(REPO_ROOT)}")
    say(f"  developer                        {naming.developer()}")
    say(f"  worktree                         {naming.worktree_label(REPO_ROOT)}")

    say("")
    say("modules")
    for module_id in sorted(modules.KNOWN_MODULE_IDS):
        try:
            declaration = modules.load(REPO_ROOT, module_id)
        except modules.ModuleDeclarationError as error:
            say(f"  {module_id}  declaration error: {error}")
            problems.append(f"{module_id} declaration is invalid.")
            continue
        state = "implemented" if declaration.implemented else "not implemented"
        say(f"  {module_id} {declaration.slug:16} {state:16} {sorted(declaration.resources)}")

    say("")
    say("configuration (redacted -- no secret value is ever printed)")
    for name, value in _redacted_environment().items():
        say(f"  {name:28} {value}")

    say("")
    if warnings:
        for warning in warnings:
            say(f"warning: {warning}")
    if problems:
        say("")
        fail(f"{len(problems)} prerequisite problem(s)")
        for problem in problems:
            print(f"      - {problem}", file=sys.stderr)
        return EXIT_PREREQUISITE_MISSING

    say("OK: this machine can run the stack.")
    return EXIT_OK


def _redacted_environment() -> dict[str, str]:
    """Return the documented variables, redacted, without importing the backend.

    Reimplements redaction rather than importing ``config.env`` because doctor
    must work with no virtual environment. The two implementations are kept in
    step by tests/integration/test_dev_cli.py.
    """
    secret_names = {
        "SESSION_SECRET",
        "TOTP_ENCRYPTION_KEY",
        "OBJECT_STORAGE_SECRET_KEY",
        "OBJECT_STORAGE_ACCESS_KEY",
    }
    dsn_names = {"DATABASE_URL", "BROKER_URL"}
    documented = (
        "APP_ENV",
        "MODULE_ID",
        "SCHOOL_ID",
        "DATABASE_URL",
        "BROKER_URL",
        "OBJECT_STORAGE_ENDPOINT",
        "OBJECT_STORAGE_BUCKET",
        "OBJECT_STORAGE_ACCESS_KEY",
        "OBJECT_STORAGE_SECRET_KEY",
        "SESSION_SECRET",
        "TOTP_ENCRYPTION_KEY",
        "DEV_PERSONA_MODE",
    )
    view: dict[str, str] = {}
    for name in documented:
        raw = os.environ.get(name, "")
        if not raw:
            view[name] = "<unset>"
        elif name in secret_names:
            view[name] = "<set>"
        elif name in dsn_names:
            from urllib.parse import urlparse

            parsed = urlparse(raw)
            if parsed.password:
                host = parsed.hostname or ""
                port = f":{parsed.port}" if parsed.port else ""
                view[name] = (
                    f"{parsed.scheme}://{parsed.username}:<redacted>@{host}{port}{parsed.path}"
                )
            else:
                view[name] = raw
        else:
            view[name] = raw
    return view


# --------------------------------------------------------------------------
# up / down
# --------------------------------------------------------------------------


def command_up(arguments: argparse.Namespace) -> int:
    """Start the module's stack and print the real allocated URLs.

    Starts ONLY the containers the module declared. Host ports are allocated
    dynamically and reused across restarts, so a bookmarked URL keeps working.
    """
    declaration, names = context(arguments.module_id)
    require_implemented(declaration)

    composer = docker_command()
    if composer is None:
        fail(
            "Docker Compose is not available, so no stack can be started.",
            hint=(
                "Docker Compose is the development runner for this project.\n"
                "Install Docker Desktop (or the compose plugin), then re-run:\n"
                "  python scripts/dev.py doctor"
            ),
        )
        return EXIT_PREREQUISITE_MISSING
    if not docker_daemon_running():
        fail("the Docker daemon is not running.", hint="Start Docker, then re-run.")
        return EXIT_PREREQUISITE_MISSING

    allocation = ports.PortAllocation(repo_root=REPO_ROOT, stem=names.stem)
    allocated = allocation.allocate(compose.required_port_names(declaration))

    compose_text = compose.render(
        repo_root=REPO_ROOT,
        declaration=declaration,
        names=names,
        ports=allocated,
        profile=arguments.profile,
    )
    target = compose_file_path(names)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(compose_text)

    # Secrets are generated before compose runs: the generated file references
    # them as ${VAR} rather than embedding them, so they must be in the
    # environment for interpolation.
    local = secrets.LocalSecrets(repo_root=REPO_ROOT, stem=names.stem)
    generated = local.ensure()

    say(f"starting {declaration.module_id} ({declaration.slug}) -- profile {arguments.profile}")
    say(f"  project   {names.compose_project}")
    say(f"  database  {names.database}")
    containers = sorted(declaration.resources - {"frontend"})
    say(f"  services  {containers}")
    say("")

    result = subprocess.run(
        [*composer, "-f", str(target), "up", "-d", "--build", "--wait"],
        cwd=REPO_ROOT,
        env={**os.environ, **generated},
    )
    if result.returncode != 0:
        fail(
            "Compose failed to bring the stack up.",
            hint=(
                f"Inspect it with:\n  docker compose -f {target.relative_to(REPO_ROOT)} ps\n"
                f"  docker compose -f {target.relative_to(REPO_ROOT)} logs\n"
                "A port conflict is the usual cause; `down` then `up` reallocates."
            ),
        )
        return EXIT_FAILED

    say("")
    say("stack is up.")
    say(f"  API        http://127.0.0.1:{allocated['api']}")
    say(f"  API schema http://127.0.0.1:{allocated['api']}/api/schema/")
    say(f"  health     http://127.0.0.1:{allocated['api']}/healthz")
    say(f"  readiness  http://127.0.0.1:{allocated['api']}/readyz")
    if declaration.needs_frontend:
        say(f"  frontend   http://127.0.0.1:{allocated['frontend']}")
    say(f"  postgres   127.0.0.1:{allocated['postgres']} (db {names.database})")
    if declaration.needs_broker:
        say(f"  broker     127.0.0.1:{allocated['broker']}")
    if declaration.needs_object_storage:
        storage_url = f"http://127.0.0.1:{allocated['object_storage']}"
        say(f"  storage    {storage_url} (bucket {names.bucket})")
        say(f"  storage ui http://127.0.0.1:{allocated['object_storage_console']}")
    say(f"  secrets    {local.path.relative_to(REPO_ROOT)} (not in Git)")
    say("")
    say("next:")
    say(
        f"  python scripts/dev.py migrate {declaration.module_id} --profile {arguments.profile}"
    )
    say(f"  python scripts/dev.py seed {declaration.module_id} --scenario baseline")
    say(f"  python scripts/dev.py check {declaration.module_id} --suite standalone")
    return EXIT_OK


def command_down(arguments: argparse.Namespace) -> int:
    """Stop the module's containers. NEVER deletes a volume.

    Data survives on purpose: a developer who has seeded and hand-explored a
    stack must not lose it to a routine stop. Removing data is a separate,
    explicit act (``docker volume rm``), and the command says so.
    """
    declaration, names = context(arguments.module_id)
    composer = docker_command()
    if composer is None:
        fail("Docker Compose is not available.", hint="Nothing to stop.")
        return EXIT_PREREQUISITE_MISSING

    target = compose_file_path(names)
    if not target.exists():
        say(f"no generated Compose file for {names.stem}; nothing to stop.")
        return EXIT_OK

    # No --volumes flag, deliberately.
    result = subprocess.run(
        [*composer, "-f", str(target), "down", "--remove-orphans"],
        cwd=REPO_ROOT,
    )
    ports.PortAllocation(repo_root=REPO_ROOT, stem=names.stem).clear()

    say("")
    say(f"stopped {declaration.module_id}. Volumes were NOT deleted:")
    say(f"  {names.volume_prefix}_postgres")
    if declaration.needs_object_storage:
        say(f"  {names.volume_prefix}_objects")
    say("To discard the data explicitly:")
    say(f"  docker volume rm {names.volume_prefix}_postgres")
    return EXIT_OK if result.returncode == 0 else EXIT_FAILED


# --------------------------------------------------------------------------
# migrate / seed
# --------------------------------------------------------------------------


def command_migrate(arguments: argparse.Namespace) -> int:
    """Apply the module's real migrations to its isolated database."""
    declaration, names = context(arguments.module_id)
    require_implemented(declaration)

    allocated = ports.PortAllocation(repo_root=REPO_ROOT, stem=names.stem).load()
    if "postgres" not in allocated:
        fail(
            "no running stack for this module.",
            hint=(
                f"python scripts/dev.py up {declaration.module_id} "
                f"--profile {arguments.profile}"
            ),
        )
        return EXIT_PREREQUISITE_MISSING

    say(f"applying migrations for {declaration.module_id} to {names.database}")
    status = run_django(
        ["migrate", "--noinput"],
        declaration=declaration,
        names=names,
        allocated=allocated,
        profile=arguments.profile,
    )
    if status != 0:
        fail("migrations failed.")
        return EXIT_FAILED
    say("OK: migrations applied.")
    return EXIT_OK


def command_seed(arguments: argparse.Namespace) -> int:
    """Load a named synthetic scenario. Refuses a non-development target.

    Three independent refusals, because seeding a real school's database with
    synthetic students would be unrecoverable:
      1. the profile must not be production
      2. the database name must carry this harness's namespace prefix
      3. the host must be loopback
    """
    declaration, names = context(arguments.module_id)
    require_implemented(declaration)

    if arguments.scenario not in declaration.seed_scenarios:
        fail(
            f"unknown scenario {arguments.scenario!r} for {declaration.module_id}.",
            hint=f"declared scenarios: {list(declaration.seed_scenarios)}",
        )
        return EXIT_REFUSED

    allocated = ports.PortAllocation(repo_root=REPO_ROOT, stem=names.stem).load()
    if "postgres" not in allocated:
        fail(
            "no running stack for this module.",
            hint=f"python scripts/dev.py up {declaration.module_id}",
        )
        return EXIT_PREREQUISITE_MISSING

    target_dsn = compose.database_url(names, allocated)
    refusal = refuse_non_development_target(target_dsn, names)
    if refusal:
        fail(f"refusing to seed: {refusal}", hint="Seeding is for development databases only.")
        return EXIT_REFUSED

    say(
        f"seeding {declaration.module_id} scenario {arguments.scenario!r} into {names.database}"
    )
    status = run_django(
        ["seed_scenario", "--scenario", arguments.scenario],
        declaration=declaration,
        names=names,
        allocated=allocated,
        profile="standalone",
    )
    if status != 0:
        fail("seeding failed.")
        return EXIT_FAILED
    say("OK: scenario loaded.")
    return EXIT_OK


def refuse_non_development_target(dsn: str, names: naming.ResourceNames) -> str:
    """Return a refusal reason for a non-development target, or "" if safe.

    Exposed as a function so tests can assert each refusal independently rather
    than needing a live database.
    """
    from urllib.parse import urlparse

    if os.environ.get("APP_ENV") == "production":
        return "APP_ENV is production"
    parsed = urlparse(dsn)
    database = (parsed.path or "").lstrip("/")
    if not database.startswith("school_"):
        return f"database {database!r} is not a harness-created development database"
    if database != names.database:
        return f"database {database!r} does not match this namespace ({names.database!r})"
    if (parsed.hostname or "") not in ("127.0.0.1", "localhost", "::1"):
        return f"host {parsed.hostname!r} is not loopback"
    return ""


# --------------------------------------------------------------------------
# check / evidence
# --------------------------------------------------------------------------


def command_check(arguments: argparse.Namespace) -> int:
    """Run one suite and write a machine-readable report.

    Exits nonzero when the suite fails. A suite that cannot run because a
    prerequisite is absent is recorded as NOT RUN, never as passing -- that
    distinction is the whole point of the report's ``backend`` field.
    """
    declaration, names = context(arguments.module_id)
    suite = arguments.suite

    if suite == "contracts":
        return _check_contracts(declaration, names)
    if suite == "standalone":
        return _check_standalone(declaration, names, arguments.profile)
    if suite == "browser":
        return _check_browser(declaration, names)
    fail(f"unknown suite {suite!r}", hint=f"valid suites: {list(VALID_SUITES)}")
    return EXIT_REFUSED


def _check_contracts(declaration, names) -> int:
    """Run the contract suite: schema drift, architecture, frozen interfaces.

    Needs no database and no containers, so it always runs and is the fastest
    signal that something structural broke.
    """
    say(f"check {declaration.module_id} -- suite contracts")
    steps: list[tuple[str, list[str]]] = [
        ("contract manifest", [sys.executable, "scripts/contract_manifest.py", "--check"]),
        ("architecture", [sys.executable, "scripts/arch_check.py"]),
    ]
    interpreter = venv_python()
    if interpreter is not None:
        steps.append(
            (
                "contract tests",
                [str(interpreter), "-m", "pytest", "tests/contracts", "-q"],
            )
        )

    outcomes: dict[str, object] = {}
    ok = True
    for label, command in steps:
        say(f"  {label} ...")
        status = subprocess.run(command, cwd=REPO_ROOT).returncode
        outcomes[label] = "passed" if status == 0 else f"failed (exit {status})"
        ok = ok and status == 0
    if interpreter is None:
        outcomes["contract tests"] = "not run (.venv missing)"
        ok = False

    path = evidence.write_report(
        repo_root=REPO_ROOT,
        stem=names.stem,
        suite="contracts",
        module_id=declaration.module_id,
        passed=ok,
        backend="no-database-required",
        details=outcomes,
    )
    say(f"  report {path.relative_to(REPO_ROOT)}")
    return EXIT_OK if ok else EXIT_FAILED


def _check_standalone(declaration, names, profile: str) -> int:
    """Run the module's unit and API suite against its real PostgreSQL database.

    Requires a running stack. Without one the report records ``not-run`` with the
    reason, rather than silently falling back to SQLite and producing a result
    that looks equivalent but is not.
    """
    say(f"check {declaration.module_id} -- suite standalone")
    require_implemented(declaration)

    allocated = ports.PortAllocation(repo_root=REPO_ROOT, stem=names.stem).load()
    interpreter = venv_python()

    if "postgres" not in allocated or interpreter is None:
        reason = (
            "no running stack; start it with dev.py up"
            if "postgres" not in allocated
            else "the project virtual environment is missing"
        )
        evidence.write_report(
            repo_root=REPO_ROOT,
            stem=names.stem,
            suite="standalone",
            module_id=declaration.module_id,
            passed=False,
            backend="not-run",
            details={"reason": reason},
        )
        fail(
            f"standalone suite did not run: {reason}.",
            hint=(
                "This suite asserts PostgreSQL behaviour and must not be replaced "
                "by the local SQLite profile.\n"
                f"  python scripts/dev.py up {declaration.module_id}"
            ),
        )
        return EXIT_PREREQUISITE_MISSING

    report_json = REPO_ROOT / "dev" / "state" / f"{names.stem}.pytest.json"
    status = subprocess.run(
        [
            str(interpreter),
            "-m",
            "pytest",
            "tests",
            "-q",
            # Both flags are required: --json-report-file on its own writes
            # nothing, which would leave "machine-readable results" quietly
            # unmet while the suite still looked green.
            "--json-report",
            f"--json-report-file={report_json}",
        ],
        cwd=REPO_ROOT,
        env=environment_for(declaration, names, allocated, profile=profile),
    ).returncode

    summary: dict[str, object] = {"pytest_exit": status}
    if report_json.exists():
        try:
            data = json.loads(report_json.read_text())
            summary["totals"] = data.get("summary", {})
        except ValueError:
            summary["totals"] = "unreadable report"

    path = evidence.write_report(
        repo_root=REPO_ROOT,
        stem=names.stem,
        suite="standalone",
        module_id=declaration.module_id,
        passed=status == 0,
        backend="postgres-container",
        details=summary,
    )
    say(f"  report {path.relative_to(REPO_ROOT)}")
    return EXIT_OK if status == 0 else EXIT_FAILED


def _check_browser(declaration, names) -> int:
    """Run the Playwright browser suite against the running stack.

    Records ``not-run`` when the frontend dependencies or a running stack are
    absent. Claiming browser coverage without a browser is exactly the kind of
    false green this command exists to prevent.
    """
    say(f"check {declaration.module_id} -- suite browser")
    frontend = REPO_ROOT / "frontend"
    allocated = ports.PortAllocation(repo_root=REPO_ROOT, stem=names.stem).load()

    missing: list[str] = []
    if not (frontend / "node_modules").exists():
        missing.append("frontend/node_modules (run: npm ci --prefix frontend)")
    if "frontend" not in allocated:
        missing.append(
            f"a running stack (run: python scripts/dev.py up {declaration.module_id})"
        )
    if shutil.which("node") is None:
        missing.append("node")

    if missing:
        evidence.write_report(
            repo_root=REPO_ROOT,
            stem=names.stem,
            suite="browser",
            module_id=declaration.module_id,
            passed=False,
            backend="not-run",
            details={"missing": missing},
        )
        fail("browser suite did not run.", hint="missing:\n  - " + "\n  - ".join(missing))
        return EXIT_PREREQUISITE_MISSING

    status = subprocess.run(
        ["npm", "run", "test:browser"],
        cwd=frontend,
        env={
            **os.environ,
            "SCHOOL_API_URL": f"http://127.0.0.1:{allocated['api']}",
            "SCHOOL_FRONTEND_URL": f"http://127.0.0.1:{allocated['frontend']}",
        },
    ).returncode

    path = evidence.write_report(
        repo_root=REPO_ROOT,
        stem=names.stem,
        suite="browser",
        module_id=declaration.module_id,
        passed=status == 0,
        backend="playwright-chromium",
        details={"npm_exit": status},
    )
    say(f"  report {path.relative_to(REPO_ROOT)}")
    return EXIT_OK if status == 0 else EXIT_FAILED


def command_evidence(arguments: argparse.Namespace) -> int:
    """Collect every suite report for a module into one reviewable bundle.

    Exits nonzero when any suite did not pass, so ``evidence`` can gate a review
    rather than merely describing one.
    """
    declaration, names = context(arguments.module_id)
    bundle = evidence.collect_bundle(REPO_ROOT, names.stem, declaration.module_id)
    target = REPO_ROOT / evidence.EVIDENCE_DIRNAME / names.stem / "bundle.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")

    say(f"evidence for {declaration.module_id} ({names.stem})")
    say(f"  commit {bundle['source']['commit'][:12]} dirty={bundle['source']['dirty']}")
    for suite, report in bundle["suites"].items():
        verdict = "PASS" if report.get("passed") else "FAIL"
        say(f"  {suite:12} {verdict:4} backend={report.get('backend')}")
    say(f"  bundle {target.relative_to(REPO_ROOT)}")

    if not bundle["all_suites_passed"]:
        fail("not every suite passed; this module is not ready for review.")
        return EXIT_FAILED
    return EXIT_OK


# --------------------------------------------------------------------------
# entrypoint
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Return the CLI parser for every command."""
    parser = argparse.ArgumentParser(
        prog="dev.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="check prerequisites and print redacted config")

    def with_module(name: str, help_text: str) -> argparse.ArgumentParser:
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("module_id", metavar="ID", help="module id, M00..M14")
        return sub

    for name, help_text in (
        ("up", "start the module's declared containers and print URLs"),
        ("migrate", "apply the module's real migrations"),
    ):
        sub = with_module(name, help_text)
        sub.add_argument("--profile", choices=VALID_PROFILES, default="standalone")

    seed = with_module("seed", "load a named synthetic scenario")
    seed.add_argument("--scenario", required=True)

    check = with_module("check", "run a suite and write a machine-readable report")
    check.add_argument("--suite", choices=VALID_SUITES, required=True)
    check.add_argument("--profile", choices=VALID_PROFILES, default="standalone")

    with_module("evidence", "collect suite reports into one bundle")
    with_module("down", "stop containers; never deletes a volume")
    return parser


COMMANDS = {
    "doctor": command_doctor,
    "up": command_up,
    "migrate": command_migrate,
    "seed": command_seed,
    "check": command_check,
    "evidence": command_evidence,
    "down": command_down,
}


def main() -> int:
    """Dispatch to the requested command."""
    arguments = build_parser().parse_args()
    return COMMANDS[arguments.command](arguments)


if __name__ == "__main__":
    raise SystemExit(main())
