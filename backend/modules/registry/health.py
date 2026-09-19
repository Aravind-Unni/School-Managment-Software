"""Health checks M02 declares to the host.

A check answers "can this module actually serve", not "is the process alive".
Reporting healthy while the configuration row is missing would let the runner
announce a working stack that 404s on its first request.
"""

from __future__ import annotations


def check_tables() -> bool:
    """Return whether M02's own tables are queryable."""
    from .models import Student

    Student.objects.exists()
    return True


def check_school_config_installed() -> bool:
    """Return whether the bootstrap installed this deployment's configuration.

    Absent means the seed did not run. The API cannot serve school-config or
    any write that authorises against it, so this is unhealthy rather than a
    condition to create on the fly.
    """
    from django.conf import settings

    from .models import SchoolConfig

    return SchoolConfig.objects.filter(school_id=settings.SCHOOL_ID).exists()
