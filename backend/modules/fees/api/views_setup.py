"""Fee setup endpoints the office uses day to day.

``GET /fee-heads`` lists the school's fee types with how much has been
charged, how much is still outstanding and how many pupils owe it.
``POST /fees/charge-classes`` charges one fee to every pupil currently in the
chosen classes, creating the fee type on first use. Running it again for the
same fee and due date charges only pupils who were not charged yet (new
admissions), so it is safe to repeat.

Does not handle: different amounts within one class (charge those pupils from
the collection screen), or withdrawing a charge (use a concession).
"""

from __future__ import annotations

import re

from django.db import transaction
from django.db.models import Count, Min, Sum
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import StateConflict, ValidationFailed

from ..models import FeeHead
from . import deps
from .views import validated


class ChargeClassesRequest(serializers.Serializer):
    """Body of POST /fees/charge-classes."""

    fee_head_id = serializers.UUIDField(required=False, allow_null=True)
    fee_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    amount_paise = serializers.IntegerField(min_value=1)
    due_date = serializers.DateField()
    section_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)


def _code_for(name: str) -> str:
    """Turn a fee name such as "Annual day fee" into a code "ANNUAL_DAY_FEE"."""
    code = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").upper()
    return code[:60] or "FEE"


class FeeHeadCollectionView(APIView):
    """GET /fee-heads."""

    @extend_schema(operation_id="list_fee_heads", responses={200: dict})
    def get(self, request: Request) -> Response:
        """List fee types with charged, outstanding and pupil counts."""
        context = request.school_context
        deps.gate().require_staff_action(context, "fees.read")
        heads = FeeHead.objects.filter(school_id=context.school_id).annotate(
            charged_paise=Sum("charges__amount_paise"),
            outstanding_paise=Sum("charges__balance_paise"),
            pupils=Count("charges__student_id", distinct=True),
            first_due=Min("charges__due_date"),
        )
        items = [
            {
                "id": str(head.id),
                "code": head.code,
                "label_key": head.label_key,
                "charged_paise": int(head.charged_paise or 0),
                "outstanding_paise": int(head.outstanding_paise or 0),
                "pupils": head.pupils,
                "first_due": head.first_due.isoformat() if head.first_due else None,
            }
            for head in heads.order_by("first_due", "code")
        ]
        return Response({"items": items, "next_cursor": None})


class ChargeClassesView(APIView):
    """POST /fees/charge-classes."""

    @extend_schema(
        operation_id="charge_classes",
        request=ChargeClassesRequest,
        responses={200: dict},
    )
    def post(self, request: Request) -> Response:
        """Charge a fee to every pupil in the chosen classes; skip those already charged."""
        context = request.school_context
        body = validated(ChargeClassesRequest, request.data)
        gate = deps.gate()
        gate.require_staff_action(context, "fees.configure")
        service = deps.charge_service()
        registry = service.registry
        today = gate.effective_date()
        with transaction.atomic():
            head = None
            if body.get("fee_head_id"):
                head = FeeHead.objects.filter(
                    id=body["fee_head_id"], school_id=context.school_id
                ).first()
            if head is None:
                name = (body.get("fee_name") or "").strip()
                if not name:
                    raise ValidationFailed("fees.error.name_required")
                head, _ = FeeHead.objects.get_or_create(
                    school_id=context.school_id,
                    code=_code_for(name),
                    defaults={"label_key": name, "version": 1},
                )
            charged = already = 0
            for section_id in body["section_ids"]:
                roster = registry.get_roster(context, section_id, today)
                for pupil in roster.students:
                    key = f"class:{head.code}:{body['due_date'].isoformat()}:{pupil.student_id}"
                    try:
                        _, created = service.raise_charge(
                            context,
                            source_key=key,
                            student_id=pupil.student_id,
                            fee_head_id=head.id,
                            amount_paise=body["amount_paise"],
                            due_date=body["due_date"],
                            description_key=head.label_key,
                            via_api=True,
                        )
                    except StateConflict:
                        # Charged before with a different amount; leave it as it is.
                        created = False
                    if created:
                        charged += 1
                    else:
                        already += 1
        return Response(
            {
                "fee_head_id": str(head.id),
                "label_key": head.label_key,
                "charged": charged,
                "already_charged": already,
            },
            status=status.HTTP_200_OK,
        )
