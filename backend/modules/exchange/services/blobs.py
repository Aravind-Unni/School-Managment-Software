"""Process-local byte staging for import sources and generated artifacts.

Why this exists, stated plainly so the next agent does not mistake it for a
design choice: the frozen ``FilesPort`` has no method that returns the BYTES of
a stored file. It can open an upload, report status, pin evidence, mint a read
URL and store an artifact from a ``content_ref`` — but an import worker needs to
read the CSV it is validating, and a download endpoint needs the artifact bytes
behind the URL it minted.

So M13 stages bytes here, exactly as M12's own ``memory_store`` does for its
in-process profile, and passes the staging key to
``FilesPort.store_artifact(content_ref=...)``. The real M12 provider resolves
that same ``content_ref`` against object storage, so the call shape is the one
integration will use.

Recorded as an open contract question in docs/modules/M13/handoff.md: either
FilesPort grows a byte-read method, or M13 declares the object_storage consumer.
Until that is reviewed, this module is the seam.

Does not handle: persistence across processes. A worker in another process sees
an empty store, which is correct for standalone and is why the integrated
profile must not rely on it.
"""

from __future__ import annotations

import hashlib


class ByteStore:
    """A dictionary of key to bytes, with digests computed on write."""

    def __init__(self, name: str) -> None:
        """Build an empty store. ``name`` appears in key errors."""
        self._name = name
        self._objects: dict[str, bytes] = {}

    def put(self, key: str, body: bytes) -> str:
        """Store bytes under a key and return their sha256 hex digest."""
        self._objects[key] = body
        return hashlib.sha256(body).hexdigest()

    def get(self, key: str) -> bytes:
        """Return stored bytes, or raise KeyError naming the store and key."""
        try:
            return self._objects[key]
        except KeyError as exc:
            raise KeyError(f"{self._name} has no object {key!r}") from exc

    def exists(self, key: str) -> bool:
        """Return whether a key is present."""
        return key in self._objects

    def clear(self) -> None:
        """Drop every object. Used by the baseline seed to stay deterministic."""
        self._objects.clear()

    def keys(self) -> tuple[str, ...]:
        """Return every key, sorted, for isolation assertions."""
        return tuple(sorted(self._objects))


_SOURCES = ByteStore("exchange source store")
_ARTIFACTS = ByteStore("exchange artifact store")


def source_store() -> ByteStore:
    """Return the staged bytes of uploaded import sources."""
    return _SOURCES


def artifact_store() -> ByteStore:
    """Return the staged bytes of generated exports and reports."""
    return _ARTIFACTS


def source_key(school_id, file_ref) -> str:
    """Return the staging key for one school's import source file."""
    return f"import-source/{school_id}/{file_ref}"


def artifact_key(school_id, job_id) -> str:
    """Return the staging key for one school's generated artifact."""
    return f"artifact/{school_id}/{job_id}"


def digest_of(body: bytes) -> str:
    """Return the sha256 hex digest of a byte string."""
    return hashlib.sha256(body).hexdigest()
