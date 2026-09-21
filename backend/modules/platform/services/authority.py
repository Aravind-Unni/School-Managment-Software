"""Authority helpers for platform operational endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ActionDenied
from contracts.identity import RequestContext
from contracts.scope import ScopeFacts
from contracts.values import school_date


@dataclass(frozen=True, slots=True)
class AuthorityGate:
    """Resolves Access for school-scoped platform actions."""

    access: object
    clock: object

    def effective_date(self) -> date:
        """Return Asia/Kolkata civil date from the injected clock."""
        return school_date(self.clock.now())

    def require_action(self, context: RequestContext, action: str) -> None:
        """Authorise a school-scoped staff or ops action."""
        self.access.check(
            context,
            action,
            ScopeFacts(
                resource_school_id=context.school_id,
                effective_date=self.effective_date(),
            ),
        )

    def require_backups_manage(self, context: RequestContext) -> None:
        """Authorise backups.manage, recent 2FA, and (optionally) ops identity.

        When ``PLATFORM_OPS_ACTOR_IDS`` is configured, only those accounts may
        manage backups even if a role grants backups.manage; when it is empty,
        the grant plus a fresh second factor is sufficient.
        """
        from django.conf import settings

        self.require_action(context, "backups.manage")
        self.access.require_recent_2fa(context, max_age_seconds=300)
        ops_actors = {str(a) for a in getattr(settings, "PLATFORM_OPS_ACTOR_IDS", ()) or ()}
        if ops_actors and str(context.actor_id) not in ops_actors:
            raise ActionDenied("platform.error.ops_identity_required")

    def same_school_or_404(self, context: RequestContext, school_id: UUID) -> None:
        """Raise ObjectInaccessible when the row's school differs."""
        from contracts.errors import ObjectInaccessible

        if school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
