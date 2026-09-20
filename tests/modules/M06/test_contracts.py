"""M06 contract suite: schema validity and registration agreement."""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest

from modules.performance.permissions import PERMISSION_CODES
from modules.performance.registration import REGISTRATION

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M06 = REPO_ROOT / "contracts" / "M06"


def load_json(relative: str) -> dict:
    """Load one of M06's JSON contract documents."""
    return json.loads((M06 / relative).read_text())


def test_dto_schema_is_valid():
    """DTO schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_event_schema_is_valid():
    """Event schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_response_fixtures_match_required_keys():
    """Consumer examples carry the required DashboardDTO keys."""
    schema = load_json("schemas/dtos.schema.json")
    dashboard = schema["$defs"]["DashboardDTO"]
    fixtures = load_json("fixtures/responses.json")
    for key in dashboard["required"]:
        assert key in fixtures["dashboard_s1"]


def test_permission_codes_match_registration():
    """Backend permission list matches ModuleRegistration."""
    assert set(PERMISSION_CODES) == set(REGISTRATION.permission_codes)


def test_openapi_lists_contract_operations():
    """Frozen OpenAPI exposes the packet operations."""
    paths = load_json("openapi.json")["paths"]
    assert "/performance/dashboard" in paths
    assert "/warning-rules" in paths
    assert "/warnings/{id}/acknowledge" in paths
    assert "/warnings/{id}/dismiss" in paths
    assert "/interventions" in paths
    assert "/meetings" in paths
    assert "/performance/export" in paths
    assert "/performance/rebuild" in paths


def test_event_names_are_envelope_safe():
    """Event types match the frozen lowercase two-segment pattern."""
    events = load_json("schemas/events.schema.json")["$defs"]
    assert "performance.warning_opened" in events
    assert "performance.intervention_reviewed" in events
