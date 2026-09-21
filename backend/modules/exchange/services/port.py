"""In-process ExchangePort implementation.

Thin on purpose: it is the seam other modules bind to, and every decision it
makes already lives in ReportCardService. Keeping it a forwarder means the HTTP
surface and the port surface cannot authorise differently.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contracts.exchange import ArtifactAccessDTO, ReportJobStartDTO
from contracts.identity import RequestContext

from .reportcards import ReportCardService


@dataclass(frozen=True, slots=True)
class ExchangeService:
    """Concrete ExchangePort for in-process consumers such as M05 publication."""

    report_cards: ReportCardService

    def request_report(
        self,
        ctx: RequestContext,
        kind: str,
        source_refs: list[dict],
        locale: str,
        template_version: str,
    ) -> ReportJobStartDTO:
        """Enqueue report generation and return the first job's handle.

        Does not handle: waiting. The caller polls, then asks for the artifact.
        """
        return self.report_cards.request_report(
            ctx, kind, source_refs, locale, template_version
        )

    def get_artifact(self, ctx: RequestContext, job_id: UUID) -> ArtifactAccessDTO:
        """Return a short-lived authorised read URL for a finished job.

        Re-checks Access and the relationship, so a caller that held a job id
        from before a guardianship lapsed still gets 403.
        """
        return self.report_cards.get_artifact(ctx, job_id)
