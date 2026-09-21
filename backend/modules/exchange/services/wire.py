"""ORM row to contracted DTO shapes. One place, so two endpoints cannot drift."""

from __future__ import annotations

from ..models import ExportJob, ImportJob, ImportRow, ReportCardJob, ReportSnapshot


def import_job_to_wire(row: ImportJob) -> dict:
    """Serialise an ImportJob to the frozen ImportJobDTO shape."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "dataset": row.dataset,
        "state": row.state,
        "file_ref": str(row.file_ref),
        "validation_version": row.validation_version,
        "source_digest": row.source_digest,
        "accepted_count": row.accepted_count,
        "error_count": row.error_count,
        "applied_count": row.applied_count,
        "template_version": row.template_version,
        "schema_version": row.schema_version,
    }


def import_row_errors(row: ImportRow) -> list[dict]:
    """Return one row's errors in the frozen ImportRowErrorDTO shape.

    ``message_key`` is derived from the adapter's code so the frontend never
    has to render a raw code, and so a new code cannot ship without a key.
    """
    return [
        {
            "row": error["row"],
            "field": error["field"],
            "code": error["code"],
            "message_key": f"exchange.error.{error['code']}",
        }
        for error in row.validation_errors
    ]


def export_job_to_wire(row: ExportJob) -> dict:
    """Serialise an ExportJob to the frozen ExportJobDTO shape."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "dataset": row.dataset,
        "format": row.format,
        "locale": row.locale,
        "state": row.state,
        "artifact_ref": str(row.artifact_file_id) if row.artifact_file_id else None,
        "failure_message_key": row.failure_message_key,
    }


def report_card_job_to_wire(row: ReportCardJob) -> dict:
    """Serialise a ReportCardJob to the frozen ReportCardJobDTO shape."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "publication_id": str(row.publication_id),
        "student_id": str(row.student_id),
        "locale": row.locale,
        "template_version": row.template_version,
        "state": row.state,
        "report_id": str(row.report_id) if row.report_id else None,
    }


def report_snapshot_to_wire(row: ReportSnapshot) -> dict:
    """Serialise a ReportSnapshot to the frozen ReportSnapshotDTO shape.

    ``artifact_ref`` is the stored file id. The snapshot keeps the whole
    ArtifactRef (version and digest included) internally; the wire shape is a
    bare uuid because that is what the frozen schema declares.
    """
    return {
        "id": str(row.id),
        "type": row.type,
        "source_revision_ids": list(row.source_revision_ids),
        "policy_versions": list(row.policy_versions),
        "locale": row.locale,
        "artifact_ref": str(row.artifact_ref.get("file_id", "")),
        "state": row.state,
        "superseded_by": str(row.superseded_by) if row.superseded_by else None,
    }
