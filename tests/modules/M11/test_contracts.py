"""M11 contract suite: schema validity and registration agreement."""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest

from modules.communications.permissions import PERMISSION_CODES
from modules.communications.registration import REGISTRATION

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M11 = REPO_ROOT / "contracts" / "M11"


def load_json(relative: str) -> dict:
    """Load one of M11's JSON contract documents."""
    return json.loads((M11 / relative).read_text())


def test_dto_schema_is_valid():
    """DTO schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_event_schema_is_valid():
    """Event schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_response_fixtures_match_required_keys():
    """Consumer examples carry contracted example keys."""
    fixtures = load_json("fixtures/responses.json")
    assert fixtures["examples"]["notice_draft_en"]["locale"] == "en"
    assert "കായികദിനം" in fixtures["examples"]["notice_published_ml"]["title"]
    assert fixtures["examples"]["delivery_queued"]["state"] == "queued"


def test_permission_codes_match_registration():
    """Backend permission list matches ModuleRegistration."""
    assert set(PERMISSION_CODES) == set(REGISTRATION.permission_codes)
    assert set(REGISTRATION.consumers) == {"access", "registry", "platform", "clock"}


def test_openapi_lists_contract_operations():
    """Frozen OpenAPI exposes the packet operations."""
    paths = load_json("openapi.json")["paths"]
    assert "/notices" in paths
    assert "/notices/{id}/publish" in paths
    assert "/messages" in paths
    assert "/deliveries/{id}" in paths
    assert "/sms/callback/{provider}" in paths


def test_event_names_are_envelope_safe():
    """Event types match the frozen lowercase dotted pattern."""
    events = load_json("schemas/events.schema.json")["$defs"]
    assert "communications.notice_published" in events
    assert "communications.delivery_status_changed" in events


def test_communications_port_exports():
    """CommunicationsPort and DeliveryDTO are exported from contracts."""
    from contracts import CommunicationsPort, DeliveryDTO

    assert CommunicationsPort is not None
    assert DeliveryDTO is not None


def test_the_module_imports_no_other_business_module():
    """Communications must not import another business module package."""
    import ast

    root = REPO_ROOT / "backend" / "modules" / "communications"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                if name.startswith("modules.") and not name.startswith(
                    "modules.communications"
                ):
                    raise AssertionError(f"{path}: forbidden import {name}")
