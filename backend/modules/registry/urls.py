"""URL patterns for M02, mounted at its declared api_prefix.

Only the roots step 1 actually serves are mounted. Enrolment, guardian links,
teaching assignments, promotion, withdrawal and exchange arrive in later steps;
mounting an empty route now would let a consumer call something that silently
does nothing.

Paths carry NO trailing slash, exactly as ``contracts/M02/openapi.json`` declares
them. The shared ``API_PATH_ROOT_PATTERN`` in contracts/registration.py requires
every declared ROOT to end in one, so registration.py declares ``students/``
while this file serves ``students``. Serving both forms was tried and rejected:
it produced duplicate operationIds and failed ``spectacular --fail-on-warn``.
The declaration mismatch is recorded in docs/modules/M02/handoff.md; reconciling
it is a contract revision, not a routing choice made here.
"""

from __future__ import annotations

from django.urls import path

from .api.views import (
    AcademicYearCollectionView,
    DuplicateReviewView,
    GuardianCollectionView,
    SchoolConfigView,
    SectionArchiveView,
    SectionCollectionView,
    SectionDetailView,
    StaffCollectionView,
    StandardCollectionView,
    StudentCollectionView,
    StudentDetailView,
    SubjectCollectionView,
    TermCollectionView,
)
from .api.views_lifecycle import (
    EnrolmentCollectionView,
    EnrolmentTransferView,
    GuardianLinkCollectionView,
    GuardianLinkDetailView,
    SectionRosterView,
    SubjectEnrolmentCollectionView,
    SubjectEnrolmentEndView,
    SubjectOfferingCollectionView,
    TeachingAssignmentCollectionView,
    TeachingAssignmentDetailView,
)
from .api.views_self import MyStudentsView

app_name = "registry"


urlpatterns = [
    path("school-config", SchoolConfigView.as_view(), name="school-config"),
    path("academic-years", AcademicYearCollectionView.as_view(), name="year-collection"),
    path("terms", TermCollectionView.as_view(), name="term-collection"),
    path("standards", StandardCollectionView.as_view(), name="standard-collection"),
    path("sections", SectionCollectionView.as_view(), name="section-collection"),
    path("subjects", SubjectCollectionView.as_view(), name="subject-collection"),
    # Fixed segments must precede the UUID converter, or "duplicate-review"
    # would be matched as a malformed student id and answered with a 404.
    path(
        "students/duplicate-review",
        DuplicateReviewView.as_view(),
        name="student-duplicate-review",
    ),
    path("students", StudentCollectionView.as_view(), name="student-collection"),
    path("students/mine", MyStudentsView.as_view(), name="students-mine"),
    path("guardians", GuardianCollectionView.as_view(), name="guardian-collection"),
    path("staff", StaffCollectionView.as_view(), name="staff-collection"),
    path(
        "sections/<uuid:section_id>/archive",
        SectionArchiveView.as_view(),
        name="section-archive",
    ),
    path(
        "sections/<uuid:section_id>/roster",
        SectionRosterView.as_view(),
        name="section-roster",
    ),
    path("sections/<uuid:section_id>", SectionDetailView.as_view(), name="section-detail"),
    path("students/<uuid:student_id>", StudentDetailView.as_view(), name="student-detail"),
    path(
        "guardian-links",
        GuardianLinkCollectionView.as_view(),
        name="guardian-link-collection",
    ),
    path(
        "guardian-links/<uuid:section_id>",
        GuardianLinkDetailView.as_view(),
        name="guardian-link-detail",
    ),
    path(
        "teaching-assignments",
        TeachingAssignmentCollectionView.as_view(),
        name="teaching-assignment-collection",
    ),
    path(
        "teaching-assignments/<uuid:section_id>",
        TeachingAssignmentDetailView.as_view(),
        name="teaching-assignment-detail",
    ),
    path(
        "subject-offerings",
        SubjectOfferingCollectionView.as_view(),
        name="subject-offering-collection",
    ),
    path("enrolments", EnrolmentCollectionView.as_view(), name="enrolment-collection"),
    path(
        "enrolments/<uuid:section_id>/transfer",
        EnrolmentTransferView.as_view(),
        name="enrolment-transfer",
    ),
    path(
        "subject-enrolments",
        SubjectEnrolmentCollectionView.as_view(),
        name="subject-enrolment-collection",
    ),
    path(
        "subject-enrolments/<uuid:section_id>/end",
        SubjectEnrolmentEndView.as_view(),
        name="subject-enrolment-end",
    ),
]
