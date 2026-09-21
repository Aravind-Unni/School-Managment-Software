"""``manage.py install_school`` -- install or update this school's configuration.

Reads the defaults plus ``--config`` (or ``SCHOOL_CONFIG_FILE``) and writes the
configuration rows every module needs. Safe to re-run after every edit.
"""

from __future__ import annotations

import os
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Install school configuration from TOML."""

    help = "Install or update the school's configuration from its TOML config file."

    def add_arguments(self, parser) -> None:
        """Accept a config path and a dry-run flag."""
        parser.add_argument(
            "--config",
            default=os.environ.get("SCHOOL_CONFIG_FILE", ""),
            help="Path to the school's TOML file (merged over the built-in defaults).",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Validate the configuration and print it; write nothing.",
        )

    def handle(self, *args, **options) -> None:
        """Validate, then install in one transaction and print a summary."""
        from config.school_install import install_school, load_school_config

        try:
            config = load_school_config(options["config"] or None)
        except (ValueError, FileNotFoundError) as exc:
            raise CommandError(str(exc)) from exc
        source = options["config"] or "built-in defaults only"
        self.stdout.write(f"school config: {source}")
        self.stdout.write(
            f"school: {config['school']['name']} ({config['academic_year']['name']})"
        )
        if options["check"]:
            self.stdout.write(self.style.SUCCESS("configuration is valid (nothing written)"))
            return
        try:
            report = install_school(
                config,
                school_id=uuid.UUID(str(settings.SCHOOL_ID)),
                now=settings.SCHOOL_CLOCK.now(),
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        for label, counts in (("created", report.created), ("updated", report.updated)):
            if counts:
                summary = ", ".join(f"{kind}={count}" for kind, count in sorted(counts.items()))
                self.stdout.write(f"  {label}: {summary}")
        self.stdout.write(self.style.SUCCESS("school configuration installed"))
