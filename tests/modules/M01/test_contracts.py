"""M01 contract suite: schema validity, seed/implementation agreement, fixtures.

Runs with no database and no containers, so it is the fastest signal that something
structural broke.
"""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest
import yaml

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M01 = REPO_ROOT / "contracts" / "M01"


def load_yaml(name: str) -> dict:
    """Load one of M01's YAML contract documents."""
    return yaml.safe_load((M01 / name).read_text())


def load_json(relative: str) -> dict:
    """Load one of M01's JSON contract documents."""
    return json.loads((M01 / relative).read_text())


# --- schema validity -------------------------------------------------------


def test_the_dto_schema_is_itself_a_valid_json_schema():
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_every_write_dto_refuses_unknown_fields():
    """An undeclared field must be a 422, never a silently ignored value."""
    defs = load_json("schemas/dtos.schema.json")["$defs"]
    writes = [name for name in defs if name.endswith("Request")]
    assert writes, "no request DTOs found"
    for name in writes:
        assert defs[name].get("additionalProperties") is False, name


def test_the_error_code_table_only_uses_contracted_statuses():
    from contracts.errors import HTTP_STATUS_BY_CODE, ErrorCode

    rows = load_json("error-codes.json")["responses"]
    assert rows
    for row in rows:
        code = ErrorCode(row["code"])
        assert HTTP_STATUS_BY_CODE[code] == row["status"], row


def test_every_message_key_is_namespaced():
    for row in load_json("error-codes.json")["responses"]:
        assert row["message_key"].startswith("error."), row


# --- the seed and the implementation must agree ----------------------------


def test_the_generated_openapi_covers_exactly_the_specified_operations():
    """The seed was written BEFORE the code; the code must match it.

    This is what makes "specify in OpenAPI before coding" more than a gesture: a
    path added without specifying it, or specified and never built, fails here.
    """
    generated = load_yaml("openapi.yaml")
    seed = load_yaml("openapi-seed.yaml")
    built = {
        (method, path.replace("/api/v1", ""))
        for path, methods in generated["paths"].items()
        for method in methods
    }
    specified = {
        (method, path) for path, methods in seed["paths"].items() for method in methods
    }
    assert specified - built == set(), f"specified but not implemented: {specified - built}"
    assert built - specified == set(), f"implemented but not specified: {built - specified}"


def test_every_operation_declares_a_success_and_an_unauthenticated_response():
    for path, methods in load_yaml("openapi.yaml")["paths"].items():
        for method, operation in methods.items():
            codes = set(operation["responses"])
            assert codes & {"200", "201"}, (method, path)
            assert "401" in codes, (method, path)


def test_the_permission_codes_match_the_registration():
    from modules.access.permissions import CATALOGUE
    from modules.access.registration import REGISTRATION

    assert set(REGISTRATION.permission_codes) == {spec.code for spec in CATALOGUE}


def test_the_declared_api_path_roots_cover_every_url():
    """A new path root must be declared, or collision checking cannot see it."""
    from modules.access.registration import REGISTRATION
    from modules.access.urls import urlpatterns

    # Roots carry a trailing slash ("auth/"); a route's first segment does not
    # ("auth/login" -> "auth"). Compare on the first segment.
    roots = {root.rstrip("/") for root in REGISTRATION.api_path_roots}
    for pattern in urlpatterns:
        route = str(pattern.pattern)
        first_segment = route.split("/")[0]
        assert first_segment in roots, f"{route} is outside declared roots {sorted(roots)}"


def test_the_declared_public_paths_match_the_middleware():
    from modules.access.middleware import PUBLIC_SUFFIXES
    from modules.access.registration import REGISTRATION

    assert set(REGISTRATION.public_paths) == set(PUBLIC_SUFFIXES)


# --- fixtures --------------------------------------------------------------


def test_the_persona_fixture_matches_what_the_seed_creates():
    """A documented id that the seed does not produce is worse than none."""
    from modules.access import seeds

    personas = load_json("fixtures/personas.json")
    # The fixture file names accounts in upper case for readability (O1, T1); the
    # seed derives ids from the lower-case label. Normalise rather than duplicating
    # the cast in two cases.
    for label, account in personas["accounts"].items():
        assert account["id"] == str(seeds._account_id(label.lower())), label
    for label, role in personas["roles"].items():
        assert role["id"] == str(seeds._role_id(label.lower())), label


def test_the_used_recovery_code_fixture_matches_the_seed():
    from modules.access.seeds import USED_RECOVERY_CODE

    personas = load_json("fixtures/personas.json")
    assert personas["preloaded_state"]["used_recovery_code"]["code"] == USED_RECOVERY_CODE


def test_the_two_factor_policy_is_recorded_as_proposed_not_approved():
    """A fixture cannot activate a production policy."""
    policy = load_json("fixtures/personas.json")["_two_factor_policy"]
    assert "PROPOSED" in policy["status"]
    assert "OFF" in policy["parent_student"]
    assert policy["all_account_types_may_enrol"] is True


def test_every_acceptance_case_names_an_expected_outcome():
    cases = load_json("fixtures/expected-results.json")["cases"]
    assert len(cases) >= 18
    for case in cases:
        assert case.get("name")
        assert case.get("then"), case["name"]


# --- forbidden imports -----------------------------------------------------


def test_m01_imports_no_other_business_module():
    """M01 must reach other modules only through service ports."""
    import ast

    module_root = REPO_ROOT / "backend" / "modules" / "access"
    for source in module_root.rglob("*.py"):
        if "migrations" in source.parts:
            continue
        tree = ast.parse(source.read_text(), filename=str(source))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                if name.startswith("modules.") and not name.startswith("modules.access"):
                    raise AssertionError(f"{source}: forbidden import {name}")


def test_m01_does_not_bind_a_fake_access_adapter():
    """M01 IS Access, so it must not consume the access port."""
    from modules.access.registration import REGISTRATION

    assert "access" not in REGISTRATION.consumers
    assert "registry" in REGISTRATION.consumers


def test_no_source_file_logs_credential_material():
    """A grep-level guard against the mistake that cannot be undone."""
    module_root = REPO_ROOT / "backend" / "modules" / "access"
    forbidden = (
        "logger.info(secret",
        "print(secret",
        "logger.debug(password",
        "print(password",
    )
    for source in module_root.rglob("*.py"):
        text = source.read_text()
        for needle in forbidden:
            assert needle not in text, f"{source}: {needle}"
