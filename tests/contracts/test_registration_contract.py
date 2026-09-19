"""ModuleRegistration validates its own declaration at import time."""

from __future__ import annotations

import pytest

from contracts.registration import (
    FrontendRoute,
    HealthCheck,
    ModuleRegistration,
    ScheduledJob,
)
from shared.module_catalog import BUSINESS_MODULE_IDS, MODULE_SLUGS, address_for

pytestmark = pytest.mark.contract

#: The nine fields B00 fixes for a registration, plus django_app for the host.
REQUIRED_FIELDS = {
    "id",
    "slug",
    "api_prefix",
    "frontend_routes",
    "permission_codes",
    "consumers",
    "scheduled_jobs",
    "migration_dependencies",
    "health_checks",
}


def test_registration_declares_every_contracted_field():
    assert REQUIRED_FIELDS <= set(ModuleRegistration.__dataclass_fields__)


def test_catalog_matches_the_specified_slug_mapping():
    # Straight from the B00 packet. A drift here mis-routes a whole module.
    assert MODULE_SLUGS == {
        "M00": "demo",
        "M01": "access",
        "M02": "registry",
        "M03": "timetable",
        "M04": "attendance",
        "M05": "assessment",
        "M06": "performance",
        "M07": "fees",
        "M08": "transport",
        "M09": "library",
        "M10": "alumni",
        "M11": "communications",
        "M12": "files",
        "M13": "exchange",
        "M14": "platform",
    }


def test_there_are_exactly_fourteen_business_modules():
    assert len(BUSINESS_MODULE_IDS) == 14
    assert "M00" not in BUSINESS_MODULE_IDS


@pytest.mark.parametrize("bad_id", ["M15", "M99", "S04", "m04", "4", ""])
def test_ids_outside_m00_to_m14_are_refused(bad_id):
    with pytest.raises(ValueError, match=r"M00\.\.M14"):
        ModuleRegistration(id=bad_id, slug="demo", api_prefix="/api/demo/")


@pytest.mark.parametrize(
    "bad_prefix", ["api/demo/", "/api/demo", "/demo/", "/api/Demo/", "/api//"]
)
def test_malformed_api_prefixes_are_refused(bad_prefix):
    with pytest.raises(ValueError, match="api_prefix"):
        ModuleRegistration(id="M00", slug="demo", api_prefix=bad_prefix)


def test_permission_codes_must_be_namespaced_to_the_module_slug():
    # A module granting itself another module's permission is a privilege leak.
    with pytest.raises(ValueError, match="namespaced"):
        ModuleRegistration(
            id="M04",
            slug="attendance",
            api_prefix="/api/attendance/",
            permission_codes=("fees.read_invoice",),
        )


@pytest.mark.parametrize("bad_code", ["Attendance.read", "attendance-read", "attendance."])
def test_malformed_permission_codes_are_refused(bad_code):
    with pytest.raises(ValueError):
        ModuleRegistration(
            id="M04",
            slug="attendance",
            api_prefix="/api/attendance/",
            permission_codes=(bad_code,),
        )


def test_a_route_cannot_require_an_undeclared_permission():
    with pytest.raises(ValueError, match="undeclared"):
        ModuleRegistration(
            id="M00",
            slug="demo",
            api_prefix="/api/demo/",
            permission_codes=("demo.read_own_note",),
            frontend_routes=(
                FrontendRoute(path="/demo", component="X", required_permission="demo.write_x"),
            ),
        )


def test_the_demo_registration_is_valid_and_declares_only_fakeable_ports():
    from modules.demo.registration import REGISTRATION
    from shared.ports import FAKEABLE_PORTS

    assert REGISTRATION.id == "M00"
    assert REGISTRATION.slug == "demo"
    assert set(REGISTRATION.consumers) <= FAKEABLE_PORTS
    assert REGISTRATION.api_prefix == "/api/demo/"


def test_every_business_module_has_a_contract_directory():
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[2]
    for module_id in BUSINESS_MODULE_IDS:
        assert (root / address_for(module_id).contract_dir).is_dir(), module_id


def test_registration_accepts_jobs_and_health_checks():
    registration = ModuleRegistration(
        id="M04",
        slug="attendance",
        api_prefix="/api/attendance/",
        permission_codes=("attendance.read_register",),
        scheduled_jobs=(
            ScheduledJob("nightly", "0 18 * * *", "modules.attendance.tasks.roll"),
        ),
        health_checks=(HealthCheck("db", "modules.attendance.health.check"),),
        migration_dependencies=("M02",),
    )
    assert registration.scheduled_jobs[0].cron == "0 18 * * *"
    assert registration.migration_dependencies == ("M02",)
