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


def test_permission_codes_must_lie_inside_an_owned_prefix():
    """A module granting itself another module's permission is a privilege leak.

    B00 enforced this by requiring every code to start with the module slug. M01's
    real vocabulary is 'roles.manage' and 'auth.factor.manage_self', so ownership
    is now declared as PREFIXES instead. The property is unchanged; only how it is
    expressed moved.
    """
    with pytest.raises(ValueError, match="owned prefixes"):
        ModuleRegistration(
            id="M04",
            slug="attendance",
            api_prefix="/api/attendance/",
            permission_codes=("fees.read_invoice",),
        )


def test_the_slug_prefix_is_owned_by_default():
    """Every registration written against B00 stays valid with no change."""
    registration = ModuleRegistration(
        id="M04",
        slug="attendance",
        api_prefix="/api/attendance/",
        permission_codes=("attendance.read_register",),
    )
    assert registration.owned_permission_prefixes == frozenset({"attendance."})


def test_a_multi_segment_code_is_accepted_inside_an_owned_prefix():
    registration = ModuleRegistration(
        id="M01",
        slug="access",
        api_prefix="/api/v1/",
        api_path_roots=("auth/",),
        permission_prefixes=("auth.",),
        permission_codes=("auth.factor.manage_self", "auth.factor.reset_other"),
    )
    assert "auth.factor.manage_self" in registration.permission_codes


def test_a_shared_api_prefix_requires_declared_path_roots():
    """Two modules under /api/v1/ with no declared roots collide silently."""
    with pytest.raises(ValueError, match="api_path_roots must declare"):
        ModuleRegistration(id="M01", slug="access", api_prefix="/api/v1/")


def test_path_roots_are_rejected_under_a_module_specific_prefix():
    with pytest.raises(ValueError, match="only meaningful under a shared"):
        ModuleRegistration(
            id="M00", slug="demo", api_prefix="/api/demo/", api_path_roots=("notes/",)
        )


def test_two_modules_claiming_one_permission_prefix_is_refused():
    from contracts.registration import assert_no_registration_collisions

    first = ModuleRegistration(
        id="M01",
        slug="access",
        api_prefix="/api/v1/",
        api_path_roots=("auth/",),
        permission_prefixes=("auth.",),
    )
    second = ModuleRegistration(
        id="M02",
        slug="registry",
        api_prefix="/api/v1/",
        api_path_roots=("people/",),
        permission_prefixes=("auth.",),
    )
    with pytest.raises(ValueError, match="permission prefix"):
        assert_no_registration_collisions((first, second))


def test_two_modules_claiming_one_api_path_is_refused():
    from contracts.registration import assert_no_registration_collisions

    first = ModuleRegistration(
        id="M01",
        slug="access",
        api_prefix="/api/v1/",
        api_path_roots=("auth/",),
        permission_prefixes=("auth.",),
    )
    second = ModuleRegistration(
        id="M02",
        slug="registry",
        api_prefix="/api/v1/",
        api_path_roots=("auth/",),
        permission_prefixes=("people.",),
    )
    with pytest.raises(ValueError, match="API path"):
        assert_no_registration_collisions((first, second))


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


def test_the_active_module_registration_is_valid_and_declares_only_fakeable_ports():
    """Assert the registration of whichever module this profile installed.

    Was hardcoded to the M00 demo, which imported ``modules.demo`` under EVERY
    profile and so broke the very isolation assertion next door -- "no other
    business module is even imported". Reading MODULE_ID instead checks each
    module's own registration, which is the property worth having.
    """
    import importlib

    from django.conf import settings

    from shared.ports import FAKEABLE_PORTS

    address = address_for(settings.MODULE_ID)
    registration = importlib.import_module(address.registration_path).REGISTRATION

    assert registration.id == address.id
    assert registration.slug == address.slug
    assert set(registration.consumers) <= FAKEABLE_PORTS
    assert registration.api_prefix.startswith("/api/")


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


def test_the_persona_fixture_file_matches_the_derived_uuids():
    """The committed fixture file must not drift from shared.fixtures.

    A stale id here would make a cross-language consumer suite assert against a
    persona the backend never produces.
    """
    import json
    import pathlib

    from shared import fixtures as fx

    root = pathlib.Path(__file__).resolve().parents[2]
    data = json.loads((root / "contracts/M00/fixtures/personas.json").read_text())

    assert data["namespace"] == str(fx.FIXTURE_NAMESPACE)
    assert data["schools"] == {
        "school_a": str(fx.SCHOOL_A),
        "school_b": str(fx.SCHOOL_B),
    }
    expected_people = {
        "S1": fx.STUDENT_S1,
        "S2": fx.STUDENT_S2,
        "S3": fx.STUDENT_S3,
        "G1": fx.GUARDIAN_G1,
        "G2": fx.GUARDIAN_G2,
        "T1": fx.TEACHER_T1,
        "T2": fx.TEACHER_T2,
        "P1": fx.PRINCIPAL_P1,
    }
    for key, value in expected_people.items():
        assert data["people"][key]["id"] == str(value), key
    assert data["sections"] == {"C1": str(fx.CLASS_C1), "C2": str(fx.CLASS_C2)}


def test_the_documented_relationships_match_what_the_fake_registry_answers():
    """Every expected_relationships row in the fixture file must be reproducible."""
    import json
    import pathlib
    from datetime import UTC, datetime

    from contracts.identity import AuthLevel, RequestContext
    from shared import fixtures as fx
    from shared.fakes import FakeRegistry

    root = pathlib.Path(__file__).resolve().parents[2]
    data = json.loads((root / "contracts/M00/fixtures/personas.json").read_text())
    by_label = {
        "S1": fx.STUDENT_S1,
        "S2": fx.STUDENT_S2,
        "S3": fx.STUDENT_S3,
        "G1": fx.GUARDIAN_G1,
        "G2": fx.GUARDIAN_G2,
        "T1": fx.TEACHER_T1,
        "T2": fx.TEACHER_T2,
        "P1": fx.PRINCIPAL_P1,
    }
    registry = FakeRegistry()
    for row in data["expected_relationships"]:
        context = RequestContext(
            actor_id=by_label[row["actor"]],
            school_id=fx.SCHOOL_A,
            request_id="fixture-check",
            auth_level=AuthLevel.TWO_FACTOR,
            auth_time=datetime.now(UTC),
        )
        facts = registry.relationship_facts(context, by_label[row["subject"]])
        assert facts.relationship.value == row["relationship"], row
