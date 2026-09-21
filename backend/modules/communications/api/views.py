"""M11 REST endpoints for notices, messages, deliveries and SMS callbacks."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import deps
from .serializers import (
    CreateNoticeRequest,
    EnqueueMessageRequest,
    ErrorEnvelopeResponse,
    PublishNoticeRequest,
)

COMMON_ERRORS = {
    401: OpenApiResponse(ErrorEnvelopeResponse, "Unauthenticated."),
    403: OpenApiResponse(ErrorEnvelopeResponse, "Action denied."),
    404: OpenApiResponse(ErrorEnvelopeResponse, "Absent, or not visible."),
    409: OpenApiResponse(ErrorEnvelopeResponse, "Version or state conflict."),
    422: OpenApiResponse(ErrorEnvelopeResponse, "Business validation failed."),
}


def validated(serializer_class, data) -> dict:
    """Parse a closed request body, raising 422 on anything unexpected."""
    payload = serializer_class(data=data)
    payload.is_valid(raise_exception=True)
    return payload.validated_data


class NoticeCollectionView(APIView):
    """POST /notices."""

    @extend_schema(
        operation_id="create_notice",
        request=CreateNoticeRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a draft notice."""
        body = validated(CreateNoticeRequest, request.data)
        audience = body["audience"]
        result = deps.notice_service().create(
            request.school_context,
            title=body["title"],
            body=body["body"],
            locale=body["locale"],
            audience=dict(audience),
            scheduled_at=body.get("scheduled_at"),
        )
        return Response(result, status=status.HTTP_201_CREATED)


class NoticePublishView(APIView):
    """POST /notices/{id}/publish."""

    @extend_schema(
        operation_id="publish_notice",
        request=PublishNoticeRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, notice_id: UUID) -> Response:
        """Publish notice and snapshot audience."""
        body = validated(PublishNoticeRequest, request.data)
        return Response(
            deps.notice_service().publish(
                request.school_context,
                notice_id,
                expected_version=body["expected_version"],
            )
        )


class MessageCollectionView(APIView):
    """POST /messages."""

    @extend_schema(
        operation_id="enqueue_message",
        request=EnqueueMessageRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Enqueue a templated delivery."""
        body = validated(EnqueueMessageRequest, request.data)
        result = deps.delivery_service().enqueue(
            request.school_context,
            template_key=body["template_key"],
            recipient_ref=body["recipient_ref"],
            channel=body["channel"],
            locale=body["locale"],
            variables=dict(body["variables"]),
            dedupe_key=body["dedupe_key"],
        )
        return Response(result, status=status.HTTP_201_CREATED)


class DeliveryDetailView(APIView):
    """GET /deliveries/{id}."""

    @extend_schema(
        operation_id="get_delivery",
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request, delivery_id: UUID) -> Response:
        """Delivery state and sanitized attempts."""
        return Response(deps.delivery_service().get(request.school_context, delivery_id))


class SmsCallbackView(APIView):
    """POST /sms/callback/{provider} — signature-authenticated."""

    authentication_classes: ClassVar[list] = []
    permission_classes: ClassVar[list] = []

    @extend_schema(
        operation_id="sms_provider_callback",
        responses={202: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, provider: str) -> Response:
        """Accept a signed provider callback with replay protection."""
        raw = request.body
        headers = dict(request.headers.items())
        school_id = getattr(settings, "SCHOOL_ID", None)
        from uuid import UUID as _UUID

        result = deps.delivery_service().accept_callback(
            school_id=_UUID(str(school_id)),
            provider_name=provider,
            headers=headers,
            raw_body=raw,
        )
        return Response(result, status=status.HTTP_202_ACCEPTED)
