"""Exchange DTOs and port owned by M13, consumed by modules that need reports.

Frozen under ``school-contracts-v14`` (``contracts/M13/ports.md`` section 1 and
``contracts/M13/schemas/dtos.schema.json``). M05 publication calls
``request_report`` for asynchronous report-card generation rather than building
PDFs itself.

Does not handle: the module-local ``DomainExchangePort`` adapter registry. That
is deliberately NOT here: adapters are an implementation detail of M13 and a
shared Protocol would invite other modules to register their own.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from .identity import RequestContext


@dataclass(frozen=True, slots=True)
class ReportJobStartDTO:
    """Acknowledgement that a report job was accepted for background work.

    ``state`` is ``queued`` or ``processing`` only. A finished report is never
    reported here: the caller polls the job, which is what keeps the caller from
    blocking on PDF generation.
    """

    job_id: UUID
    state: str

    def __post_init__(self) -> None:
        """Reject a state outside the frozen enum.

        Failing at construction means an implementation cannot return a state
        the consumer's schema would reject at the wire boundary.
        """
        if self.state not in ("queued", "processing"):
            raise ValueError(f"report job state must be queued or processing: {self.state!r}")

    def to_wire(self) -> dict[str, object]:
        """Serialise to the contracted ReportJobStartDTO shape."""
        return {"job_id": str(self.job_id), "state": self.state}


@dataclass(frozen=True, slots=True)
class ArtifactAccessDTO:
    """A short-lived authorised read URL for one generated artifact.

    Minted only after the provider has re-run its Access check. The URL is the
    whole grant: it is short-lived rather than revocable, so a consumer must not
    cache or forward it.
    """

    authorized_read_url: str
    expires_at: datetime

    def to_wire(self) -> dict[str, object]:
        """Serialise to the contracted ArtifactAccessDTO shape."""
        return {
            "authorized_read_url": self.authorized_read_url,
            "expires_at": self.expires_at.isoformat().replace("+00:00", "Z"),
        }


@runtime_checkable
class ExchangePort(Protocol):
    """Reports, imports and exports. Owned by M13 exchange.

    Report snapshots bind publication revision ids immutably: a later policy
    revision produces a NEW snapshot that supersedes the old one, and never
    edits the old one's bound ids.

    Implementations must not accept browser-supplied ResourceGrant values;
    ``get_artifact`` mints its own grant after re-checking Access.
    """

    def request_report(
        self,
        ctx: RequestContext,
        kind: str,
        source_refs: list[dict],
        locale: str,
        template_version: str,
    ) -> ReportJobStartDTO:
        """Enqueue generation of one report and return its job handle.

        ``kind`` must be in the frozen report dataset allowlist and
        ``source_refs`` names the publication and students the report binds.

        Does not handle: waiting for the artifact. Poll the job, then call
        ``get_artifact``.
        """
        ...

    def get_artifact(self, ctx: RequestContext, job_id: UUID) -> ArtifactAccessDTO:
        """Return a short-lived authorised read URL for a finished job.

        Re-checks Access and the actor-to-subject relationship at call time, so
        a link issued before a guardianship lapsed cannot be reissued after.

        Raises ObjectInaccessible (404) for an unknown or other-school job,
        StateConflict (409) when the job is not ready, and ActionDenied (403)
        when the relationship no longer grants read.
        """
        ...
