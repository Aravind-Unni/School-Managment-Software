"""M02 REST endpoints.

Views are thin: parse, delegate, render. They hold no authorisation logic of
their own, so an import or an export calling the same service gets the same
decision as an HTTP caller.

Does not handle: steps 2-4. Enrolment, guardian links, teaching assignments,
promotion, withdrawal and exchange endpoints are not mounted yet, and the
module declares only the roots it actually serves.
"""

from __future__ import annotations

from uuid import UUID

from django.db import transaction
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import models
from . import wire
from .deps import configuration_service, guardian_link_service, people_service
from .listing import list_response
from .serializers import (
    AcademicYearRequest,
    AcademicYearResponse,
    ArchiveRequest,
    CreateStudentRequest,
    DuplicateReviewRequest,
    DuplicateReviewResponse,
    ErrorEnvelopeResponse,
    GuardianRequest,
    GuardianResponse,
    SchoolConfigResponse,
    SectionRequest,
    SectionResponse,
    StaffRequest,
    StaffResponse,
    StandardRequest,
    StandardResponse,
    StudentDTOResponse,
    StudentRecordPageResponse,
    StudentRecordResponse,
    SubjectRequest,
    SubjectResponse,
    TermRequest,
    TermResponse,
    UpdateSchoolConfigRequest,
    UpdateStudentRequest,
)

#: Error responses every endpoint in this module can return. Declared once so a
#: generated client carries the full error surface, not just the happy path.
COMMON_ERRORS = {
    400: OpenApiResponse(ErrorEnvelopeResponse, "Client asserted its own identity."),
    401: OpenApiResponse(ErrorEnvelopeResponse, "Unauthenticated, or 2FA too old."),
    403: OpenApiResponse(ErrorEnvelopeResponse, "Action denied in this scope."),
    404: OpenApiResponse(ErrorEnvelopeResponse, "Absent, or not visible to you."),
    409: OpenApiResponse(ErrorEnvelopeResponse, "Version or state conflict."),
    422: OpenApiResponse(ErrorEnvelopeResponse, "Business validation failed."),
}


def validated(serializer_class, data) -> dict:
    """Parse a closed request body, raising 422 on anything unexpected."""
    payload = serializer_class(data=data)
    payload.is_valid(raise_exception=True)
    return payload.validated_data


class SchoolConfigView(APIView):
    """GET and PUT the single school configuration row."""

    @extend_schema(
        operation_id="get_school_config",
        summary="Read the school configuration",
        responses={200: SchoolConfigResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return this deployment's configuration."""
        row = configuration_service().get_school_config(request.school_context)
        return Response(wire.school_config_to_wire(row))

    @extend_schema(
        operation_id="update_school_config",
        summary="Update the school configuration",
        request=UpdateSchoolConfigRequest,
        responses={200: SchoolConfigResponse, **COMMON_ERRORS},
    )
    def put(self, request: Request) -> Response:
        """Update the configuration under expected_version. Never creates."""
        body = validated(UpdateSchoolConfigRequest, request.data)
        row = configuration_service().update_school_config(
            request.school_context,
            display_name=body["display_name"],
            board=body["board"],
            default_language=body["default_language"],
            expected_version=body["expected_version"],
        )
        return Response(wire.school_config_to_wire(row))


class AcademicYearCollectionView(APIView):
    """POST an academic year."""

    def get(self, request: Request) -> Response:
        """Return one keyset page (``cursor``, ``page_size``)."""
        return list_response(
            request,
            models.AcademicYear,
            wire.academic_year_to_wire,
            action="students.read",
            with_external_ids=False,
            search_fields=(),
        )

    @extend_schema(
        operation_id="create_academicyear",
        summary="Create an academic year",
        request=AcademicYearRequest,
        responses={201: AcademicYearResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a year in draft state and return it with HTTP 201."""
        body = validated(AcademicYearRequest, request.data)
        row = configuration_service().create_academic_year(
            request.school_context,
            name=body["name"],
            start=body["start"],
            end=body["end"],
        )
        return Response(wire.academic_year_to_wire(row), status=201)


class TermCollectionView(APIView):
    """POST a term."""

    def get(self, request: Request) -> Response:
        """Return one keyset page (``cursor``, ``page_size``)."""
        return list_response(
            request,
            models.Term,
            wire.term_to_wire,
            action="students.read",
            with_external_ids=False,
            search_fields=(),
        )

    @extend_schema(
        operation_id="create_term",
        summary="Create a term",
        request=TermRequest,
        responses={201: TermResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a term inside its year's inclusive range."""
        body = validated(TermRequest, request.data)
        row = configuration_service().create_term(
            request.school_context,
            year_id=body["year_id"],
            name=body["name"],
            start=body["start"],
            end=body["end"],
        )
        return Response(wire.term_to_wire(row), status=201)


class StandardCollectionView(APIView):
    """POST a class level."""

    def get(self, request: Request) -> Response:
        """Return one keyset page (``cursor``, ``page_size``)."""
        return list_response(
            request,
            models.Standard,
            wire.standard_to_wire,
            action="students.read",
            with_external_ids=False,
            search_fields=(),
        )

    @extend_schema(
        operation_id="create_standard",
        summary="Create a standard",
        request=StandardRequest,
        responses={201: StandardResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a standard between 1 and 12."""
        body = validated(StandardRequest, request.data)
        row = configuration_service().create_standard(
            request.school_context, number=body["number"]
        )
        return Response(wire.standard_to_wire(row), status=201)


class SectionCollectionView(APIView):
    """POST a section."""

    def get(self, request: Request) -> Response:
        """Return one keyset page (``cursor``, ``page_size``)."""
        return list_response(
            request,
            models.Section,
            wire.section_to_wire,
            action="students.read",
            with_external_ids=False,
            search_fields=(),
        )

    @extend_schema(
        operation_id="create_section",
        summary="Create a section",
        request=SectionRequest,
        responses={201: SectionResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a division of a standard within a year."""
        body = validated(SectionRequest, request.data)
        row = configuration_service().create_section(
            request.school_context,
            year_id=body["year_id"],
            standard_id=body["standard_id"],
            name=body["name"],
        )
        return Response(wire.section_to_wire(row), status=201)


class SectionDetailView(APIView):
    """GET one section."""

    @extend_schema(
        operation_id="get_section",
        summary="Read one section",
        responses={200: SectionResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request, section_id: UUID) -> Response:
        """Return one section, archived or not."""
        from ..models import Section
        from ..services.writes import fetch_in_school

        configuration_service()._authorise(request.school_context, "registry.manage")
        row = fetch_in_school(
            Section, school_id=request.school_context.school_id, row_id=section_id
        )
        return Response(wire.section_to_wire(row))


class SectionArchiveView(APIView):
    """POST to archive a section. Archive preserves; there is no DELETE."""

    @extend_schema(
        operation_id="archive_section",
        summary="Archive a section without deleting it",
        request=ArchiveRequest,
        responses={200: SectionResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request, section_id: UUID) -> Response:
        """Mark the section archived under expected_version."""
        body = validated(ArchiveRequest, request.data)
        row = configuration_service().archive_section(
            request.school_context,
            section_id=section_id,
            expected_version=body["expected_version"],
        )
        return Response(wire.section_to_wire(row))


class SubjectCollectionView(APIView):
    """POST a school-authored subject."""

    def get(self, request: Request) -> Response:
        """Return one keyset page (``cursor``, ``page_size``)."""
        return list_response(
            request,
            models.Subject,
            wire.subject_to_wire,
            action="students.read",
            with_external_ids=False,
            search_fields=(),
        )

    @extend_schema(
        operation_id="create_subject",
        summary="Create a subject",
        request=SubjectRequest,
        responses={201: SubjectResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a subject with a school-unique code."""
        body = validated(SubjectRequest, request.data)
        row = configuration_service().create_subject(
            request.school_context, code=body["code"], display_name=body["display_name"]
        )
        return Response(wire.subject_to_wire(row), status=201)


class StudentCollectionView(APIView):
    """GET a cursor page of students, POST an admission."""

    @extend_schema(
        operation_id="list_students",
        summary="List students",
        parameters=[
            OpenApiParameter(
                "cursor",
                str,
                description="Opaque keyset cursor from a previous next_cursor. Do not parse.",
            ),
            OpenApiParameter(
                "page_size",
                int,
                description="1 to 100. Out of range is refused, never silently clamped.",
            ),
        ],
        responses={200: StudentRecordPageResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return one page of students in stable id order; ``query`` searches."""
        return list_response(
            request,
            models.Student,
            wire.student_record_to_wire,
            action="students.read",
            with_external_ids=True,
            search_fields=("display_name", "admission_no"),
        )

    @extend_schema(
        operation_id="create_student",
        summary="Admit a student",
        request=CreateStudentRequest,
        responses={201: StudentDTOResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Admit a student, returning the minimal StudentDTO with HTTP 201.

        The response deliberately carries no version. A follow-up GET supplies
        the versioned browser record; keeping the two apart is what stops the
        browser shape leaking into what other modules consume.
        """
        body = validated(CreateStudentRequest, request.data)
        # One transaction: an admission never survives without the links it named.
        with transaction.atomic():
            dto = people_service().admit_student(
                request.school_context,
                admission_no=body["admission_no"],
                display_name=body["display_name"],
                date_of_birth=body["profile"]["date_of_birth"],
                preferred_language=body["profile"]["preferred_language"],
                external_ids=tuple(body["external_ids"]),
                acknowledgement=body["duplicate_review"],
            )
            # Links named in the admission are created with it, not silently dropped.
            links = guardian_link_service()
            for link in body["guardian_links"]:
                links.create_link(
                    request.school_context,
                    student_id=dto.id,
                    guardian_id=link["guardian_id"],
                    visibility=link["visibility"],
                    from_date=link["from_date"],
                    to_date=link["to_date"],
                )
        return Response(dto.to_wire(), status=201)


class StudentDetailView(APIView):
    """GET and PUT one student's versioned browser record."""

    @extend_schema(
        operation_id="get_student",
        summary="Read one student record",
        responses={200: StudentRecordResponse, **COMMON_ERRORS},
    )
    def get(self, request: Request, student_id: UUID) -> Response:
        """Return one student's record."""
        service = people_service()
        row = service.get_student(request.school_context, student_id)
        return Response(wire.student_record_to_wire(row, service.external_ids_for(row.id)))

    @extend_schema(
        operation_id="update_student",
        summary="Amend a student profile",
        request=UpdateStudentRequest,
        responses={200: StudentRecordResponse, **COMMON_ERRORS},
    )
    def put(self, request: Request, student_id: UUID) -> Response:
        """Amend a student's profile under expected_version."""
        body = validated(UpdateStudentRequest, request.data)
        service = people_service()
        row = service.update_student(
            request.school_context,
            student_id=student_id,
            display_name=body["display_name"],
            date_of_birth=body["profile"]["date_of_birth"],
            preferred_language=body["profile"]["preferred_language"],
            expected_version=body["expected_version"],
        )
        return Response(wire.student_record_to_wire(row, service.external_ids_for(row.id)))


class DuplicateReviewView(APIView):
    """POST to see which stored students a proposed admission may duplicate."""

    @extend_schema(
        operation_id="review_student_duplicates",
        summary="Open a duplicate review for a proposed admission",
        request=DuplicateReviewRequest,
        responses={200: DuplicateReviewResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Issue a review token pinned to the candidates and versions shown."""
        body = validated(DuplicateReviewRequest, request.data)
        row = people_service().open_duplicate_review(
            request.school_context,
            admission_no=body["admission_no"],
            display_name=body["display_name"],
            date_of_birth=body["profile"]["date_of_birth"],
        )
        return Response(
            {
                "review_id": str(row.id),
                "review_version": row.version,
                "candidates": row.candidates,
                "expires_at": row.expires_at.isoformat(),
            }
        )


class GuardianCollectionView(APIView):
    """POST a guardian record."""

    def get(self, request: Request) -> Response:
        """Return one keyset page (``cursor``, ``page_size``, ``query``)."""
        return list_response(
            request,
            models.Guardian,
            wire.guardian_to_wire,
            action="guardians.manage",
            with_external_ids=True,
            search_fields=("display_name", "phone", "email"),
        )

    @extend_schema(
        operation_id="create_guardian",
        summary="Create a guardian",
        request=GuardianRequest,
        responses={201: GuardianResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a guardian. Creating one grants no access to anything."""
        body = validated(GuardianRequest, request.data)
        service = people_service()
        row = service.create_guardian(
            request.school_context,
            display_name=body["display_name"],
            email=body["email"],
            phone=body["phone"],
            external_ids=tuple(body["external_ids"]),
        )
        return Response(
            wire.guardian_to_wire(row, service.external_ids_for(row.id)), status=201
        )


class StaffCollectionView(APIView):
    """POST a staff person record."""

    def get(self, request: Request) -> Response:
        """Return one keyset page (``cursor``, ``page_size``, ``query``)."""
        return list_response(
            request,
            models.StaffProfile,
            wire.staff_to_wire,
            action="students.read",
            with_external_ids=True,
            search_fields=("display_name",),
        )

    @extend_schema(
        operation_id="create_staff",
        summary="Create a staff record",
        request=StaffRequest,
        responses={201: StaffResponse, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a staff record, independent of any login account."""
        body = validated(StaffRequest, request.data)
        service = people_service()
        row = service.create_staff(
            request.school_context,
            display_name=body["display_name"],
            external_ids=tuple(body["external_ids"]),
        )
        return Response(wire.staff_to_wire(row, service.external_ids_for(row.id)), status=201)
