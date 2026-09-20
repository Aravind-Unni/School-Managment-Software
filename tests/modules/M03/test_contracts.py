"""M03 contract suite: schema validity, fixtures, and code/contract agreement.

Runs with no database and no containers, so it is the fastest signal that
something structural broke. These assertions are about the FROZEN artefacts in
contracts/M03 and whether the code still serves them -- not about behaviour,
which the other files in this directory cover.
"""

from __future__ import annotations

import ast
import json
import pathlib
from datetime import timedelta

import jsonschema
import pytest

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M03 = REPO_ROOT / "contracts" / "M03"
BACKEND_MODULE = REPO_ROOT / "backend" / "modules" / "timetable"


def load_json(relative: str) -> dict:
    """Load one of M03's JSON contract documents."""
    return json.loads((M03 / relative).read_text())


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
    examples = load_json("fixtures/responses.json")["examples"]
    assert examples, "the fixture file must carry examples"
    for example in examples:
        selected = {"$defs": schema["$defs"], "$ref": f"#/$defs/{example['schema']}"}
        jsonschema.Draft202012Validator(
            selected, format_checker=jsonschema.FormatChecker()
        ).validate(example["body"])


def test_every_event_fixture_validates_against_the_frozen_envelope_and_its_payload():
    """The envelope is the foundation's; only the payload is this module's."""
    envelope = json.loads(
        (REPO_ROOT / "contracts" / "common" / "event-envelope.schema.json").read_text()
    )
    payloads = load_json("schemas/events.schema.json")
    events = load_json("fixtures/responses.json")["events"]
    assert events, "both emitted events must have an example"
    for event in events:
        jsonschema.Draft202012Validator(
            envelope, format_checker=jsonschema.FormatChecker()
        ).validate(event["body"])
        name = event["payload_schema"].split("#/$defs/")[1]
        jsonschema.Draft202012Validator(
            {"$defs": payloads["$defs"], "$ref": f"#/$defs/{name}"},
            format_checker=jsonschema.FormatChecker(),
        ).validate(event["body"]["payload"])


# --- closed write shapes ---------------------------------------------------


def test_every_object_definition_refuses_unknown_fields():
    """An undeclared field must be a 422, never a silently ignored value."""
    schema = load_json("schemas/dtos.schema.json")
    for name, definition in schema["$defs"].items():
        if definition.get("type") != "object":
            continue
        assert definition.get("additionalProperties") is False, name


def test_no_write_shape_accepts_a_client_supplied_school_id_or_version():
    """Identity is server state. A create never takes an id, school or version."""
    schema = load_json("schemas/dtos.schema.json")
    creates = (
        "CreateTimetableRequest",
        "CalendarExceptionRequest",
        "TeacherUnavailableRequest",
        "SubstitutionRequest",
        "PeriodTemplateRequest",
        "SlotRequest",
    )
    for name in creates:
        properties = schema["$defs"][name].get("properties", {})
        assert "school_id" not in properties, name
        assert "id" not in properties, name
        assert "version" not in properties, name


def test_every_update_shape_requires_expected_version():
    """A write without optimistic locking silently overwrites a concurrent one."""
    schema = load_json("schemas/dtos.schema.json")
    updates = (
        "ReplaceTimetableRequest",
        "PublishRequest",
        "UpdateCalendarExceptionRequest",
        "UpdateTeacherUnavailableRequest",
        "UpdateSubstitutionRequest",
        "SessionCancellationRequest",
    )
    for name in updates:
        assert "expected_version" in schema["$defs"][name]["required"], name


# --- events ----------------------------------------------------------------


def test_event_names_satisfy_the_frozen_envelope_pattern():
    """The packet's TimetablePublished.v1 does not; review item 1 chose to conform."""
    import re

    envelope = json.loads(
        (REPO_ROOT / "contracts" / "common" / "event-envelope.schema.json").read_text()
    )
    pattern = re.compile(envelope["properties"]["event_type"]["pattern"])
    names = load_json("schemas/events.schema.json")["$defs"].keys()
    assert set(names) == {"timetable.published", "timetable.substitution_assigned"}
    for name in names:
        assert pattern.match(name), name


# --- error taxonomy --------------------------------------------------------


def test_every_error_row_reuses_a_frozen_error_code_with_its_frozen_status():
    """A module may add message keys. It may not add a code or remap a status."""
    from contracts.errors import HTTP_STATUS_BY_CODE, ErrorCode

    by_value = {str(code): code for code in ErrorCode}
    for row in load_json("error-codes.json")["rows"]:
        code = by_value.get(row["code"])
        assert code is not None, row
        # The one deliberate exception: the shared middleware renders a spoofed
        # identity header as 400 while carrying validation_failed, before any
        # module code runs.
        if row["message_key"] == "error.client_asserted_identity":
            assert row["status"] == 400
            continue
        assert row["status"] == HTTP_STATUS_BY_CODE[code], row


def test_module_message_keys_are_namespaced():
    """A bare key would collide with another module's in the frontend catalogue."""
    for row in load_json("error-codes.json")["rows"]:
        key = row["message_key"]
        assert key.startswith("error.") or key.startswith("timetable.error."), key


def test_conflict_codes_agree_between_the_error_rows_and_the_dto_enum():
    """Two lists of the same closed set drift; this is what notices."""
    rows = {row["code"] for row in load_json("error-codes.json")["conflict_codes"]}
    enum = set(
        load_json("schemas/dtos.schema.json")["$defs"]["ConflictDTO"]["properties"]["code"][
            "enum"
        ]
    )
    assert rows == enum


def test_exactly_one_conflict_code_is_non_blocking():
    """Review item 4: teacher_not_assigned reports, everything else blocks."""
    rows = load_json("error-codes.json")["conflict_codes"]
    non_blocking = [row["code"] for row in rows if not row["blocking"]]
    assert non_blocking == ["teacher_not_assigned"]


# --- registration agrees with the contract ---------------------------------


def test_the_registration_declares_every_permission_the_openapi_requires():
    """An endpoint asking for a permission the module never declared cannot be granted."""
    from modules.timetable.registration import REGISTRATION

    required = {
        operation["x-permission"]
        for path in load_json("openapi.json")["paths"].values()
        for operation in path.values()
    }
    assert required <= set(REGISTRATION.permission_codes)


def test_every_openapi_path_falls_under_a_declared_api_path_root():
    """Otherwise the host's collision check never examines the path at all."""
    from modules.timetable.registration import REGISTRATION

    roots = tuple(root.rstrip("/") for root in REGISTRATION.api_path_roots)
    for path in load_json("openapi.json")["paths"]:
        assert path.lstrip("/").split("/")[0] in roots, path


def test_the_registration_declares_exactly_the_ports_this_module_uses():
    """Declaring an unused consumer claims capability that was never tested."""
    from modules.timetable.registration import REGISTRATION

    assert set(REGISTRATION.consumers) == {"access", "registry", "platform", "clock"}


def test_the_module_declares_no_broker_and_no_worker():
    """M03 owns no asynchronous work. Declaring one would start a broker for nothing."""
    declaration = json.loads(
        (REPO_ROOT / "dev" / "modules" / "M03" / "module.json").read_text()
    )
    assert declaration["resources"]["broker"] is False
    assert declaration["resources"]["worker"] is False

    from modules.timetable.registration import REGISTRATION

    assert REGISTRATION.scheduled_jobs == ()


# --- authorisation fixtures ------------------------------------------------


def test_the_fixture_policy_is_enumerated_and_has_no_allow_all():
    """Deny by default is the property. A wildcard rule would erase it."""
    from modules.timetable.fixture_policy import FIXTURE_POLICY_RULES

    actions = [rule.action for rule in FIXTURE_POLICY_RULES]
    assert actions, "standalone would 403 on every endpoint without fixture grants"
    assert len(actions) == len(set(actions))
    for action in actions:
        assert action.startswith("timetable."), action


def test_publication_is_the_only_action_requiring_a_fresh_second_factor():
    """Review item 11: step-up on publish, not on daily substitution work."""
    from contracts.identity import AuthLevel
    from modules.timetable.fixture_policy import FIXTURE_POLICY_RULES

    stepped_up = {
        rule.action
        for rule in FIXTURE_POLICY_RULES
        if rule.minimum_auth_level is AuthLevel.TWO_FACTOR
    }
    assert stepped_up == {"timetable.publish"}
    publish = next(r for r in FIXTURE_POLICY_RULES if r.action == "timetable.publish")
    assert publish.max_auth_age == timedelta(seconds=300)


def test_section_scoped_reads_are_relationship_gated():
    """A school-scoped read rule would let any actor read any class's schedule."""
    from modules.timetable.fixture_policy import FIXTURE_POLICY_RULES

    by_action = {rule.action: rule for rule in FIXTURE_POLICY_RULES}
    for action in ("timetable.read_section", "timetable.read_student"):
        assert by_action[action].allowed_relationships, action


# --- boundaries ------------------------------------------------------------


def test_the_module_imports_no_other_business_module():
    """The architecture check enforces this repo-wide; this names it for M03."""
    offenders: list[str] = []
    for path in sorted(BACKEND_MODULE.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            for name in names:
                if name.startswith("modules.") and not name.startswith("modules.timetable"):
                    offenders.append(f"{path.name}: {name}")
    assert offenders == []


def test_the_module_never_reads_the_wall_clock():
    """Decision logic takes the instant as an argument. A global clock is untestable."""
    offenders: list[str] = []
    for path in sorted(BACKEND_MODULE.rglob("*.py")):
        if "migrations" in path.parts:
            continue
        source = path.read_text()
        for marker in ("datetime.now(", "date.today(", "timezone.now("):
            if marker in source:
                offenders.append(f"{path.name}: {marker}")
    assert offenders == []


def test_m03_is_frozen_in_the_manifest():
    """Implementation may only follow a recorded review decision."""
    manifest = json.loads((REPO_ROOT / "contracts" / "manifest.json").read_text())
    entry = manifest["modules"]["M03"]
    assert entry["status"] == "frozen"
    assert entry["review"]["reviewer"]
    assert all(artefact["frozen"] for artefact in entry["artefacts"])
