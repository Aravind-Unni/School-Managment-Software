"""Loads a named synthetic scenario into a development database.

Delegates to the target module's ``seeds.py``, so the harness never knows a
module's domain. ``scripts/dev.py seed`` already refuses a non-development
target; this command refuses again independently, because a developer running
``manage.py seed_scenario`` directly bypasses the CLI's checks entirely.

Does not handle: idempotency across scenarios. Each scenario is responsible for
being safe to re-run, and the demo's are.
"""

from __future__ import annotations

import importlib

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shared.module_catalog import address_for


class Command(BaseCommand):
    """``manage.py seed_scenario --scenario <name>``."""

    help = "Load a named synthetic scenario for the module selected by MODULE_ID."

    def add_arguments(self, parser) -> None:
        """Declare the --scenario argument."""
        parser.add_argument("--scenario", required=True, help="scenario name")

    def handle(self, *args, **options) -> None:
        """Refuse unsafe targets, then load the scenario in one transaction.

        Three independent refusals: a production profile, a database whose name
        does not look harness-created, and a non-loopback host. Any one of them
        aborts before a single row is written.
        """
        self._refuse_unsafe_target()

        scenario = options["scenario"]
        address = address_for(settings.MODULE_ID)
        try:
            seeds = importlib.import_module(f"{address.django_app}.seeds")
        except ModuleNotFoundError as exc:
            raise CommandError(
                f"{address.id} ({address.slug}) has no seeds module at "
                f"{address.django_app}.seeds; nothing to seed."
            ) from exc

        available = getattr(seeds, "SCENARIOS", {})
        if scenario not in available:
            raise CommandError(
                f"unknown scenario {scenario!r}; {address.id} declares {sorted(available)}"
            )

        with transaction.atomic():
            summary = available[scenario]()

        self.stdout.write(f"loaded scenario {scenario!r} for {address.id}")
        for label, count in sorted(summary.items()):
            self.stdout.write(f"  {label}: {count}")

    def _refuse_unsafe_target(self) -> None:
        """Abort unless this is unmistakably a local development database."""
        if getattr(settings, "APP_ENV", "") == "production":
            raise CommandError(
                "refusing to seed: APP_ENV is production. Synthetic students must "
                "never reach a real school's database."
            )
        if not getattr(settings, "DEMO_FIXTURES_ENABLED", False):
            raise CommandError(
                "refusing to seed: DEMO_FIXTURES_ENABLED is false for this profile."
            )

        database = settings.DATABASES["default"]
        name = str(database.get("NAME", ""))
        engine = str(database.get("ENGINE", ""))

        if engine.endswith("sqlite3"):
            # The local test profile uses an in-memory database; seeding it from
            # the CLI is pointless but harmless, so allow it and say so.
            self.stdout.write("note: target is SQLite (local test profile)")
            return

        if not name.startswith("school_"):
            raise CommandError(
                f"refusing to seed: database {name!r} was not created by this "
                "harness (expected a 'school_<developer>_<worktree>_<module>' name)."
            )
        host = str(database.get("HOST", ""))
        if host not in ("127.0.0.1", "localhost", "::1", ""):
            raise CommandError(f"refusing to seed: host {host!r} is not loopback.")
