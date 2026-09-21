"""REST endpoints for guardian links, assignments and enrolments."""

from __future__ import annotations

from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import wire_lifecycle
from .cursors import decode_cursor, encode_cursor, resolve_page_size
from .deps import enrolment_service, guardian_link_service, teaching_assignment_service
from .serializers_lifecycle import (
    EndSubjectEnrolmentRequest,
    EnrolmentPageResponse,
    EnrolmentRequest,
    EnrolmentResponse,
    GuardianLinkPageResponse,
    GuardianLinkRequest,
    GuardianLinkResponse,
    RosterResponse,
    SubjectEnrolmentPageResponse,
    SubjectEnrolmentRequest,
    SubjectEnrolmentResponse,
    SubjectOfferingPageResponse,
    SubjectOfferingRequest,
    SubjectOfferingResponse,
    TeachingAssignmentPageResponse,
    TeachingAssignmentRequest,
    TeachingAssignmentResponse,
    TransferEnrolmentRequest,
    UpdateGuardianLinkRequest,
    UpdateTeachingAssignmentRequest,
)
from .views import COMMON_ERRORS, validated


class GuardianLinkCollectionView(APIView):
    """List and create guardian links."""

    @extend_schema(
        operation_id="list_guardian_links",
        summary="list guardian links",
        parameters=[
            OpenApiParameter("cursor", str, required=False),
            OpenApiParameter("page_size", int, required=False),
            OpenApiParameter("student_id", UUID, required=False),
        ],
        responses={200: GuardianLinkPageResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return one page of guardian links."""
        page_size = resolve_page_size(request.query_params.get("page_size"))
        after_id = decode_cursor(request.query_params.get("cursor"))
        student_param = request.query_params.get("student_id")
        student_id = UUID(student_param) if student_param else None
        service = guardian_link_service()
        rows, has_more = service.list_links(
            request.school_context,
            student_id=student_id,
            after_id=after_id,
            page_size=page_size,
        )
        return Response(
            {
                "items": [wire_lifecycle.guardian_link_to_wire(row) for row in rows],
                "next_cursor": encode_cursor(rows[-1].id) if has_more and rows else None,
            }
        )

    @extend_schema(
        operation_id="create_guardian_link",
        summary="create guardian link",
        request=GuardianLinkRequest,
        responses={201: GuardianLinkResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a guardian link."""
        body = validated(GuardianLinkRequest, request.data)
        row = guardian_link_service().create_link(
            request.school_context,
            student_id=body["student_id"],
            guardian_id=body["guardian_id"],
            visibility=body["visibility"],
            from_date=body["from_date"],
            to_date=body["to_date"],
        )
        return Response(wire_lifecycle.guardian_link_to_wire(row), status=201)


class GuardianLinkDetailView(APIView):
    """Update one guardian link."""

    @extend_schema(
        operation_id="update_guardian_link",
        summary="update guardian link",
        request=UpdateGuardianLinkRequest,
        responses={200: GuardianLinkResponse, **COMMON_ERRORS},
    )
    def put(self, request: Request, section_id: UUID) -> Response:
        """Update a guardian link under expected_version."""
        body = validated(UpdateGuardianLinkRequest, request.data)
        row = guardian_link_service().update_link(
            request.school_context,
            link_id=section_id,
            visibility=body["visibility"],
            from_date=body["from_date"],
            to_date=body["to_date"],
            expected_version=body["expected_version"],
        )
        return Response(wire_lifecycle.guardian_link_to_wire(row))


class TeachingAssignmentCollectionView(APIView):
    """List and create teaching assignments."""

    @extend_schema(
        operation_id="list_teaching_assignments",
        summary="list teaching assignments",
        parameters=[
            OpenApiParameter("cursor", str, required=False),
            OpenApiParameter("page_size", int, required=False),
        ],
        responses={200: TeachingAssignmentPageResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return one page of teaching assignments."""
        page_size = resolve_page_size(request.query_params.get("page_size"))
        after_id = decode_cursor(request.query_params.get("cursor"))
        rows, has_more = teaching_assignment_service().list_assignments(
            request.school_context, after_id=after_id, page_size=page_size
        )
        return Response(
            {
                "items": [wire_lifecycle.teaching_assignment_to_wire(row) for row in rows],
                "next_cursor": encode_cursor(rows[-1].id) if has_more and rows else None,
            }
        )

    @extend_schema(
        operation_id="create_teachingassignment",
        summary="create teachingassignment",
        request=TeachingAssignmentRequest,
        responses={201: TeachingAssignmentResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a teaching assignment."""
        body = validated(TeachingAssignmentRequest, request.data)
        row = teaching_assignment_service().create_assignment(
            request.school_context,
            staff_id=body["staff_id"],
            section_id=body["section_id"],
            subject_id=body["subject_id"],
            from_date=body["from_date"],
            to_date=body["to_date"],
        )
        return Response(wire_lifecycle.teaching_assignment_to_wire(row), status=201)


class TeachingAssignmentDetailView(APIView):
    """Read and update one teaching assignment."""

    @extend_schema(
        operation_id="get_teachingassignment",
        summary="get teachingassignment",
        responses={200: TeachingAssignmentResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request, section_id: UUID) -> Response:
        """Return one teaching assignment."""
        row = teaching_assignment_service().get_assignment(
            request.school_context, section_id
        )
        return Response(wire_lifecycle.teaching_assignment_to_wire(row))

    @extend_schema(
        operation_id="update_teachingassignment",
        summary="update teachingassignment",
        request=UpdateTeachingAssignmentRequest,
        responses={200: TeachingAssignmentResponse, **COMMON_ERRORS},
    )
    def put(self, request: Request, section_id: UUID) -> Response:
        """Update a teaching assignment."""
        body = validated(UpdateTeachingAssignmentRequest, request.data)
        row = teaching_assignment_service().update_assignment(
            request.school_context,
            assignment_id=section_id,
            staff_id=body["staff_id"],
            section_id=body["section_id"],
            subject_id=body["subject_id"],
            from_date=body["from_date"],
            to_date=body["to_date"],
            expected_version=body["expected_version"],
        )
        return Response(wire_lifecycle.teaching_assignment_to_wire(row))


class SubjectOfferingCollectionView(APIView):
    """List and create subject offerings."""

    @extend_schema(
        operation_id="list_subject_offerings",
        summary="list subject offerings",
        parameters=[
            OpenApiParameter("cursor", str, required=False),
            OpenApiParameter("page_size", int, required=False),
        ],
        responses={200: SubjectOfferingPageResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return one page of subject offerings."""
        page_size = resolve_page_size(request.query_params.get("page_size"))
        after_id = decode_cursor(request.query_params.get("cursor"))
        rows, has_more = teaching_assignment_service().list_subject_offerings(
            request.school_context, after_id=after_id, page_size=page_size
        )
        return Response(
            {
                "items": [wire_lifecycle.subject_offering_to_wire(row) for row in rows],
                "next_cursor": encode_cursor(rows[-1].id) if has_more and rows else None,
            }
        )

    @extend_schema(
        operation_id="create_subjectoffering",
        summary="create subjectoffering",
        request=SubjectOfferingRequest,
        responses={201: SubjectOfferingResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a subject offering."""
        body = validated(SubjectOfferingRequest, request.data)
        row = teaching_assignment_service().create_subject_offering(
            request.school_context,
            year_id=body["year_id"],
            section_id=body["section_id"],
            subject_id=body["subject_id"],
            optional_group=body["optional_group"],
        )
        return Response(wire_lifecycle.subject_offering_to_wire(row), status=201)


class EnrolmentCollectionView(APIView):
    """List and create enrolments."""

    @extend_schema(
        operation_id="list_enrolments",
        summary="list enrolments",
        parameters=[
            OpenApiParameter("cursor", str, required=False),
            OpenApiParameter("page_size", int, required=False),
            OpenApiParameter("student_id", UUID, required=False),
        ],
        responses={200: EnrolmentPageResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return one page of enrolments."""
        page_size = resolve_page_size(request.query_params.get("page_size"))
        after_id = decode_cursor(request.query_params.get("cursor"))
        student_param = request.query_params.get("student_id")
        student_id = UUID(student_param) if student_param else None
        rows, has_more = enrolment_service().list_enrolments(
            request.school_context,
            student_id=student_id,
            after_id=after_id,
            page_size=page_size,
        )
        return Response(
            {
                "items": [wire_lifecycle.enrolment_to_wire(row) for row in rows],
                "next_cursor": encode_cursor(rows[-1].id) if has_more and rows else None,
            }
        )

    @extend_schema(
        operation_id="create_enrolment",
        summary="create enrolment",
        request=EnrolmentRequest,
        responses={201: EnrolmentResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create an enrolment."""
        body = validated(EnrolmentRequest, request.data)
        row = enrolment_service().create_enrolment(
            request.school_context,
            student_id=body["student_id"],
            year_id=body["year_id"],
            section_id=body["section_id"],
            from_date=body["from_date"],
            to_date=body["to_date"],
        )
        return Response(wire_lifecycle.enrolment_to_wire(row), status=201)


class EnrolmentTransferView(APIView):
    """Transfer an enrolment to another section."""

    @extend_schema(
        operation_id="transfer_enrolment",
        summary="transfer enrolment",
        request=TransferEnrolmentRequest,
        responses={200: EnrolmentResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request, section_id: UUID) -> Response:
        """Transfer a pupil to another section from an effective date."""
        body = validated(TransferEnrolmentRequest, request.data)
        row = enrolment_service().transfer_enrolment(
            request.school_context,
            enrolment_id=section_id,
            target_section_id=body["target_section_id"],
            effective_date=body["effective_date"],
            expected_version=body["expected_version"],
        )
        return Response(wire_lifecycle.enrolment_to_wire(row))


class SubjectEnrolmentCollectionView(APIView):
    """List and create subject enrolments."""

    @extend_schema(
        operation_id="list_subject_enrolments",
        summary="list subject enrolments",
        parameters=[
            OpenApiParameter("cursor", str, required=False),
            OpenApiParameter("page_size", int, required=False),
            OpenApiParameter("enrolment_id", UUID, required=False),
        ],
        responses={200: SubjectEnrolmentPageResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return one page of subject enrolments."""
        page_size = resolve_page_size(request.query_params.get("page_size"))
        after_id = decode_cursor(request.query_params.get("cursor"))
        enrolment_param = request.query_params.get("enrolment_id")
        enrolment_id = UUID(enrolment_param) if enrolment_param else None
        rows, has_more = enrolment_service().list_subject_enrolments(
            request.school_context,
            enrolment_id=enrolment_id,
            after_id=after_id,
            page_size=page_size,
        )
        return Response(
            {
                "items": [wire_lifecycle.subject_enrolment_to_wire(row) for row in rows],
                "next_cursor": encode_cursor(rows[-1].id) if has_more and rows else None,
            }
        )

    @extend_schema(
        operation_id="create_subject_enrolment",
        summary="create subject enrolment",
        request=SubjectEnrolmentRequest,
        responses={201: SubjectEnrolmentResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a subject enrolment."""
        body = validated(SubjectEnrolmentRequest, request.data)
        row = enrolment_service().create_subject_enrolment(
            request.school_context,
            enrolment_id=body["enrolment_id"],
            subject_offering_id=body["subject_offering_id"],
            from_date=body["from_date"],
            to_date=body["to_date"],
        )
        return Response(wire_lifecycle.subject_enrolment_to_wire(row), status=201)


class SubjectEnrolmentEndView(APIView):
    """End a subject enrolment."""

    @extend_schema(
        operation_id="end_subject_enrolment",
        summary="end subject enrolment",
        request=EndSubjectEnrolmentRequest,
        responses={200: SubjectEnrolmentResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request, section_id: UUID) -> Response:
        """Set the inclusive end date on a subject enrolment."""
        body = validated(EndSubjectEnrolmentRequest, request.data)
        row = enrolment_service().end_subject_enrolment(
            request.school_context,
            subject_enrolment_id=section_id,
            to_date=body["to_date"],
            expected_version=body["expected_version"],
        )
        return Response(wire_lifecycle.subject_enrolment_to_wire(row))


class SectionRosterView(APIView):
    """Return a dated section roster."""

    @extend_schema(
        operation_id="get_section_roster",
        summary="get section roster",
        parameters=[
            OpenApiParameter("date", str, required=True),
            OpenApiParameter("subject_id", UUID, required=False),
        ],
        responses={200: RosterResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request, section_id: UUID) -> Response:
        """Return the roster for a section on a date."""
        from datetime import date

        effective = date.fromisoformat(request.query_params["date"])
        subject_param = request.query_params.get("subject_id")
        subject_id = UUID(subject_param) if subject_param else None
        roster = enrolment_service().get_section_roster(
            request.school_context,
            section_id=section_id,
            effective_date=effective,
            subject_id=subject_id,
        )
        return Response(roster.to_wire())
