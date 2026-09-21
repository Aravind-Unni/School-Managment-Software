"""S3-compatible ObjectStoragePort for integrated runs (host-owned).

Lives under ``config/`` rather than ``shared/`` so it may use boto3 without
pulling business-module imports into the shared harness purity boundary.
"""

from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from contracts.errors import ActionDenied
from contracts.evidence import EvidenceRef, ResourceGrant
from contracts.identity import RequestContext


@dataclass
class _MemoryObjectStore:
    """Process-local byte store when MinIO is not configured."""

    _objects: dict[str, bytes] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def put(
        self, key: str, body: bytes, *, content_type: str = "application/octet-stream"
    ) -> None:
        """Store bytes under key."""
        del content_type
        with self._lock:
            self._objects[key] = body

    def presigned_get(self, key: str, *, expires_in: int) -> str:
        """Return a memory URL stand-in."""
        return f"memory://{key}?expires_in={expires_in}"


@dataclass
class _S3ObjectStore:
    """Minimal S3-compatible client for ObjectStoragePort."""

    endpoint: str
    bucket: str
    access_key: str
    secret_key: str

    def _client(self):
        """Build a boto3 client."""
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    def put(
        self, key: str, body: bytes, *, content_type: str = "application/octet-stream"
    ) -> None:
        """Put object into the configured bucket."""
        self._client().put_object(
            Bucket=self.bucket, Key=key, Body=body, ContentType=content_type
        )

    def presigned_get(self, key: str, *, expires_in: int) -> str:
        """Return a signed GET URL."""
        return self._client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )


class S3ObjectStorageAdapter:
    """ObjectStoragePort backed by OBJECT_STORAGE_* settings or memory."""

    def __init__(self) -> None:
        """Select memory or S3 from the environment."""
        endpoint = os.environ.get("OBJECT_STORAGE_ENDPOINT", "").strip()
        if endpoint:
            self._store = _S3ObjectStore(
                endpoint=endpoint,
                bucket=os.environ.get("OBJECT_STORAGE_BUCKET", "school-files"),
                access_key=os.environ.get("OBJECT_STORAGE_ACCESS_KEY", ""),
                secret_key=os.environ.get("OBJECT_STORAGE_SECRET_KEY", ""),
            )
            self._backend = "s3"
        else:
            self._store = _MemoryObjectStore()
            self._backend = "memory"

    @staticmethod
    def school_prefix(school_id) -> str:
        """Return the mandatory key prefix for a school's private objects."""
        return f"schools/{school_id}/"

    def put(
        self,
        context: RequestContext,
        *,
        storage_key: str,
        content_type: str,
        body: bytes,
    ) -> EvidenceRef:
        """Store bytes under the school prefix and return an EvidenceRef."""
        prefix = self.school_prefix(context.school_id)
        full_key = storage_key if storage_key.startswith(prefix) else prefix + storage_key
        if ".." in full_key or full_key.startswith("/"):
            raise ValueError(f"unsafe storage key {storage_key!r}")
        self._store.put(full_key, body, content_type=content_type)
        return EvidenceRef(
            evidence_id=uuid4(),
            school_id=context.school_id,
            storage_key=full_key,
            content_type=content_type,
            byte_size=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
            uploaded_at=datetime.now(UTC),
        )

    def signed_read_url(
        self,
        ref: EvidenceRef,
        *,
        grant: ResourceGrant,
        expires_in_seconds: int,
    ) -> str:
        """Mint a short-lived read URL after enforcing the grant."""
        now = datetime.now(UTC)
        if not grant.is_valid_at(now):
            raise ActionDenied("error.grant_expired")
        if grant.school_id != ref.school_id:
            raise ActionDenied("error.grant_school_mismatch")
        if grant.resource_id != ref.evidence_id:
            raise ActionDenied("error.grant_resource_mismatch")
        return self._store.presigned_get(ref.storage_key, expires_in=expires_in_seconds)
