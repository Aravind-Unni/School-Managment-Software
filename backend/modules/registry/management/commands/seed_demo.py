"""``manage.py seed_demo`` -- fill an empty trial school with synthetic data.

About 100 students in Std 6-9, their parents, 5 teachers, a principal, an
accountant and a librarian, a published timetable, three weeks of attendance,
published Unit Test 1 marks, fees with payments, library loans and notices.
Refuses unless ALLOW_DEMO_DATA=true and the school has no students.
"""

from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Seed demo data through the product's own API."""

    help = "Fill an empty trial school with synthetic demo data (ALLOW_DEMO_DATA=true)."

    def add_arguments(self, parser) -> None:
        """Accept the owner to act as and the random seed."""
        parser.add_argument("--owner", default=os.environ.get("OWNER_LOGIN", "owner"))
        parser.add_argument("--seed", type=int, default=2026)

    def handle(self, *args, **options) -> None:
        """Run all stages and print the demo logins."""
        from config.demo.seed import DemoRefused, run

        try:
            summary = run(options["owner"], seed=options["seed"], log=self.stdout.write)
        except DemoRefused as exc:
            raise CommandError(str(exc)) from exc
        logins = summary.pop("logins")
        password = summary.pop("password")
        for key, value in summary.items():
            self.stdout.write(f"  {key}: {value}")
        self.stdout.write(
            self.style.SUCCESS(f"demo school ready; every demo password is {password}")
        )
        self.stdout.write("staff logins:")
        for role, login, name in logins:
            if role not in ("guardian", "student"):
                self.stdout.write(f"  {login:<16} {role:<14} {name}")
        parents = [row for row in logins if row[0] == "guardian"][:3]
        students = [row for row in logins if row[0] == "student"][:3]
        self.stdout.write("example parent logins: " + ", ".join(row[1] for row in parents))
        self.stdout.write("example student logins: " + ", ".join(row[1] for row in students))
