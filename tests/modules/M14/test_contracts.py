"""M14 contract suite: schema validity, fixtures and registration agreement."""

from __future__ import annotations

import json
import pathlib
import uuid

import jsonschema
import pytest

from modules.platform.permissions import PERMISSION_CODES
from modules.platform.registration import REGISTRATION
from modules.platform.services.adapter import PlatformAdapter
from shared.ports import runtime

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M14 = REPO_ROOT / "contracts" / "M14"


def load_json(relative: str) -> dict:
    """Load one of M14's JSON contract documents."""
    return json.loads((M14 / relative).read_text())


def test_dto_schema_is_valid():
    """DTO schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_event_schema_is_valid():
    """Event schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_every_scenario_uuid_parses():
    """Scenario ids must be real UUIDs."""
    scenario = load_json("fixtures/scenario.json")["school_a"]
    for key, value in scenario.items():
        if key.endswith("_id"):
            uuid.UUID(value)


def test_response_fixtures_match_required_dto_keys():
    """Consumer examples carry every required key of the DTO they illustrate."""
    schema = load_json("schemas/dtos.schema.json")["$defs"]
    examples = load_json("fixtures/responses.json")
    pairs = (
        ("LiveHealthDTO", "live_health"),
        ("ReadyHealthDTO", "ready_health_ok"),
        ("JobDTO", "job_failed"),
        ("AuditRecordDTO", "audit_redacted"),
        ("RestoreRehearsalDTO", "restore_rehearsal_verified"),
    )
    for definition, example in pairs:
        for key in schema[definition]["required"]:
            assert key in examples[example], (definition, key)


def test_event_fixtures_validate_against_the_event_schema():
    """Example event payload validates against its frozen schema."""
    events = load_json("schemas/events.schema.json")["$defs"]
    payload = load_json("fixtures/responses.json")["event_job_state_changed"]["payload"]
    jsonschema.Draft202012Validator(events["platform.job_state_changed"]).validate(payload)


def test_permission_codes_match_registration():
    """Backend permission list matches ModuleRegistration."""
    assert set(PERMISSION_CODES) == set(REGISTRATION.permission_codes)
    assert REGISTRATION.owned_permission_prefixes == frozenset(
        {"platform.", "jobs.", "audit.", "backups."}
    )


def test_registration_declares_contracted_consumers():
    """Consumers include access, clock, object_storage and self platform."""
    assert set(REGISTRATION.consumers) == {
        "access",
        "clock",
        "object_storage",
        "platform",
    }


def test_openapi_lists_contract_operations():
    """Frozen OpenAPI exposes the packet's paths."""
    paths = load_json("openapi.json")["paths"]
    for route in (
        "/health/live",
        "/health/ready",
        "/jobs/{id}",
        "/jobs/{id}/retry",
        "/audit",
        "/operations/restore-rehearsals",
    ):
        assert route in paths


def test_m14_binds_real_platform_not_test_adapter(db):
    """M14 must never receive TestPlatformAdapter."""
    platform = runtime.get_registry().resolve("platform")
    assert isinstance(platform, PlatformAdapter)
    assert type(platform).__name__ != "TestPlatformAdapter"
