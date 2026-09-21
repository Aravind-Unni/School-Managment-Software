"""DTO serialisation helpers for files API and port responses."""

from __future__ import annotations

from contracts.files import FileDTO

from ..models import File, PurgeJob, UploadSession


def file_to_dto(row: File) -> FileDTO:
    """Map a File row to the frozen FileDTO (without rejection_reason)."""
    return FileDTO(
        id=row.id,
        school_id=row.school_id,
        state=row.state,
        review_confirmed=row.review_confirmed,
        canonical_version=row.canonical_version,
        sha256=row.sha256,
        bytes=row.byte_size,
        width=row.width,
        height=row.height,
        profile_version=row.profile_version,
    )


def file_to_wire(row: File) -> dict:
    """Serialise FileDTO shape including rejection_reason for HTTP."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "state": row.state,
        "canonical_version": row.canonical_version,
        "sha256": row.sha256,
        "bytes": row.byte_size,
        "width": row.width,
        "height": row.height,
        "profile_version": row.profile_version,
        "review_confirmed": row.review_confirmed,
        "rejection_reason": row.rejection_reason,
    }


def upload_session_to_wire(row: UploadSession, upload_url: str) -> dict:
    """Serialise UploadSessionDTO."""
    return {
        "id": str(row.id),
        "upload_url": upload_url,
        "expires_at": row.expires_at.isoformat().replace("+00:00", "Z"),
        "max_bytes": row.max_bytes,
    }


def purge_job_to_wire(row: PurgeJob) -> dict:
    """Serialise PurgeJobDTO."""
    return {
        "id": str(row.id),
        "source_id": str(row.source_id),
        "state": row.state,
        "block_reason": row.block_reason,
    }
