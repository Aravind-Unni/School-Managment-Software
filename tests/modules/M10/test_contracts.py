"""M10 contract suite: schema validity and registration agreement."""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest

from modules.alumni.permissions import PERMISSION_CODES
from modules.alumni.registration import REGISTRATION

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M10 = REPO_ROOT / "contracts" / "M10"


def load_json(relative: str) -> dict:
    """Load one of M10's JSON contract documents."""
    return json.loads((M10 / relative).read_text())


def test_dto_schema_is_valid():
    """DTO schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_event_schema_is_valid():
    """Event schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_response_fixtures_match_required_keys():
    """Consumer examples carry contracted example keys."""
    fixtures = load_json("fixtures/responses.json")
    assert "state" in fixtures["examples"]["candidate_pending_graduate"]
    assert "contact_fields" in fixtures["examples"]["profile_after_approve"]
    assert fixtures["examples"]["preference_withdrawn"]["allowed"] is False


def test_permission_codes_match_registration():
    """Backend permission list matches ModuleRegistration."""
    assert set(PERMISSION_CODES) == set(REGISTRATION.permission_codes)
    assert set(REGISTRATION.consumers) == {"access", "registry", "platform", "clock"}


def test_openapi_lists_contract_operations():
    """Frozen OpenAPI exposes the packet operations."""
    paths = load_json("openapi.json")["paths"]
    assert "/alumni/candidates" in paths
    assert "/alumni/candidates/{id}/approve" in paths
    assert "/alumni" in paths
    assert "/alumni/{id}/contact" in paths
    assert "/alumni/exports" in paths


def test_event_names_are_envelope_safe():
    """Event types match the frozen lowercase dotted pattern."""
    events = load_json("schemas/events.schema.json")["$defs"]
    assert "alumni.profile_approved" in events
    assert "alumni.contact_preference_changed" in events


def test_alumni_port_exports():
    """AlumniPort and DTOs are exported from contracts."""
    from contracts import (
        AlumniPort,
        AlumniProfileView,
        ContactPreferenceView,
        CreateCandidateResult,
    )

    assert AlumniPort is not None
    assert AlumniProfileView is not None
    assert ContactPreferenceView is not None
    assert CreateCandidateResult is not None


def test_the_module_imports_no_other_business_module():
    """Alumni must not import another business module package."""
    import ast

    root = REPO_ROOT / "backend" / "modules" / "alumni"
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
                if name.startswith("modules.") and not name.startswith("modules.alumni"):
                    raise AssertionError(f"{path}: forbidden import {name}")
