"""Module-owned object store: boto3 when configured, else in-memory bytes."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field


@dataclass
class MemoryObjectStore:
    """Process-local byte store for SQLite tests and profiles without MinIO."""

    _objects: dict[str, bytes] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def put(
        self, key: str, body: bytes, *, content_type: str = "application/octet-stream"
    ) -> None:
        """Store bytes under key. content_type is recorded only for S3 path."""
        del content_type
        with self._lock:
            self._objects[key] = body

    def get(self, key: str) -> bytes:
        """Return bytes or raise KeyError."""
        with self._lock:
            return self._objects[key]

    def delete(self, key: str) -> None:
        """Remove key if present."""
        with self._lock:
            self._objects.pop(key, None)

    def exists(self, key: str) -> bool:
        """Return whether key is present."""
        with self._lock:
            return key in self._objects


@dataclass
class S3ObjectStore:
    """S3-compatible client against OBJECT_STORAGE_* settings."""

    endpoint: str
    bucket: str
    access_key: str
    secret_key: str

    def _client(self):
        """Build a boto3 client. Assumes credentials are present."""
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

    def get(self, key: str) -> bytes:
        """Get object bytes."""
        response = self._client().get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete(self, key: str) -> None:
        """Delete object; ignore missing."""
        try:
            self._client().delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            return

    def exists(self, key: str) -> bool:
        """Head object."""
        try:
            self._client().head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def presigned_put(self, key: str, *, expires_in: int) -> str:
        """Return a signed PUT URL for quarantine upload."""
        return self._client().generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
            HttpMethod="PUT",
        )

    def presigned_get(self, key: str, *, expires_in: int) -> str:
        """Return a signed GET URL for private read."""
        return self._client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )


_MEMORY = MemoryObjectStore()


def object_store():
    """Return the active store: S3 when OBJECT_STORAGE_ENDPOINT is set, else memory."""
    endpoint = os.environ.get("OBJECT_STORAGE_ENDPOINT", "").strip()
    if not endpoint:
        return _MEMORY
    return S3ObjectStore(
        endpoint=endpoint,
        bucket=os.environ.get("OBJECT_STORAGE_BUCKET", "school-files"),
        access_key=os.environ.get("OBJECT_STORAGE_ACCESS_KEY", ""),
        secret_key=os.environ.get("OBJECT_STORAGE_SECRET_KEY", ""),
    )


def memory_store() -> MemoryObjectStore:
    """Expose the shared memory store for tests that assert orphan cleanup."""
    return _MEMORY
