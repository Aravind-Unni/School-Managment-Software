"""Run every demo stage in order and return a summary for the operator."""

from __future__ import annotations

import random
import uuid

from django.conf import settings

from .api_actor import ApiActor
from .seed_academics import seed_assessments, seed_attendance, seed_timetable
from .seed_operations import rebuild_performance, seed_fees, seed_library, seed_notices
from .seed_people import DEMO_PASSWORD, seed_people


class DemoRefused(RuntimeError):
    """Seeding would be unsafe here; the message says why."""


def check_allowed(school_id) -> None:
    """Refuse on a school that already has students, or without explicit consent."""
    import os

    from modules.registry.models import Student

    if os.environ.get("ALLOW_DEMO_DATA", "").lower() != "true":
        raise DemoRefused(
            "demo data is for trial installs only; set ALLOW_DEMO_DATA=true to confirm"
        )
    if Student.objects.filter(school_id=school_id).exists():
        raise DemoRefused(
            "this school already has students; demo data is only for an empty school"
        )


def run(owner_login: str, *, seed: int = 2026, log=print) -> dict:
    """Seed the whole demo school as ``owner_login``. Returns counts and logins."""
    from modules.access.models import User

    school_id = uuid.UUID(str(settings.SCHOOL_ID))
    check_allowed(school_id)
    rng = random.Random(seed)
    today = settings.SCHOOL_CLOCK.now().date()
    owner = ApiActor(User.objects.get(school_id=school_id, login_name=owner_login))

    log("people: staff, students, parents, classes, teaching assignments ...")
    cast = seed_people(owner, school_id, rng=rng)
    actors = {
        login: ApiActor(User.objects.get(school_id=school_id, login_name=login))
        for login in cast.staff
    }
    principal = actors["principal"]

    log("timetable ...")
    seed_timetable(principal, cast, school_id)
    log("attendance history (this takes a few minutes) ...")
    sessions = seed_attendance(cast, actors, today=today, rng=rng)
    log("assessments ...")
    published = seed_assessments(cast, actors, principal, rng=rng)
    log("fees ...")
    payments = seed_fees(actors["accounts"], cast, school_id, rng=rng)
    log("library ...")
    loans = seed_library(actors["library"], cast, today=today, rng=rng)
    log("notices ...")
    notices = seed_notices(actors, cast)
    log("performance dashboards and warnings ...")
    rebuilt = rebuild_performance(principal)
    return {
        "students": len(cast.students),
        "parents": len(cast.guardians),
        "staff": len(cast.staff),
        "attendance_sessions": sessions,
        "published_assessments": published,
        "payments": payments,
        "library_loans": loans,
        "notices": notices,
        "projections": rebuilt,
        "password": DEMO_PASSWORD,
        "logins": cast.logins,
    }
