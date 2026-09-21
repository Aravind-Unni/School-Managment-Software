"""Baseline seed for M13: policy, a staged import CSV, and published results.

Everything here is synthetic and deterministic. The import CSV deliberately
contains the two shapes the packet calls out — a duplicated enrolment row and a
cell that looks like a formula — plus one malformed row, because a seed that
only holds clean data cannot demonstrate the behaviour the module exists for.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from django.conf import settings

from shared import fixtures
from shared.ports import runtime

from .adapters.registry import reset_adapters
from .fixture_ids import load_scenario
from .models import (
    CommitBatch,
    ExchangePolicy,
    ExportJob,
    ImportJob,
    ImportRow,
    ReportCardJob,
    ReportSnapshot,
    Supersession,
)
from .services.blobs import artifact_store, source_key, source_store

FROZEN_INSTANT = datetime(2026, 9, 21, 4, 30, tzinfo=UTC)

#: The enrolments CSV the baseline stages. Row 1 is clean, row 2 repeats row 1's
#: key, row 3 carries the frozen fixture's formula cell, row 4 is short, row 5 is
#: clean. Two clean rows and a one-row commit chunk are what let the resume test
#: span more than one CommitBatch.
ENROLMENTS_HEADER = "student_id,section_id,effective_from"

#: Rows one CommitBatch covers in the baseline. One, so a commit of the two
#: accepted rows writes two batches and a resumed commit has something to skip.
BASELINE_CHUNK_ROWS = 1


def _enrolments_csv() -> str:
    r"""Return the synthetic enrolments CSV, including its deliberate defects.

    The formula cell is ``=1+1`` in ``effective_from``, copied from the frozen
    scenario fixture. Neutralisation stores it as ``\t=1+1`` and raises no
    formula error; the enrolments grammar separately reports it as an invalid
    date, which is recorded as an open question in the module's handoff.
    """
    s1 = fixtures.STUDENT_S1
    s2 = fixtures.STUDENT_S2
    s3 = fixtures.STUDENT_S3
    c1 = fixtures.CLASS_C1
    c2 = fixtures.CLASS_C2
    day = fixtures.TERM_SAMPLE_DATE.isoformat()
    return "\n".join(
        [
            ENROLMENTS_HEADER,
            f"{s1},{c1},{day}",
            f"{s1},{c1},{day}",
            f"{s2},{c1},=1+1",
            f"{s2},{c1}",
            f"{s3},{c2},{day}",
            "",
        ]
    )


def _clear(school_ids: list[UUID]) -> None:
    """Drop every M13 row for the named schools and reset process state."""
    for model in (
        CommitBatch,
        ImportRow,
        ImportJob,
        ExportJob,
        Supersession,
        ReportSnapshot,
        ReportCardJob,
        ExchangePolicy,
    ):
        model.objects.filter(school_id__in=school_ids).delete()
    source_store().clear()
    artifact_store().clear()
    reset_adapters()


def _seed_published_results(ports, scenario: dict, school_id: UUID) -> None:
    """Install S1's published results on FakeAssessment at policy version v1.

    ``result_revision_id`` and ``policy_version`` are what the report snapshot
    binds, so they come from the frozen scenario rather than being generated.
    """
    school_a = scenario["school_a"]
    ports.resolve("assessment").seed_published_results(
        student_id=UUID(school_a["student_s1_id"]),
        school_id=school_id,
        term_id=UUID(school_a["publication_id"]),
        items=[
            {
                "subject_id": str(fixtures.SUBJECT_MALAYALAM),
                "marks_obtained": "78.50",
                "result_revision_id": school_a["result_revision_id_s1"],
                "policy_version": school_a["policy_version_v1"],
                "state": "published",
            }
        ],
    )


def _seed_attendance(ports, school_id: UUID) -> None:
    """Install period attendance for S1 and S2 so exports have rows to render."""
    from contracts.timetable import AttendanceSummaryDTO

    attendance = ports.resolve("attendance")
    day = fixtures.TERM_SAMPLE_DATE
    for student_id, present, absent in (
        (fixtures.STUDENT_S1, 6, 1),
        (fixtures.STUDENT_S2, 5, 2),
    ):
        attendance.seed_summary(
            AttendanceSummaryDTO(
                unit="period",
                student_id=student_id,
                from_date=day,
                to_date=day,
                eligible=8,
                marked=present + absent,
                present=present,
                absent=absent,
                late=0,
                excused=0,
                unmarked=8 - (present + absent),
                updated_at=FROZEN_INSTANT,
                subject_id=None,
                percentage=None,
                policy_version=None,
            ),
            school_id=school_id,
        )


def seed_baseline(*, school_id: UUID | None = None) -> dict[str, object]:
    """Load the contracted M13 baseline and return the ids a test needs.

    Seeds, in order: the fixture policy for School A and School B, the staged
    enrolments CSV with its digest registered on FakeFiles, S1's published
    results at policy version v1, and period attendance for the C1 roster.

    Does not handle: a mid-commit import job. Every test that needs one creates
    it by actually committing, because a hand-built half-committed row would
    not prove the resume path.
    """
    school = school_id or fixtures.SCHOOL_A
    scenario = load_scenario()
    policy_fx = scenario["policy_fixture"]
    school_a = scenario["school_a"]
    other_school = fixtures.SCHOOL_B
    _clear([school, other_school])

    for sid in (school, other_school):
        ExchangePolicy.objects.create(
            school_id=sid,
            formula_neutralization_prefix=policy_fx["formula_neutralization_prefixes"][0],
            malayalam_pdf_font_bundle=policy_fx["malayalam_pdf_font_bundle"],
            signed_read_seconds=policy_fx["signed_read_seconds"],
            commit_requires_2fa=policy_fx["commit_requires_2fa"],
            commit_chunk_rows=BASELINE_CHUNK_ROWS,
        )

    body = _enrolments_csv().encode("utf-8")
    file_ref = UUID(school_a["import_file_id"])
    digest = source_store().put(source_key(school, file_ref), body)

    ports = runtime.get_registry()
    files = ports.resolve("files")
    files.seed_file(
        file_id=file_ref,
        school_id=school,
        purpose="import_source",
        state="accepted",
        review_confirmed=True,
        canonical_version=1,
        sha256=digest,
        bytes_count=len(body),
    )
    foreign_ref = UUID(scenario["school_a"]["export_job_id"])
    files.seed_file(
        file_id=foreign_ref,
        school_id=other_school,
        purpose="import_source",
        state="accepted",
        review_confirmed=True,
        canonical_version=1,
        sha256=digest,
        bytes_count=len(body),
    )

    _seed_published_results(ports, scenario, school)
    _seed_attendance(ports, school)
    settings.SCHOOL_CLOCK.set(FROZEN_INSTANT)

    return {
        "school_id": str(school),
        "other_school_id": str(other_school),
        "import_file_id": str(file_ref),
        "import_file_digest": digest,
        "foreign_file_id": str(foreign_ref),
        "wrong_digest": scenario["commit_mismatch"]["wrong_digest"],
        "publication_id": school_a["publication_id"],
        "result_revision_id_s1": school_a["result_revision_id_s1"],
        "policy_version_v1": school_a["policy_version_v1"],
        "policy_version_v2": school_a["policy_version_v2"],
        "student_s1_id": str(fixtures.STUDENT_S1),
        "student_s2_id": str(fixtures.STUDENT_S2),
        "section_c1_id": str(fixtures.CLASS_C1),
        "principal_actor_id": str(fixtures.PRINCIPAL_P1),
        "teacher_t1_id": str(fixtures.TEACHER_T1),
        "guardian_g1_id": str(fixtures.GUARDIAN_G1),
        "guardian_g2_id": str(fixtures.GUARDIAN_G2),
        "csv_rows": 5,
        "accepted_rows": 2,
        "commit_chunk_rows": BASELINE_CHUNK_ROWS,
    }


def reseed_published_results_v2(*, school_id: UUID | None = None) -> str:
    """Re-seed S1's published results at policy version v2 and return it.

    Used to prove a historical snapshot does not move: after this call the
    source data says v2, and the v1 snapshot must still say v1.
    """
    school = school_id or fixtures.SCHOOL_A
    scenario = load_scenario()
    school_a = scenario["school_a"]
    version_two = school_a["policy_version_v2"]
    runtime.get_registry().resolve("assessment").seed_published_results(
        student_id=UUID(school_a["student_s1_id"]),
        school_id=school,
        term_id=UUID(school_a["publication_id"]),
        items=[
            {
                "subject_id": str(fixtures.SUBJECT_MALAYALAM),
                "marks_obtained": "81.00",
                "result_revision_id": school_a["result_revision_id_s1"],
                "policy_version": version_two,
                "state": "published",
            }
        ],
    )
    return version_two


def empty(*, school_id: UUID | None = None) -> dict[str, object]:
    """No-op empty scenario."""
    return {"school_id": str(school_id or fixtures.SCHOOL_A)}


SCENARIOS = {"baseline": seed_baseline, "empty": empty}
