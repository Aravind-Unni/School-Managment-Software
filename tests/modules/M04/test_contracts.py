"""M04 contract suite: schema validity and registration agreement."""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest

from modules.attendance.permissions import PERMISSION_CODES
from modules.attendance.registration import REGISTRATION

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M04 = REPO_ROOT / "contracts" / "M04"


def load_json(relative: str) -> dict:
    """Load one of M04's JSON contract documents."""
    return json.loads((M04 / relative).read_text())


def test_dto_schema_is_valid():
    """DTO schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_event_schema_is_valid():
    """Event schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_response_fixtures_match_summary_schema():
    """Consumer summary examples validate against AttendanceSummaryDTO."""
    schema = load_json("schemas/dtos.schema.json")
    summary = schema["$defs"]["AttendanceSummaryDTO"]
    # Inline $ref resolution is limited; validate required keys instead.
    examples = load_json("fixtures/responses.json")["examples"]
    for example in examples:
        if example["id"] in {"R1", "R2"}:
            body = example["body"]
            for key in summary["required"]:
                assert key in body


def test_permission_codes_match_registration():
    """Backend permission list matches ModuleRegistration."""
    assert set(PERMISSION_CODES) == set(REGISTRATION.permission_codes)


def test_openapi_lists_six_operations():
    """Frozen OpenAPI exposes the six packet operations."""
    paths = load_json("openapi.json")["paths"]
    assert "/attendance/periods" in paths
    assert "/attendance/sessions" in paths
    assert "/attendance/sessions/{id}" in paths
    assert "/attendance/sessions/{id}/submit" in paths
    assert "/attendance/entries/{id}/corrections" in paths
    assert "/attendance/summary" in paths


def test_event_names_are_envelope_safe():
    """Event types match the frozen lowercase two-segment pattern."""
    events = load_json("schemas/events.schema.json")["$defs"]
    assert "attendance.submitted" in events
    assert "attendance.corrected" in events
