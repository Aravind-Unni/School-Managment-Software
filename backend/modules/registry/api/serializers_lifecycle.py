"""Request and response serializers for step 2-3 endpoints."""

from __future__ import annotations

from rest_framework import serializers

from .serializers import ClosedSerializer


class GuardianLinkRequest(ClosedSerializer):
    """Create a guardian link."""

    student_id = serializers.UUIDField()
    guardian_id = serializers.UUIDField()
    visibility = serializers.ChoiceField(choices=("academic", "none"))
    from_date = serializers.DateField()
    to_date = serializers.DateField(allow_null=True)


class UpdateGuardianLinkRequest(ClosedSerializer):
    """Update a guardian link."""

    visibility = serializers.ChoiceField(choices=("academic", "none"))
    from_date = serializers.DateField()
    to_date = serializers.DateField(allow_null=True)
    expected_version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(min_length=1)


class GuardianLinkResponse(ClosedSerializer):
    """One guardian link."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    student_id = serializers.UUIDField()
    guardian_id = serializers.UUIDField()
    visibility = serializers.CharField()
    from_date = serializers.DateField()
    to_date = serializers.DateField(allow_null=True)


class GuardianLinkPageResponse(ClosedSerializer):
    """Cursor page of guardian links."""

    items = GuardianLinkResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class TeachingAssignmentRequest(ClosedSerializer):
    """Create a teaching assignment."""

    staff_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    from_date = serializers.DateField()
    to_date = serializers.DateField(allow_null=True)


class UpdateTeachingAssignmentRequest(ClosedSerializer):
    """Update a teaching assignment."""

    staff_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    from_date = serializers.DateField()
    to_date = serializers.DateField(allow_null=True)
    expected_version = serializers.IntegerField(min_value=1)


class TeachingAssignmentResponse(ClosedSerializer):
    """One teaching assignment."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    staff_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    from_date = serializers.DateField()
    to_date = serializers.DateField(allow_null=True)


class TeachingAssignmentPageResponse(ClosedSerializer):
    """Cursor page of teaching assignments."""

    items = TeachingAssignmentResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class SubjectOfferingRequest(ClosedSerializer):
    """Create a subject offering."""

    year_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    optional_group = serializers.CharField(min_length=1, allow_null=True)


class SubjectOfferingResponse(ClosedSerializer):
    """One subject offering."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    year_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    optional_group = serializers.CharField(allow_null=True)
    archived = serializers.BooleanField()


class SubjectOfferingPageResponse(ClosedSerializer):
    """Cursor page of subject offerings."""

    items = SubjectOfferingResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class EnrolmentRequest(ClosedSerializer):
    """Create an enrolment."""

    student_id = serializers.UUIDField()
    year_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    from_date = serializers.DateField()
    to_date = serializers.DateField(allow_null=True)


class EnrolmentResponse(ClosedSerializer):
    """One enrolment."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    student_id = serializers.UUIDField()
    year_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    from_date = serializers.DateField()
    to_date = serializers.DateField(allow_null=True)
    previous_enrolment_id = serializers.UUIDField(allow_null=True)
    state = serializers.CharField()


class EnrolmentPageResponse(ClosedSerializer):
    """Cursor page of enrolments."""

    items = EnrolmentResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class TransferEnrolmentRequest(ClosedSerializer):
    """Transfer an enrolment to another section."""

    target_section_id = serializers.UUIDField()
    effective_date = serializers.DateField()
    expected_version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(min_length=1)


class SubjectEnrolmentRequest(ClosedSerializer):
    """Create a subject enrolment."""

    enrolment_id = serializers.UUIDField()
    subject_offering_id = serializers.UUIDField()
    from_date = serializers.DateField()
    to_date = serializers.DateField(allow_null=True)


class EndSubjectEnrolmentRequest(ClosedSerializer):
    """End a subject enrolment on an inclusive date."""

    to_date = serializers.DateField()
    expected_version = serializers.IntegerField(min_value=1)


class SubjectEnrolmentResponse(ClosedSerializer):
    """One subject enrolment."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    enrolment_id = serializers.UUIDField()
    subject_offering_id = serializers.UUIDField()
    from_date = serializers.DateField()
    to_date = serializers.DateField(allow_null=True)


class SubjectEnrolmentPageResponse(ClosedSerializer):
    """Cursor page of subject enrolments."""

    items = SubjectEnrolmentResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class RosterResponse(ClosedSerializer):
    """Section roster snapshot."""

    section_id = serializers.UUIDField()
    date = serializers.DateField()
    subject_id = serializers.UUIDField(allow_null=True)
    version = serializers.IntegerField()
    students = serializers.ListField(child=serializers.DictField())
