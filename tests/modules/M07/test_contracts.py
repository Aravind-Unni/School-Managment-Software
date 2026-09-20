"""M07 contract suite: schema validity and registration agreement."""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest

from modules.fees.permissions import PERMISSION_CODES
from modules.fees.registration import REGISTRATION

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M07 = REPO_ROOT / "contracts" / "M07"


def load_json(relative: str) -> dict:
    """Load one of M07's JSON contract documents."""
    return json.loads((M07 / relative).read_text())


def test_dto_schema_is_valid():
    """DTO schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_event_schema_is_valid():
    """Event schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_response_fixtures_match_required_keys():
    """Consumer examples carry required ChargeDTO / BalanceDTO keys."""
    schema = load_json("schemas/dtos.schema.json")
    charge = schema["$defs"]["ChargeDTO"]
    balance = schema["$defs"]["BalanceDTO"]
    fixtures = load_json("fixtures/responses.json")
    for key in charge["required"]:
        assert key in fixtures["charge_s1_tuition"]
    for key in balance["required"]:
        assert key in fixtures["balance_after_partial_tuition_only"]


def test_permission_codes_match_registration():
    """Backend permission list matches ModuleRegistration."""
    assert set(PERMISSION_CODES) == set(REGISTRATION.permission_codes)


def test_openapi_lists_contract_operations():
    """Frozen OpenAPI exposes the packet operations."""
    paths = load_json("openapi.json")["paths"]
    assert "/fee-plans" in paths
    assert "/charges" in paths
    assert "/payments" in paths
    assert "/payments/{id}/reversals" in paths
    assert "/students/{id}/fee-statement" in paths


def test_event_names_are_envelope_safe():
    """Event types match the frozen lowercase two-segment pattern."""
    events = load_json("schemas/events.schema.json")["$defs"]
    assert "fees.payment_posted" in events
    assert "fees.payment_reversed" in events
    assert "fees.charge_posted" in events
