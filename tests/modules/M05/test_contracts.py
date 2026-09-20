"""M05 contract suite: schema validity and registration agreement."""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest

from modules.assessment.permissions import PERMISSION_CODES
from modules.assessment.registration import REGISTRATION

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M05 = REPO_ROOT / "contracts" / "M05"


def load_json(relative: str) -> dict:
    """Load one of M05's JSON contract documents."""
    return json.loads((M05 / relative).read_text())


def test_dto_schema_is_valid():
    """DTO schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_event_schema_is_valid():
    """Event schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_response_fixtures_match_required_keys():
    """Consumer examples carry the required AssessmentDTO / ResultDTO keys."""
    schema = load_json("schemas/dtos.schema.json")
    assessment = schema["$defs"]["AssessmentDTO"]
    result = schema["$defs"]["ResultDTO"]
    fixtures = load_json("fixtures/responses.json")
    for key in assessment["required"]:
        assert key in fixtures["create_assessment_response"]
    for key in result["required"]:
        assert key in fixtures["published_result_s1"]


def test_permission_codes_match_registration():
    """Backend permission list matches ModuleRegistration."""
    assert set(PERMISSION_CODES) == set(REGISTRATION.permission_codes)


def test_openapi_lists_contract_operations():
    """Frozen OpenAPI exposes the packet operations."""
    paths = load_json("openapi.json")["paths"]
    assert "/assessments" in paths
    assert "/assessments/{id}/results/{student_id}" in paths
    assert "/results/{id}/evidence" in paths
    assert "/assessments/{id}/submit" in paths
    assert "/assessments/{id}/approve" in paths
    assert "/assessments/{id}/publication" in paths
    assert "/assessments/{id}/reopen" in paths
    assert "/results/{id}/evidence/{binding_id}/view" in paths


def test_event_names_are_envelope_safe():
    """Event types match the frozen lowercase two-segment pattern."""
    events = load_json("schemas/events.schema.json")["$defs"]
    assert "assessment.results_published" in events
    assert "assessment.result_revised" in events
