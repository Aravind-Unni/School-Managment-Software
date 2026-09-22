"""GET /auth/capabilities: what the signed-in account may do, for the menu.

Navigation only. Every write is still authorised by AccessPort; this list lets
the shell hide links the account cannot use.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..scopes import ScopeType
from . import deps
from .auth_views import COMMON_ERRORS


class CapabilitiesView(APIView):
    """GET /auth/capabilities -- action codes the caller currently holds.

    Navigation-only surface. Authorisation still runs through AccessPort on every
    write; this list exists so the product shell can hide links the actor cannot
    use, not so the browser can grant itself power.
    """

    @extend_schema(
        operation_id="auth_capabilities",
        summary="List action codes the calling session holds",
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return distinct grant action codes for the caller."""
        context = deps.require_context(request)
        deps.require_session(request)
        grants = deps.access_service().held_grants(context)
        actions = sorted({grant.action for grant in grants})
        # Actions held only for oneself (a pupil) or one's own child: the shell
        # shows those only on pages built for families, never on staff tools.
        wide = {grant.action for grant in grants if grant.scope_type != ScopeType.SELF}
        self_only = sorted(set(actions) - wide)
        return Response({"actions": actions, "self_only_actions": self_only})
