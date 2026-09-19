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
    path("guardians", GuardianCollectionView.as_view(), name="guardian-collection"),
    path("staff", StaffCollectionView.as_view(), name="staff-collection"),
    path(
        "sections/<uuid:section_id>/archive",
        SectionArchiveView.as_view(),
        name="section-archive",
    ),
    path("sections/<uuid:section_id>", SectionDetailView.as_view(), name="section-detail"),
    path("students/<uuid:student_id>", StudentDetailView.as_view(), name="student-detail"),
]
