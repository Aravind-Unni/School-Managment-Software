"""Health checks M03 declares to the host.

A check answers "can this module actually serve", not "is the process alive".

Deliberately NOT a check that a published timetable exists. A school that has
not built its grid yet is a normal state, not an unhealthy deployment, and a
probe that failed until someone published would make every fresh install look
broken.
"""

from __future__ import annotations


def check_tables() -> bool:
    """Return whether M03's own tables are queryable."""
    from .models import TimetableVersion

    TimetableVersion.objects.exists()
    return True


def check_calendar_resolvable() -> bool:
    """Return whether the calendar can be resolved for a date.

    Exercises the read path that every schedule view depends on -- the effective
    version lookup and the exception join -- rather than only touching a table.
    A school with no published revision resolves to "not a school day", which is
    a correct answer and a healthy module.
    """
    from django.conf import settings

    from .services.reads import ScheduleReader

    school_id = settings.SCHOOL_ID
    today = settings.SCHOOL_CLOCK.now()
    reader = ScheduleReader(clock=settings.SCHOOL_CLOCK)
    reader.calendar_days(
        school_id=school_id, from_date=_school_date(today), to_date=_school_date(today)
    )
    return True


def _school_date(instant):
    """Return the civil date at the school for an instant."""
    from contracts.values import school_date

    return school_date(instant)
