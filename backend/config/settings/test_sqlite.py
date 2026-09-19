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

from cryptography.fernet import Fernet

from config import env
from config.settings.base import *
from config.settings.base import HARNESS_APPS, INSTALLED_APPS
from shared.module_catalog import address_for

APP_ENV = "standalone"

#: Which module's app to install. Defaults to the M00 placeholder so B00's own
#: suite is unchanged; each module's suite selects itself with MODULE_ID.
MODULE_ID = env.optional("MODULE_ID", "M00").upper()
MODULE_ADDRESS = address_for(MODULE_ID)

INSTALLED_APPS = INSTALLED_APPS + HARNESS_APPS + [MODULE_ADDRESS.django_app]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "ATOMIC_REQUESTS": False,
    }
}

SECRET_KEY = "test-only-not-a-secret"

#: A test-only Fernet key. Generated fresh per process, so nothing encrypted in
#: one test run can be decrypted in another -- which is correct for a throwaway
#: in-memory database and means no key material is ever committed.
TOTP_ENCRYPTION_KEY = Fernet.generate_key().decode()

#: M01 owns real login, so it must NOT get a synthetic persona: a persona would
#: bypass the very flow under test. Every other module uses the fixed persona.
DEV_PERSONA_MODE = "off" if MODULE_ID == "M01" else "fixed"
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
