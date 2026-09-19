"""LOCAL-ONLY test settings using SQLite. Not a deployment profile.

Why this exists: a developer without Docker can still run the pure unit and
contract suites. It is NOT sufficient for acceptance.

What it CANNOT prove, and what therefore must run against real PostgreSQL in
Compose or CI:
  * migrations applying to PostgreSQL
  * JSONB behaviour, transactional DDL, row locking
  * the two-simultaneous-isolated-profiles requirement
  * anything involving a broker or worker

``scripts/dev.py check`` never selects this module; it is chosen explicitly by
``pytest -c backend/pytest.sqlite.ini`` and marks its results as such in the
machine-readable report.
"""

from __future__ import annotations

from config.settings.base import *
from config.settings.base import HARNESS_APPS, INSTALLED_APPS

APP_ENV = "standalone"
MODULE_ID = "M00"

INSTALLED_APPS = INSTALLED_APPS + HARNESS_APPS + ["modules.demo"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "ATOMIC_REQUESTS": False,
    }
}

SECRET_KEY = "test-only-not-a-secret"
DEV_PERSONA_MODE = "fixed"
DEMO_FIXTURES_ENABLED = True
WORKER_AVAILABLE = False

from shared import fixtures
from shared.http.context import DevPersona

DEV_PERSONA = DevPersona(actor_id=fixtures.TEACHER_T1, school_id=fixtures.SCHOOL_A)

#: Marks every result produced under this profile, so a report cannot be
#: mistaken for a PostgreSQL run.
TEST_BACKEND_LABEL = "sqlite-local-only"


def build_port_registry(registration=None):
    """Bind fakes for the local SQLite test profile.

    Identical binding to the standalone runner, by construction: both call
    shared.ports.build_fake_registry. ``worker_available`` is False, so any test
    touching enqueue raises EagerModeNotAsserted rather than pretending.
    """
    from shared.ports import build_fake_registry

    return build_fake_registry(
        registration,
        app_env="standalone",
        clock=SCHOOL_CLOCK,
        worker_available=False,
    )
