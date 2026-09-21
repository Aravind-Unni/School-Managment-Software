"""Acceptance cases: validate, commit integrity, exports, reports, isolation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from shared import fixtures
from shared.harness.models import HarnessOutboxEvent

pytestmark = [pytest.mark.module]

#: The Malayalam word for the language. Asserted inside the report-card bytes.
MALAYALAM = "മലയാളം"

#: The instant the suite's clock is frozen at, matching conftest.
FROZEN_INSTANT = datetime(2026, 9, 21, 4, 30, tzinfo=UTC)


def post_json(client, url: str, payload: dict, **extra):
    """POST a JSON body the way the real client sends it."""
    return client.post(url, data=json.dumps(payload), content_type="application/json", **extra)


def create_import(client, baseline, *, dataset: str = "enrolments"):
    """Create and validate one import job; return the create response body."""
    response = post_json(
        client,
        "/api/v1/imports",
        {"dataset": dataset, "file_ref": baseline["import_file_id"], "mode": "validate"},
    )
    assert response.status_code == 201, response.content
    return response.json()


def generate_report_card(client, baseline, *, locale: str = "ml"):
    """Generate one report card for S1 and return its finished job body."""
    response = post_json(
        client,
        "/api/v1/reportcards",
        {
            "publication_id": baseline["publication_id"],
            "student_ids": [baseline["student_s1_id"]],
            "locale": locale,
            "template_version": "report-card-v1",
        },
    )
    assert response.status_code == 202, response.content
    return response.json()["jobs"][0]


def commit(client, job_id, *, digest, version, key="commit-key-1"):
    """POST a commit with an Idempotency-Key and return the response."""
    return post_json(
        client,
        f"/api/v1/imports/{job_id}/commit",
        {"validation_version": version, "source_digest": digest},
        HTTP_IDEMPOTENCY_KEY=key,
    )


# --- validation ------------------------------------------------------------


def test_duplicate_and_malformed_rows_are_reported(client, baseline):
    """The repeat key is a duplicate_row error and the short row a malformed one."""
    created = create_import(client, baseline)
    job = client.get(f"/api/v1/imports/{created['job_id']}").json()
    assert job["state"] == "validated"
    assert job["accepted_count"] == 2

    errors = client.get(f"/api/v1/imports/{created['job_id']}/errors").json()["items"]
    codes = {(item["row"], item["code"]) for item in errors}
    assert (2, "duplicate_row") in codes, codes
    assert (4, "malformed_row") in codes, codes
    assert all(item["message_key"].startswith("exchange.error.") for item in errors)
    assert all(item["field"] for item in errors)


def test_formula_cell_is_neutralized_and_never_a_formula_error(client, baseline):
    """Row 3's '=1+1' is stored with a leading tab and the row survives.

    The grammar still reports the cell as an invalid date, because
    ``effective_from`` is a date column. What must not happen — and does not —
    is a rejection for the cell merely looking like a formula, or the row being
    dropped from the file.
    """
    from modules.exchange.models import ImportRow

    created = create_import(client, baseline)
    row = ImportRow.objects.get(job_id=UUID(created["job_id"]), number=3)
    assert row.payload["effective_from"] == "\t=1+1"
    assert [error["code"] for error in row.validation_errors] == ["invalid_date"]

    errors = client.get(f"/api/v1/imports/{created['job_id']}/errors").json()["items"]
    assert not any("formula" in item["code"] for item in errors)


def test_neutralisation_is_idempotent_and_reversible():
    """Validating twice cannot stack prefixes, and the key strips back cleanly."""
    from modules.exchange.services import csv_safe

    once = csv_safe.neutralize("=1+1")
    assert once == "\t=1+1"
    assert csv_safe.neutralize(once) == once
    assert csv_safe.strip_neutralization(once) == "=1+1"
    assert csv_safe.neutralize("2026-07-15") == "2026-07-15"


def test_unknown_dataset_is_rejected(client, baseline):
    """A dataset outside the allowlist is 422, not a job that never finishes."""
    response = post_json(
        client,
        "/api/v1/imports",
        {"dataset": "payroll", "file_ref": baseline["import_file_id"], "mode": "validate"},
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "error.validation_failed"


# --- commit integrity -------------------------------------------------------


def test_changed_digest_blocks_commit(client, baseline):
    """A commit quoting a different digest is refused and the job stays validated."""
    created = create_import(client, baseline)
    job = client.get(f"/api/v1/imports/{created['job_id']}").json()
    response = commit(
        client,
        created["job_id"],
        digest=baseline["wrong_digest"],
        version=job["validation_version"],
    )
    assert response.status_code == 409, response.content
    body = response.json()
    assert body["code"] == "state_conflict"
    assert body["message_key"] == "exchange.error.digest_mismatch"
    after = client.get(f"/api/v1/imports/{created['job_id']}").json()
    assert after["state"] == "validated"
    assert after["applied_count"] == 0


def test_stale_validation_version_is_a_version_conflict(client, baseline):
    """A commit quoting an older validation_version is 409 version_conflict."""
    created = create_import(client, baseline)
    response = commit(
        client, created["job_id"], digest=baseline["import_file_digest"], version=99
    )
    assert response.status_code == 409
    assert response.json()["message_key"] == "error.version_conflict"


def test_commit_requires_an_idempotency_key(client, baseline):
    """A commit with no Idempotency-Key is refused before anything is applied."""
    created = create_import(client, baseline)
    job = client.get(f"/api/v1/imports/{created['job_id']}").json()
    response = post_json(
        client,
        f"/api/v1/imports/{created['job_id']}/commit",
        {
            "validation_version": job["validation_version"],
            "source_digest": baseline["import_file_digest"],
        },
    )
    assert response.status_code == 422
    assert client.get(f"/api/v1/imports/{created['job_id']}").json()["applied_count"] == 0


def test_resume_applies_each_row_once(client, baseline):
    """Replaying the same commit key does not apply a single row twice."""
    from modules.exchange.adapters import adapter_for
    from modules.exchange.models import CommitBatch

    created = create_import(client, baseline)
    job = client.get(f"/api/v1/imports/{created['job_id']}").json()
    first = commit(
        client,
        created["job_id"],
        digest=baseline["import_file_digest"],
        version=job["validation_version"],
    )
    assert first.status_code == 202, first.content
    assert client.get(f"/api/v1/imports/{created['job_id']}").json()["applied_count"] == 2

    adapter = adapter_for("enrolments", "import")
    batches = CommitBatch.objects.filter(job_id=UUID(created["job_id"]))
    assert batches.count() == 2, "one accepted row per batch, so a resume has work to skip"
    applied_once = sum(1 for name, _args, _kwargs in adapter.calls if name == "apply_rows")
    placements = dict(adapter.placements)

    second = commit(
        client,
        created["job_id"],
        digest=baseline["import_file_digest"],
        version=job["validation_version"],
    )
    assert second.status_code == 202, second.content
    assert client.get(f"/api/v1/imports/{created['job_id']}").json()["applied_count"] == 2
    assert batches.count() == 2
    assert adapter.placements == placements
    replayed = sum(1 for name, _args, _kwargs in adapter.calls if name == "apply_rows")
    assert replayed == applied_once, "a replayed commit must not re-enter the domain adapter"


def test_commit_emits_import_completed_once_applied(client, baseline):
    """A finished commit appends exchange.import_completed with the real counts."""
    created = create_import(client, baseline)
    job = client.get(f"/api/v1/imports/{created['job_id']}").json()
    commit(
        client,
        created["job_id"],
        digest=baseline["import_file_digest"],
        version=job["validation_version"],
    )
    event = HarnessOutboxEvent.objects.get(
        event_type="exchange.import_completed", aggregate_id=UUID(created["job_id"])
    )
    assert event.payload["applied_count"] == 2
    assert event.payload["error_count"] >= 2
    assert event.school_id == fixtures.SCHOOL_A


def test_transaction_rollback_drops_the_outbox_row(client, baseline):
    """An outbox row written in a rolled-back transaction does not survive."""
    from django.db import transaction

    from modules.exchange.api import deps

    created = create_import(client, baseline)
    before = HarnessOutboxEvent.objects.filter(event_type="exchange.import_completed").count()

    class Rollback(RuntimeError):
        """Local sentinel, so the rollback is deliberate and not an incidental error."""

    with pytest.raises(Rollback), transaction.atomic():
        deps.import_service().apply_commit(UUID(created["job_id"]), "rollback-key")
        raise Rollback("force rollback after the event was appended")

    assert (
        HarnessOutboxEvent.objects.filter(event_type="exchange.import_completed").count()
        == before
    )


# --- exports ---------------------------------------------------------------


def create_export(client, baseline, *, dataset="class_roster", fields=None, fmt="csv"):
    """Create one export job and return its body."""
    response = post_json(
        client,
        "/api/v1/exports",
        {
            "dataset": dataset,
            "filters": {
                "section_id": baseline["section_c1_id"],
                "publication_id": baseline["publication_id"],
            },
            "fields": fields or ["student_id", "display_name"],
            "format": fmt,
            "locale": "en",
        },
    )
    assert response.status_code == 202, response.content
    return response.json()


def artifact_bytes(job_id: UUID) -> bytes:
    """Return the stored bytes for a finished export job."""
    from modules.exchange.models import ExportJob
    from modules.exchange.services.blobs import artifact_key, artifact_store

    row = ExportJob.objects.get(id=job_id)
    return artifact_store().get(artifact_key(row.school_id, row.id))


def test_forbidden_fields_are_omitted_from_the_file(client, baseline):
    """A withheld column is absent from the bytes, not blanked."""
    from modules.exchange.adapters import adapter_for
    from modules.exchange.models import ExportJob

    adapter = adapter_for("class_roster", "export")
    withheld = list(adapter.forbidden_fields)
    assert withheld, "the roster dataset must withhold something for this to mean anything"

    job = create_export(
        client,
        baseline,
        fields=["student_id", "display_name", *withheld],
    )
    row = ExportJob.objects.get(id=UUID(job["id"]))
    assert row.field_grants == ["student_id", "display_name"]
    assert row.requested_fields == ["student_id", "display_name", *withheld]

    body = artifact_bytes(row.id).decode("utf-8")
    header = body.splitlines()[0]
    assert header == "student_id,display_name"
    for name in withheld:
        assert name not in body


def test_an_export_of_only_forbidden_fields_is_refused(client, baseline):
    """Asking for nothing exportable is 422, not a silently empty file."""
    from modules.exchange.adapters import adapter_for

    withheld = list(adapter_for("class_roster", "export").forbidden_fields)
    response = post_json(
        client,
        "/api/v1/exports",
        {
            "dataset": "class_roster",
            "filters": {"section_id": baseline["section_c1_id"]},
            "fields": withheld,
            "format": "csv",
            "locale": "en",
        },
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "exchange.error.forbidden_field"


def test_export_csv_escapes_formula_cells():
    """A cell that would run as a formula is written as text."""
    from modules.exchange.services import csv_safe

    rendered = csv_safe.write_rows(
        ["student_id", "note"],
        [
            {"student_id": "S1", "note": "=cmd|'/c calc'!A1"},
            {"student_id": "S2", "note": "@SUM"},
        ],
    )
    assert "\t=cmd" in rendered
    assert "\t@SUM" in rendered
    cells = [cell for line in rendered.splitlines() for cell in line.split(",")]
    assert not any(cell.startswith(("=", "+", "@")) for cell in cells)


def test_export_download_returns_a_short_lived_url(client, baseline, clock):
    """A ready export hands back an authorised read URL that expires."""
    job = create_export(client, baseline)
    response = client.get(f"/api/v1/exports/{job['id']}/download")
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["authorized_read_url"]
    assert datetime.fromisoformat(body["expires_at"]) > clock.now()


def test_download_of_an_unfinished_export_is_a_state_conflict(client, baseline):
    """Downloading while the job is still processing is 409 job_not_ready."""
    from modules.exchange.models import ExportJob, JobState

    job = create_export(client, baseline)
    ExportJob.objects.filter(id=UUID(job["id"])).update(state=JobState.PROCESSING)
    response = client.get(f"/api/v1/exports/{job['id']}/download")
    assert response.status_code == 409
    assert response.json()["message_key"] == "exchange.error.job_not_ready"


def test_a_guardian_cannot_download_a_whole_section_export(client, baseline, as_persona):
    """An export is staff work; a guardian is refused even for their own child's class."""
    job = create_export(client, baseline)
    as_persona(fixtures.GUARDIAN_G1)
    response = client.get(f"/api/v1/exports/{job['id']}/download")
    assert response.status_code == 403
    assert response.json()["message_key"] == "error.action_denied"


def test_at_risk_export_reports_indicators_without_a_verdict(client, baseline):
    """The at-risk sheet names its threshold policy and labels no child."""
    from modules.exchange.adapters import adapter_for

    adapter = adapter_for("at_risk", "export")
    fields = [name for name in adapter.export_fields if name not in adapter.forbidden_fields]
    job = create_export(client, baseline, dataset="at_risk", fields=fields)
    body = artifact_bytes(UUID(job["id"])).decode("utf-8")
    assert "not_assessed" in body


# --- report cards and snapshots --------------------------------------------


def read_snapshot(client, as_persona, report_id):
    """Read a snapshot as C1's class teacher, who may see S1's card."""
    as_persona(fixtures.TEACHER_T1)
    response = client.get(f"/api/v1/reports/{report_id}")
    assert response.status_code == 200, response.content
    as_persona(fixtures.PRINCIPAL_P1)
    return response.json()


def test_report_card_binds_the_published_revision(client, baseline, as_persona):
    """The snapshot names the result revision and policy version it was built from."""
    job = generate_report_card(client, baseline)
    assert job["state"] == "ready", job

    snapshot = read_snapshot(client, as_persona, job["report_id"])
    assert snapshot["source_revision_ids"] == [baseline["result_revision_id_s1"]]
    assert snapshot["policy_versions"] == [baseline["policy_version_v1"]]
    assert snapshot["locale"] == "ml"
    assert snapshot["state"] == "ready"
    assert snapshot["superseded_by"] is None
    assert HarnessOutboxEvent.objects.filter(
        event_type="exchange.report_ready", aggregate_id=UUID(job["report_id"])
    ).exists()


def test_malayalam_reaches_the_pdf_bytes(client, baseline):
    """The rendered artifact carries Malayalam text, not a transliteration."""
    from modules.exchange.fixture_ids import malayalam_name
    from modules.exchange.models import ReportSnapshot
    from modules.exchange.services.blobs import artifact_key, artifact_store

    job = generate_report_card(client, baseline, locale="ml")
    snapshot = ReportSnapshot.objects.get(id=UUID(job["report_id"]))
    body = artifact_store().get(artifact_key(snapshot.school_id, snapshot.id))
    assert body.startswith(b"%PDF-")
    assert MALAYALAM.encode("utf-8") in body
    assert malayalam_name(fixtures.STUDENT_S1).encode("utf-8") in body


def test_historical_snapshot_is_unchanged_after_a_policy_edit(client, baseline, as_persona):
    """Publishing policy v2 does not move what snapshot v1 says it bound."""
    from modules.exchange.seeds import reseed_published_results_v2

    job = generate_report_card(client, baseline)
    before = read_snapshot(client, as_persona, job["report_id"])

    version_two = reseed_published_results_v2()
    assert version_two != baseline["policy_version_v1"]

    after = read_snapshot(client, as_persona, job["report_id"])
    assert after == before


def test_supersede_creates_a_new_snapshot_and_links_the_old(
    client, baseline, as_persona, context_for
):
    """A replacement is a new row; the old one is retired and points at it."""
    from modules.exchange.api import deps
    from modules.exchange.models import Supersession
    from modules.exchange.seeds import reseed_published_results_v2

    job = generate_report_card(client, baseline)
    old_id = UUID(job["report_id"])
    version_two = reseed_published_results_v2()

    new = deps.report_card_service().supersede(
        context_for(fixtures.PRINCIPAL_P1), old_id, reason="policy revision"
    )
    assert new["id"] != str(old_id)
    assert new["policy_versions"] == [version_two]

    old = read_snapshot(client, as_persona, old_id)
    assert old["state"] == "superseded"
    assert old["superseded_by"] == new["id"]
    assert old["policy_versions"] == [baseline["policy_version_v1"]]
    linked = Supersession.objects.filter(old_report_id=old_id, new_report_id=UUID(new["id"]))
    assert linked.count() == 1
    assert HarnessOutboxEvent.objects.filter(event_type="exchange.report_superseded").exists()


def test_a_superseded_card_is_still_downloadable(client, baseline, as_persona, context_for):
    """History is not hidden: the card that was issued can still be fetched."""
    from modules.exchange.api import deps
    from modules.exchange.seeds import reseed_published_results_v2

    job = generate_report_card(client, baseline)
    reseed_published_results_v2()
    deps.report_card_service().supersede(
        context_for(fixtures.PRINCIPAL_P1), UUID(job["report_id"]), reason="policy revision"
    )
    as_persona(fixtures.GUARDIAN_G1)
    response = client.get(f"/api/v1/reports/{job['report_id']}/download")
    assert response.status_code == 200, response.content


# --- access, relationships and isolation ------------------------------------


def test_related_guardian_can_download_a_report(client, baseline, as_persona):
    """G1, who guards S1, gets an authorised read URL for S1's card."""
    job = generate_report_card(client, baseline)
    as_persona(fixtures.GUARDIAN_G1)
    response = client.get(f"/api/v1/reports/{job['report_id']}/download")
    assert response.status_code == 200, response.content
    assert response.json()["authorized_read_url"]


def test_unrelated_guardian_is_denied_the_download(client, baseline, as_persona):
    """G2, who does not guard S1, gets 403 artifact_access_revoked and no URL."""
    job = generate_report_card(client, baseline)
    as_persona(fixtures.GUARDIAN_G2)
    response = client.get(f"/api/v1/reports/{job['report_id']}/download")
    assert response.status_code == 403, response.content
    body = response.json()
    assert body["code"] == "action_denied"
    assert body["message_key"] == "exchange.error.artifact_access_revoked"
    assert "authorized_read_url" not in body


def test_an_unassigned_teacher_is_denied_a_report_card(client, baseline, as_persona):
    """T2 teaches nothing, so no relationship carries S1's card to them."""
    job = generate_report_card(client, baseline)
    as_persona(fixtures.TEACHER_T2)
    response = client.get(f"/api/v1/reports/{job['report_id']}/download")
    assert response.status_code == 403
    assert response.json()["message_key"] == "exchange.error.artifact_access_revoked"


def test_a_guardian_cannot_reach_the_bulk_import_surface(client, baseline, as_persona):
    """A non-staff actor is refused a staff-wide action outright."""
    as_persona(fixtures.GUARDIAN_G1)
    response = post_json(
        client,
        "/api/v1/imports",
        {"dataset": "enrolments", "file_ref": baseline["import_file_id"], "mode": "validate"},
    )
    assert response.status_code == 403
    assert response.json()["message_key"] == "error.action_denied"


def test_two_school_isolation_is_404(client, baseline):
    """A School B job id is absent from School A, and answers 404 not 403."""
    from modules.exchange.models import ImportJob, ImportJobState

    foreign = ImportJob.objects.create(
        school_id=UUID(baseline["other_school_id"]),
        actor_id=fixtures.TEACHER_T1_SCHOOL_B,
        dataset="enrolments",
        file_ref=UUID(baseline["foreign_file_id"]),
        state=ImportJobState.VALIDATED,
        source_digest=baseline["import_file_digest"],
        validation_version=1,
        template_version="enrolments-v1",
        schema_version="enrolments-schema-v1",
        created_at=FROZEN_INSTANT,
        updated_at=FROZEN_INSTANT,
    )
    response = client.get(f"/api/v1/imports/{foreign.id}")
    assert response.status_code == 404
    assert response.json()["message_key"] == "error.object_inaccessible"

    commit_attempt = commit(
        client, foreign.id, digest=baseline["import_file_digest"], version=1
    )
    assert commit_attempt.status_code == 404


def test_a_report_card_for_another_school_pupil_is_404(client, baseline):
    """Generating for a School B pupil is absent, not denied."""
    response = post_json(
        client,
        "/api/v1/reportcards",
        {
            "publication_id": baseline["publication_id"],
            "student_ids": [str(fixtures.STUDENT_S1_SCHOOL_B)],
            "locale": "en",
            "template_version": "report-card-v1",
        },
    )
    assert response.status_code == 404
    assert response.json()["message_key"] == "error.object_inaccessible"


def test_an_absent_report_is_404(client, baseline):
    """An unknown report id is indistinguishable from another school's."""
    response = client.get(f"/api/v1/reports/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["message_key"] == "error.object_inaccessible"


def test_a_server_internal_field_in_the_body_is_refused(client, baseline):
    """A body carrying school_id is 422 at the boundary, before any service runs."""
    response = post_json(
        client,
        "/api/v1/imports",
        {
            "dataset": "enrolments",
            "file_ref": baseline["import_file_id"],
            "mode": "validate",
            "school_id": str(fixtures.SCHOOL_B),
        },
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "error.server_internal_field_rejected"


def test_fees_ledger_writes_are_refused_from_reporting_code(baseline):
    """A report may read a balance; posting to the ledger raises explicitly."""
    from modules.exchange.adapters import ExplicitlyUnused, adapter_for

    adapter = adapter_for("ptm_summary", "export")
    for operation in ("raise_charge", "credit_charge"):
        with pytest.raises(ExplicitlyUnused):
            adapter.refuse_ledger_write(operation)


def test_the_module_reads_no_other_business_module(baseline):
    """M13 imports contracts and shared only; a domain import would be a breach."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[3] / "backend" / "modules" / "exchange"
    offenders = []
    for path in root.rglob("*.py"):
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith(("import modules.", "from modules.")) and (
                "modules.exchange" not in stripped
            ):
                offenders.append(f"{path.name}: {stripped}")
    assert offenders == []
