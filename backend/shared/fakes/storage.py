"""In-memory fake ObjectStoragePort with real grant enforcement.

Keeps bytes in a dict, but still enforces the school prefix and the grant
expiry, because those are the rules a module can get wrong. A fake that skipped
grant checks would let a module ship an unauthorised download path.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from contracts.errors import ActionDenied
from contracts.evidence import EvidenceRef, ResourceGrant
from contracts.identity import RequestContext

from .failures import FailureInjector


class FakeObjectStorage:
    """Dictionary-backed private storage.

    Object keys are forced under ``schools/<school_id>/`` so a test cannot
    accidentally assert against a cross-tenant key.
    """

    def __init__(self, *, failures: FailureInjector | None = None) -> None:
        """Build empty storage."""
        self._objects: dict[str, bytes] = {}
        self._failures = failures or FailureInjector()

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
        """Store bytes under the school prefix and return an EvidenceRef.

        Raises ValueError when ``storage_key`` is already absolute or escapes
        the prefix. The returned ref carries the real sha256 of ``body`` so
        integrity assertions are meaningful.
        """
        self._failures.maybe_fail("storage.put")
        prefix = self.school_prefix(context.school_id)
        full_key = storage_key if storage_key.startswith(prefix) else prefix + storage_key
        if ".." in full_key or full_key.startswith("/"):
            raise ValueError(f"unsafe storage key {storage_key!r}")
        self._objects[full_key] = body
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
        """Return a fake URL, after enforcing the grant.

        Raises ActionDenied when the grant is expired, belongs to another
        school, or points at a different resource. These are exactly the
        mistakes a module makes when it treats a grant as a formality.
        """
        self._failures.maybe_fail("storage.signed_read_url")
        now = datetime.now(UTC)
        if not grant.is_valid_at(now):
            raise ActionDenied("error.grant_expired")
        if grant.school_id != ref.school_id:
            raise ActionDenied("error.grant_school_mismatch")
        if grant.resource_id != ref.evidence_id:
            raise ActionDenied("error.grant_resource_mismatch")
        return (
            f"memory://{ref.storage_key}?grant={grant.grant_id}&expires_in={expires_in_seconds}"
        )

    def read(self, ref: EvidenceRef) -> bytes:
        """Return stored bytes directly. Test-only helper, bypasses grants."""
        return self._objects[ref.storage_key]

    def keys(self) -> tuple[str, ...]:
        """Return every stored key, for isolation assertions."""
        return tuple(sorted(self._objects))
