"""Create the first school owner account on a production database.

Refuses when an active owner already exists. Refuses outside production unless
``--force-dev`` is passed for local prod-compose smoke.
"""

from __future__ import annotations

import os
import uuid

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from modules.access.models import Grant, Permission, Role, User, UserRole
from modules.access.permissions import CATALOGUE
from modules.access.scopes import ScopeType


class Command(BaseCommand):
    """``manage.py bootstrap_owner`` — one-shot production owner creation."""

    help = "Create the first owner account for this SCHOOL_ID deployment."

    def add_arguments(self, parser) -> None:
        """Accept optional overrides; defaults come from the environment."""
        parser.add_argument("--login", default=os.environ.get("OWNER_LOGIN", ""))
        parser.add_argument("--password", default=os.environ.get("OWNER_PASSWORD", ""))
        parser.add_argument(
            "--display-name",
            default=os.environ.get("OWNER_DISPLAY_NAME", "School Owner"),
        )
        parser.add_argument(
            "--force-dev",
            action="store_true",
            help="Allow bootstrap when APP_ENV is not production (local smoke).",
        )

    def handle(self, *args, **options) -> None:
        """Create owner role + account when none exist for settings.SCHOOL_ID."""
        if settings.APP_ENV != "production" and not options["force_dev"]:
            raise CommandError("refusing bootstrap outside production (pass --force-dev)")

        login_name = (options["login"] or "").strip()
        password = options["password"] or ""
        display = (options["display_name"] or "").strip() or "School Owner"
        if not login_name or not password:
            raise CommandError("OWNER_LOGIN and OWNER_PASSWORD are required")

        school_id = uuid.UUID(str(settings.SCHOOL_ID))
        now = timezone.now()
        ns = school_id

        with transaction.atomic():
            for spec in CATALOGUE:
                Permission.objects.update_or_create(
                    code=spec.code,
                    defaults={
                        "description": spec.description,
                        "requires_recent_two_factor": spec.requires_recent_two_factor,
                    },
                )

            if UserRole.objects.filter(
                role__school_id=school_id, role__is_owner_role=True, user__active=True
            ).exists():
                raise CommandError("an active owner already exists; refusing")

            owner_role, _ = Role.objects.update_or_create(
                id=uuid.uuid5(ns, "bootstrap.owner_role"),
                defaults={
                    "school_id": school_id,
                    "name": "Owner",
                    "is_owner_role": True,
                    "requires_two_factor": True,
                    "version": 1,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            Grant.objects.filter(role=owner_role).delete()
            owner_actions = tuple(spec.code for spec in CATALOGUE)
            Grant.objects.bulk_create(
                [
                    Grant(
                        id=uuid.uuid5(ns, f"bootstrap.grant.{action}"),
                        school_id=school_id,
                        role=owner_role,
                        action=action,
                        scope_type=ScopeType.SCHOOL.value,
                        scope_id=None,
                        valid_from=now.date(),
                        valid_to=None,
                        created_at=now,
                    )
                    for action in owner_actions
                ]
            )

            user, created = User.objects.update_or_create(
                id=uuid.uuid5(ns, f"bootstrap.owner.{login_name}"),
                defaults={
                    "school_id": school_id,
                    "login_name": login_name,
                    "password_hash": make_password(password),
                    "display_name": display,
                    "person_id": None,
                    "active": True,
                    "version": 1,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            UserRole.objects.filter(user=user).delete()
            UserRole.objects.create(
                id=uuid.uuid5(ns, f"bootstrap.userrole.{login_name}"),
                school_id=school_id,
                user=user,
                role=owner_role,
                granted_at=now,
            )

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"owner {action}: {login_name}"))
