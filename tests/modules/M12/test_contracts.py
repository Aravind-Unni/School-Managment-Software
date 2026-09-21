"""M12 contract suite: schema validity and registration agreement."""

from __future__ import annotations

import json
import pathlib

import jsonschema
import pytest

from modules.files.permissions import PERMISSION_CODES
from modules.files.registration import REGISTRATION

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M12 = REPO_ROOT / "contracts" / "M12"


def load_json(relative: str) -> dict:
    """Load one of M12's JSON contract documents."""
    return json.loads((M12 / relative).read_text())


def test_dto_schema_is_valid():
    """DTO schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_event_schema_is_valid():
    """Event schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_response_fixtures_match_required_keys():
    """Consumer examples carry required FileDTO / UploadSessionDTO keys."""
    schema = load_json("schemas/dtos.schema.json")
    file_dto = schema["$defs"]["FileDTO"]
    upload = schema["$defs"]["UploadSessionDTO"]
    fixtures = load_json("fixtures/responses.json")["examples"]
    for key in file_dto["required"]:
        assert key in fixtures["file_candidate_ready"]
    for key in upload["required"]:
        assert key in fixtures["upload_session"]


def test_permission_codes_match_registration():
    """Backend permission list matches ModuleRegistration."""
    assert set(PERMISSION_CODES) == set(REGISTRATION.permission_codes)
    assert set(REGISTRATION.consumers) == {"access", "platform", "clock"}


def test_openapi_lists_contract_operations():
    """Frozen OpenAPI exposes the packet operations."""
    paths = load_json("openapi.json")["paths"]
    assert "/uploads" in paths
    assert "/uploads/{id}/complete" in paths
    assert "/files/{id}/status" in paths
    assert "/files/{id}/quality-confirmation" in paths
    assert "/files/{id}/reprocess" in paths
    assert "/files/{id}/retention-hold" in paths


def test_event_names_are_envelope_safe():
    """Event types match the frozen lowercase dotted pattern."""
    events = load_json("schemas/events.schema.json")["$defs"]
    assert "files.candidate_ready" in events
    assert "files.accepted" in events
    assert "files.rejected" in events
    assert "files.source_purged" in events


def test_files_port_exports():
    """FilesPort and DTOs are exported from contracts."""
    from contracts import FileDTO, FileEvidenceRef, FilesPort, UploadSession

    assert FilesPort is not None
    assert FileDTO is not None
    assert FileEvidenceRef is not None
    assert UploadSession is not None
