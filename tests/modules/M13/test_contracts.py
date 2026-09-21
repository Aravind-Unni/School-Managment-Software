"""M13 contract suite: schema validity, fixture sanity and registration agreement."""

from __future__ import annotations

import json
import pathlib
import uuid

import jsonschema
import pytest

from modules.exchange.permissions import PERMISSION_CODES
from modules.exchange.registration import REGISTRATION

pytestmark = [pytest.mark.contract, pytest.mark.module]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
M13 = REPO_ROOT / "contracts" / "M13"


def load_json(relative: str) -> dict:
    """Load one of M13's JSON contract documents."""
    return json.loads((M13 / relative).read_text())


def test_dto_schema_is_valid():
    """DTO schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/dtos.schema.json"))


def test_event_schema_is_valid():
    """Event schema validates as Draft 2020-12."""
    jsonschema.Draft202012Validator.check_schema(load_json("schemas/events.schema.json"))


def test_every_scenario_uuid_parses():
    """Scenario ids must be real UUIDs.

    This test exists because three of them were not: a nine-character first
    group parses nowhere and would have failed at the first seed.
    """
    scenario = load_json("fixtures/scenario.json")["school_a"]
    for key, value in scenario.items():
        if key.endswith("_id") and "digest" not in key:
            uuid.UUID(value)


def test_response_fixtures_match_required_dto_keys():
    """Consumer examples carry every required key of the DTO they illustrate."""
    schema = load_json("schemas/dtos.schema.json")["$defs"]
    examples = load_json("fixtures/responses.json")["examples"]
    pairs = (
        ("ImportJobDTO", "import_job_validated"),
        ("ExportJobDTO", "export_job_ready"),
        ("ReportSnapshotDTO", "report_snapshot_ready"),
        ("ArtifactAccessDTO", "artifact_access"),
        ("CreateImportResponse", "create_import_validate"),
    )
    for definition, example in pairs:
        for key in schema[definition]["required"]:
            assert key in examples[example], (definition, key)


def test_event_fixtures_validate_against_the_event_schema():
    """Every example event payload validates against its frozen schema."""
    events = load_json("schemas/events.schema.json")["$defs"]
    examples = load_json("fixtures/responses.json")["examples"]["events"]
    for name, payload in examples.items():
        jsonschema.Draft202012Validator(events[name]).validate(payload)


def test_permission_codes_match_registration():
    """Backend permission list matches ModuleRegistration, and owns its prefixes."""
    assert set(PERMISSION_CODES) == set(REGISTRATION.permission_codes)
    assert REGISTRATION.owned_permission_prefixes == frozenset(
        {"imports.", "reports.", "reportcards."}
    )


def test_registration_declares_the_contracted_consumers():
    """Consumers match the packet: no performance port, no object storage."""
    assert set(REGISTRATION.consumers) == {
        "access",
        "registry",
        "assessment",
        "attendance",
        "fees",
        "files",
        "platform",
        "clock",
    }
    assert "performance" not in REGISTRATION.consumers


def test_openapi_lists_contract_operations():
    """Frozen OpenAPI exposes exactly the packet's paths."""
    paths = load_json("openapi.json")["paths"]
    for route in (
        "/imports",
        "/imports/{id}",
        "/imports/{id}/commit",
        "/imports/{id}/errors",
        "/import-templates/{dataset}",
        "/exports",
        "/exports/{id}",
        "/exports/{id}/download",
        "/reportcards",
        "/reportcards/{id}",
        "/reports/{id}",
        "/reports/{id}/download",
    ):
        assert route in paths, route


def test_url_patterns_cover_every_openapi_path():
    """Every frozen path is mounted; an unrouted contract path is a silent 404."""
    from modules.exchange.urls import urlpatterns

    mounted = {str(pattern.pattern) for pattern in urlpatterns}
    for route in (
        "imports",
        "imports/<uuid:job_id>",
        "imports/<uuid:job_id>/commit",
        "imports/<uuid:job_id>/errors",
        "import-templates/<str:dataset>",
        "exports",
        "exports/<uuid:job_id>",
        "exports/<uuid:job_id>/download",
        "reportcards",
        "reportcards/<uuid:job_id>",
        "reports/<uuid:report_id>",
        "reports/<uuid:report_id>/download",
    ):
        assert route in mounted, route


def test_dataset_allowlists_match_the_frozen_enums():
    """Adapter registry and the frozen DTO enums name the same datasets."""
    from modules.exchange.adapters import export_datasets, import_datasets

    schema = load_json("schemas/dtos.schema.json")["$defs"]
    assert set(import_datasets()) == set(schema["ImportDataset"]["enum"])
    assert set(export_datasets()) == set(schema["ExportDataset"]["enum"])


def test_error_codes_used_by_the_module_are_declared():
    """Every module-owned message key the code raises appears in error-codes.json."""
    from modules.exchange.adapters.registry import UNKNOWN_DATASET
    from modules.exchange.services.authority import ARTIFACT_ACCESS_REVOKED
    from modules.exchange.services.exports import FORBIDDEN_FIELD
    from modules.exchange.services.imports import DIGEST_MISMATCH, JOB_NOT_READY

    declared = {row["message_key"] for row in load_json("error-codes.json")["rows"]}
    for key in (
        ARTIFACT_ACCESS_REVOKED,
        FORBIDDEN_FIELD,
        DIGEST_MISMATCH,
        JOB_NOT_READY,
        UNKNOWN_DATASET,
    ):
        assert key in declared, key


def test_exchange_port_exports():
    """ExchangePort and its DTOs are exported from contracts."""
    from contracts import ArtifactAccessDTO, ExchangePort, ReportJobStartDTO

    assert ExchangePort is not None
    assert ArtifactAccessDTO is not None
    assert ReportJobStartDTO is not None


def test_the_in_process_provider_satisfies_the_port():
    """ExchangeService structurally satisfies the runtime-checkable Protocol."""
    from contracts import ExchangePort
    from modules.exchange.services.port import ExchangeService

    assert issubclass(ExchangeService, ExchangePort)


def test_adapters_satisfy_the_module_local_port():
    """Every registered adapter satisfies DomainExchangePort."""
    from modules.exchange.adapters import (
        DomainExchangePort,
        adapter_for,
        export_datasets,
        import_datasets,
    )

    for dataset in import_datasets():
        assert isinstance(adapter_for(dataset, "import"), DomainExchangePort)
    for dataset in export_datasets():
        assert isinstance(adapter_for(dataset, "export"), DomainExchangePort)


def test_report_job_start_rejects_a_state_outside_the_enum():
    """A DTO cannot be built in a state the frozen schema would reject."""
    from contracts import ReportJobStartDTO

    with pytest.raises(ValueError, match="queued or processing"):
        ReportJobStartDTO(job_id=uuid.uuid4(), state="ready")
