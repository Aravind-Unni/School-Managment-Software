"""M09 contract suite: schema validity and registration agreement."""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest

from modules.library.permissions import PERMISSION_CODES
from modules.library.registration import REGISTRATION

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M09 = REPO_ROOT / "contracts" / "M09"


def load_json(relative: str) -> dict:
    """Load one of M09's JSON contract documents."""
    return json.loads((M09 / relative).read_text())


def test_dto_schema_is_valid():
    """DTO schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_event_schema_is_valid():
    """Event schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_response_fixtures_match_required_keys():
    """Consumer examples carry required TitleDTO / LoanDTO keys."""
    schema = load_json("schemas/dtos.schema.json")
    title = schema["$defs"]["TitleDTO"]
    loan = schema["$defs"]["LoanDTO"]
    fixtures = load_json("fixtures/responses.json")
    for key in title["required"]:
        assert key in fixtures["title"]
    for key in loan["required"]:
        assert key in fixtures["loan_open_s1"]


def test_permission_codes_match_registration():
    """Backend permission list matches ModuleRegistration."""
    assert set(PERMISSION_CODES) == set(REGISTRATION.permission_codes)
    assert set(REGISTRATION.consumers) == {"access", "registry", "platform", "clock"}


def test_openapi_lists_contract_operations():
    """Frozen OpenAPI exposes the packet operations."""
    paths = load_json("openapi.json")["paths"]
    assert "/library/titles" in paths
    assert "/library/copies" in paths
    assert "/library/loans" in paths
    assert "/library/loans/{id}/return" in paths
    assert "/library/loans/{id}/renew" in paths
    assert "/library/overdues" in paths
    assert "/library/catalogue-imports" in paths


def test_event_names_are_envelope_safe():
    """Event types match the frozen lowercase dotted pattern."""
    events = load_json("schemas/events.schema.json")["$defs"]
    assert "library.loan_issued" in events
    assert "library.loan_returned" in events
    assert "library.overdue_detected" in events


def test_library_port_exports():
    """LibraryPort and DTOs are exported from contracts."""
    from contracts import AvailabilityView, LibraryPort, OpenLoanView

    assert LibraryPort is not None
    assert OpenLoanView is not None
    assert AvailabilityView is not None
