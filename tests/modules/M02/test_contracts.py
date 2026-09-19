"""M02 contract suite: schema validity, fixtures, and code/contract agreement.

Runs with no database and no containers, so it is the fastest signal that
something structural broke. These assertions are about the FROZEN artefacts in
contracts/M02 and whether the code still serves them -- not about behaviour,
which the other files in this directory cover.
"""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M02 = REPO_ROOT / "contracts" / "M02"


def load_json(relative: str) -> dict:
    """Load one of M02's JSON contract documents."""
    return json.loads((M02 / relative).read_text())


# --- schema validity -------------------------------------------------------


def test_the_dto_schema_is_itself_a_valid_json_schema():
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_the_event_schema_is_itself_a_valid_json_schema():
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_the_openapi_document_is_valid():
    from drf_spectacular.validation import validate_schema

    validate_schema(load_json("openapi.json"))


def test_every_response_fixture_validates_against_its_declared_schema():
    """A published example that does not match its own schema is worse than none."""
    schema = load_json("schemas/dtos.schema.json")
    for example in load_json("fixtures/responses.json"):
        selected = {"$defs": schema["$defs"], "$ref": f"#/$defs/{example['schema']}"}
        jsonschema.Draft202012Validator(
            selected, format_checker=jsonschema.FormatChecker()
        ).validate(example["value"])


# --- closed write shapes ---------------------------------------------------


def test_every_write_dto_refuses_unknown_fields():
    """An undeclared field must be a 422, never a silently ignored value.

    A write shape that accepts unknown keys is how a client ends up asserting
    its own school or version and believing the server honoured it.
    """
    schema = load_json("schemas/dtos.schema.json")
    for name, definition in schema["$defs"].items():
        if definition.get("type") != "object":
            continue
        assert definition.get("additionalProperties") is False, name


def test_no_write_shape_accepts_a_client_supplied_school_or_version():
    """Identity and version are server state, never inputs on a create."""
    schema = load_json("schemas/dtos.schema.json")
    for name in ("CreateStudent", "GuardianInput", "StaffInput", "SectionInput"):
        properties = schema["$defs"][name].get("properties", {})
        assert "school_id" not in properties, name
        assert "version" not in properties, name
        assert "id" not in properties, name


# --- code and contract agree ----------------------------------------------


def test_the_error_taxonomy_is_not_extended_by_this_module():
    """M02 reuses the frozen codes and adds message keys, never new codes."""
    from contracts.errors import ErrorCode

    rows = load_json("error-codes.json")["rows"]
    for row in rows:
        assert row["code"] in {str(code) for code in ErrorCode}, row["code"]


def test_every_declared_permission_code_is_owned_by_a_declared_prefix():
    """A code outside the module's prefixes would collide with another module."""
    from modules.registry.registration import REGISTRATION

    for code in REGISTRATION.permission_codes:
        assert any(code.startswith(prefix) for prefix in REGISTRATION.permission_prefixes), code


def test_the_module_does_not_consume_the_registry_port():
    """M02 IS the Registry. Consuming a fake of itself would prove nothing."""
    from modules.registry.registration import REGISTRATION

    assert "registry" not in REGISTRATION.consumers


def test_served_paths_match_the_frozen_openapi_surface():
    """Every route mounted in step 1 is a path the frozen contract declares.

    Guards the direction that matters: serving something the contract does not
    declare. The reverse -- a contracted path not yet served -- is expected
    while steps 2 to 4 are outstanding, so it is not asserted here.
    """
    from modules.registry import urls

    contracted = set(load_json("openapi.json")["paths"])
    for pattern in urls.urlpatterns:
        route = str(pattern.pattern)
        # Rewrite Django converters into the contract's own placeholder.
        for converter in ("<uuid:section_id>", "<uuid:student_id>"):
            route = route.replace(converter, "{id}")
        assert f"/{route}" in contracted, route


def test_the_fixture_policy_grants_no_wildcard():
    """Standalone must not become allow-all by way of a convenient fixture.

    A wildcard here would mean every authorisation assertion in this module's
    suite passed without the policy path ever making a decision.
    """
    from modules.registry.fixture_policy import FIXTURE_POLICY_RULES

    assert FIXTURE_POLICY_RULES
    for rule in FIXTURE_POLICY_RULES:
        assert "*" not in rule.action
        assert rule.action.strip() == rule.action


def test_sensitive_writes_demand_a_recent_second_factor():
    """The reviewed 300-second step-up is enforced by the fixture policy."""
    from datetime import timedelta

    from modules.registry.fixture_policy import FIXTURE_POLICY_RULES

    by_action = {rule.action: rule for rule in FIXTURE_POLICY_RULES}
    for action in ("students.update", "guardians.manage"):
        assert by_action[action].max_auth_age == timedelta(seconds=300), action
