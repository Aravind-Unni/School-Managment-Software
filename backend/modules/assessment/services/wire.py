"""Wire shapes for assessment API responses. Grade is always null."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..models import Assessment, EvidenceBinding, Result, ResultRevision


def format_mark(value: Decimal | None) -> str | None:
    """Render a mark as a contracted decimal-string, or None."""
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"


def format_weight(value: Decimal) -> str:
    """Render a component weight as a three-place decimal-string."""
    return f"{value.quantize(Decimal('0.001'))}"


def component_to_wire(component) -> dict[str, Any]:
    """Serialise one component."""
    return {
        "id": str(component.id),
        "max_score": format_mark(component.max_score),
        "weight": format_weight(component.weight),
        "topic": component.topic,
        "question_type": component.question_type,
    }


def assessment_to_wire(assessment: Assessment) -> dict[str, Any]:
    """Serialise one assessment with its components."""
    components = [component_to_wire(c) for c in assessment.components.all()]
    return {
        "id": str(assessment.id),
        "school_id": str(assessment.school_id),
        "version": assessment.version,
        "year_id": str(assessment.year_id),
        "term_id": str(assessment.term_id),
        "section_id": str(assessment.section_id),
        "subject_id": str(assessment.subject_id),
        "type": assessment.type,
        "max_score": format_mark(assessment.max_score),
        "policy_version": assessment.policy_version,
        "state": assessment.state,
        "components": components,
        "due_at": assessment.due_at.isoformat() if assessment.due_at else None,
    }


def evidence_to_wire(binding: EvidenceBinding) -> dict[str, Any]:
    """Serialise one evidence binding."""
    return {
        "binding_id": str(binding.id),
        "file_id": str(binding.file_id),
        "version": binding.file_version,
        "sha256": binding.sha256,
        "page_no": binding.page_no,
    }


def result_to_wire(
    result: Result,
    *,
    assessment: Assessment | None = None,
    revision_id=None,
    evidence: list[EvidenceBinding] | None = None,
) -> dict[str, Any]:
    """Serialise one result. Grade is always null until school policy exists."""
    assessment = assessment or result.assessment
    rev = revision_id or result.current_revision_id
    if rev is None:
        rev = result.id
    bindings = evidence
    if bindings is None:
        bindings = list(result.evidence_bindings.filter(revision_id__isnull=True))
        if not bindings and result.current_revision_id is not None:
            bindings = list(
                result.evidence_bindings.filter(revision_id=result.current_revision_id)
            )
    return {
        "result_id": str(result.id),
        "revision_id": str(rev),
        "assessment_id": str(assessment.id),
        "student_id": str(result.student_id),
        "subject_id": str(assessment.subject_id),
        "attempt_id": str(result.attempt_id),
        "version": result.version,
        "status": result.status,
        "marking_outcome": result.marking_outcome,
        "score": format_mark(result.score),
        "max_score": format_mark(assessment.max_score),
        "grade": None,
        "policy_version": assessment.policy_version,
        "evidence_refs": [evidence_to_wire(b) for b in bindings],
    }


def build_result_snapshot(result: Result, assessment: Assessment) -> dict[str, Any]:
    """Build the immutable JSON snapshot stored on a ResultRevision.

    Does not handle: grade letters — always null.
    """
    marks = [
        {
            "component_id": str(mark.component_id),
            "score": format_mark(mark.score),
        }
        for mark in result.marks.order_by("component_id")
    ]
    bindings = list(
        result.evidence_bindings.filter(revision_id__isnull=True).order_by("page_no")
    )
    if not bindings and result.current_revision_id is not None:
        bindings = list(
            result.evidence_bindings.filter(revision_id=result.current_revision_id).order_by(
                "page_no"
            )
        )
    evidence = [evidence_to_wire(b) for b in bindings]
    return {
        "result_id": str(result.id),
        "student_id": str(result.student_id),
        "attempt_id": str(result.attempt_id),
        "marking_outcome": result.marking_outcome,
        "score": format_mark(result.score),
        "max_score": format_mark(assessment.max_score),
        "grade": None,
        "policy_version": assessment.policy_version,
        "marks": marks,
        "evidence_refs": evidence,
    }


def publication_to_wire(
    publication_id,
    revision_ids: list,
    report_job_id: str,
) -> dict[str, Any]:
    """Serialise a publication response."""
    return {
        "publication_id": str(publication_id),
        "result_revision_ids": [str(r) for r in revision_ids],
        "report_job_id": report_job_id,
    }


def revision_snapshot_result(
    revision: ResultRevision, assessment: Assessment
) -> dict[str, Any]:
    """Rebuild a ResultDTO-shaped dict from a stored revision snapshot."""
    snap = revision.snapshot
    return {
        "result_id": snap["result_id"],
        "revision_id": str(revision.id),
        "assessment_id": str(assessment.id),
        "student_id": snap["student_id"],
        "subject_id": str(assessment.subject_id),
        "attempt_id": snap["attempt_id"],
        "version": 1,
        "status": "published",
        "marking_outcome": snap["marking_outcome"],
        "score": snap["score"],
        "max_score": snap["max_score"],
        "grade": None,
        "policy_version": snap["policy_version"],
        "evidence_refs": snap.get("evidence_refs", []),
    }
