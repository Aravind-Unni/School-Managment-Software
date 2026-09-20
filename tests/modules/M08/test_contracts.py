"""M08 contract suite: schema validity and registration agreement."""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest

from modules.transport.permissions import PERMISSION_CODES
from modules.transport.registration import REGISTRATION

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M08 = REPO_ROOT / "contracts" / "M08"


def load_json(relative: str) -> dict:
    """Load one of M08's JSON contract documents."""
    return json.loads((M08 / relative).read_text())


def test_dto_schema_is_valid():
    """DTO schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_event_schema_is_valid():
    """Event schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_response_fixtures_match_required_keys():
    """Consumer examples carry required ParticipationDTO / BillingRequestDTO keys."""
    schema = load_json("schemas/dtos.schema.json")
    participation = schema["$defs"]["ParticipationDTO"]
    billing = schema["$defs"]["BillingRequestDTO"]
    fixtures = load_json("fixtures/responses.json")
    for key in participation["required"]:
        assert key in fixtures["participation_s1"]
    for key in billing["required"]:
        assert key in fixtures["billing_request_posted"]


def test_permission_codes_match_registration():
    """Backend permission list matches ModuleRegistration."""
    assert set(PERMISSION_CODES) == set(REGISTRATION.permission_codes)
    assert set(REGISTRATION.consumers) == {
        "access",
        "registry",
        "fees",
        "platform",
        "clock",
    }


def test_openapi_lists_contract_operations():
    """Frozen OpenAPI exposes the packet operations."""
    paths = load_json("openapi.json")["paths"]
    assert "/buses" in paths
    assert "/bus-participations" in paths
    assert "/bus-billing-runs" in paths
    assert "/bus-participants" in paths
    assert "/bus-billing-reconciliation" in paths
    assert "/bus-adjustments" in paths
    assert "/bus-billing-requests/{id}/retry" in paths


def test_event_names_are_envelope_safe():
    """Event types match the frozen lowercase dotted pattern."""
    events = load_json("schemas/events.schema.json")["$defs"]
    assert "transport.participation_changed" in events
    assert "transport.billing_requested" in events


def test_transport_port_exports():
    """TransportPort and DTOs are exported from contracts."""
    from contracts import PeriodChargeResult, TransportParticipationView, TransportPort

    assert TransportPort is not None
    assert TransportParticipationView is not None
    assert PeriodChargeResult is not None
