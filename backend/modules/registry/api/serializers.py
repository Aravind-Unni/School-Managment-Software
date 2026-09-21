"""Request and response shapes for M02, mirroring the frozen contract.

Every request serializer is CLOSED: an unknown field is a 422, not something
quietly ignored. That is what stops a client asserting ``school_id``, ``id`` or
``version`` and having it silently dropped -- dropping a spoofed field hides an
attack and a bug equally well.

Does not handle: authorisation or persistence. Views parse, services decide.
"""

from __future__ import annotations

from rest_framework import serializers

from shared.languages import LANGUAGE_CHOICES


class ClosedSerializer(serializers.Serializer):
    """A serializer that refuses fields it does not declare.

    DRF's default is to ignore unknown keys. For a write that carries identity
    and version, ignoring is the wrong default: the caller believes it sent
    something and the server believes it did not.
    """

    def to_internal_value(self, data):
        """Reject any key the serializer does not declare, then parse normally.

        Overrides to_internal_value rather than validate because ``validate``
        cannot see the raw payload of a NESTED serializer: only the outermost
        one has ``initial_data``. Checking here means a closed object stays
        closed at every depth, which is where a spoofed field would hide.
        """
        if isinstance(data, dict):
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise serializers.ValidationError(
                    dict.fromkeys(unknown, "error.field_not_accepted")
                )
        return super().to_internal_value(data)


class ProfileSerializer(ClosedSerializer):
    """The minimal pupil profile: an optional birth date and a language.

    Deliberately small. No Aadhaar and no identity document: this module
    collects the least that makes a school record usable.
    """

    date_of_birth = serializers.DateField(allow_null=True)
    preferred_language = serializers.ChoiceField(choices=LANGUAGE_CHOICES)


class ExternalIdSerializer(ClosedSerializer):
    """A stable handle for a person in another system."""

    source = serializers.CharField(min_length=1, max_length=64)
    value = serializers.CharField(min_length=1, max_length=128)


class DuplicateAcknowledgementSerializer(ClosedSerializer):
    """A reviewer's assertion that the candidates shown are different people.

    ``distinct_person_reason`` is nullable in the schema so the shape can be
    sent unfilled, but the service refuses a null: a reason is the decision.
    """

    review_id = serializers.UUIDField()
    review_version = serializers.IntegerField(min_value=1)
    distinct_person_reason = serializers.CharField(
        min_length=1, allow_null=True, max_length=500
    )


class InitialGuardianLinkSerializer(ClosedSerializer):
    """A dated guardian link supplied at admission. Honoured from step 2."""

    guardian_id = serializers.UUIDField()
    visibility = serializers.ChoiceField(choices=("academic", "none"))
    from_date = serializers.DateField()
    to_date = serializers.DateField(allow_null=True)


class CreateStudentRequest(ClosedSerializer):
    """Admit a student. Mirrors the frozen CreateStudent shape exactly."""

    admission_no = serializers.CharField(min_length=1, max_length=64)
    display_name = serializers.CharField(min_length=1, max_length=200)
    profile = ProfileSerializer()
    guardian_links = InitialGuardianLinkSerializer(many=True)
    external_ids = ExternalIdSerializer(many=True)
    duplicate_review = DuplicateAcknowledgementSerializer(allow_null=True)


class UpdateStudentRequest(ClosedSerializer):
    """Amend a student's profile under optimistic concurrency."""

    display_name = serializers.CharField(min_length=1, max_length=200)
    profile = ProfileSerializer()
    external_ids = ExternalIdSerializer(many=True)
    expected_version = serializers.IntegerField(min_value=1)


class DuplicateReviewRequest(ClosedSerializer):
    """Ask which stored students a proposed admission may duplicate."""

    admission_no = serializers.CharField(min_length=1, max_length=64)
    display_name = serializers.CharField(min_length=1, max_length=200)
    profile = ProfileSerializer()


class GuardianRequest(ClosedSerializer):
    """Create a guardian. Both contact details are genuinely optional."""

    display_name = serializers.CharField(min_length=1, max_length=200)
    email = serializers.EmailField(allow_null=True)
    phone = serializers.CharField(min_length=1, max_length=32, allow_null=True)
    external_ids = ExternalIdSerializer(many=True)


class StaffRequest(ClosedSerializer):
    """Create a staff person record."""

    display_name = serializers.CharField(min_length=1, max_length=200)
    external_ids = ExternalIdSerializer(many=True)


class UpdateSchoolConfigRequest(ClosedSerializer):
    """Replace the school configuration's mutable fields."""

    display_name = serializers.CharField(min_length=1, max_length=200)
    board = serializers.ChoiceField(choices=("CBSE",))
    default_language = serializers.ChoiceField(choices=LANGUAGE_CHOICES)
    expected_version = serializers.IntegerField(min_value=1)


class AcademicYearRequest(ClosedSerializer):
    """Create an academic year. It always starts in draft."""

    name = serializers.CharField(min_length=1, max_length=64)
    start = serializers.DateField()
    end = serializers.DateField()


class TermRequest(ClosedSerializer):
    """Create a term inside an existing year."""

    year_id = serializers.UUIDField()
    name = serializers.CharField(min_length=1, max_length=64)
    start = serializers.DateField()
    end = serializers.DateField()


class StandardRequest(ClosedSerializer):
    """Create a class level. The 1-12 bound is enforced by the service."""

    number = serializers.IntegerField()


class SectionRequest(ClosedSerializer):
    """Create a division of a standard within a year."""

    year_id = serializers.UUIDField()
    standard_id = serializers.UUIDField()
    name = serializers.CharField(min_length=1, max_length=32)


class SubjectRequest(ClosedSerializer):
    """Create a school-authored subject."""

    code = serializers.CharField(min_length=1, max_length=32)
    display_name = serializers.CharField(min_length=1, max_length=128)


class ArchiveRequest(ClosedSerializer):
    """Archive a row under optimistic concurrency. Archive is never a delete."""

    expected_version = serializers.IntegerField(min_value=1)


class ErrorEnvelopeResponse(ClosedSerializer):
    """The shared error body, declared so generated clients carry it.

    Mirrors contracts/common/error-envelope.schema.json exactly. It is FLAT --
    there is no nested ``error`` object -- which is worth stating because
    assuming a wrapper is an easy and silent mistake for a client to make.
    """

    code = serializers.CharField()
    message_key = serializers.CharField()
    request_id = serializers.CharField()
    field_errors = serializers.ListField(child=serializers.DictField())


class SchoolConfigResponse(ClosedSerializer):
    """The school configuration record."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    display_name = serializers.CharField()
    board = serializers.CharField()
    default_language = serializers.CharField()
    settings = serializers.DictField(required=False)


class AcademicYearResponse(ClosedSerializer):
    """One academic year."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    name = serializers.CharField()
    start = serializers.DateField()
    end = serializers.DateField()
    state = serializers.CharField()


class TermResponse(ClosedSerializer):
    """One term within a year."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    year_id = serializers.UUIDField()
    name = serializers.CharField()
    start = serializers.DateField()
    end = serializers.DateField()
    archived = serializers.BooleanField()


class StandardResponse(ClosedSerializer):
    """One class level."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    number = serializers.IntegerField()
    archived = serializers.BooleanField()


class SectionResponse(ClosedSerializer):
    """One division of a standard within a year."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    year_id = serializers.UUIDField()
    standard_id = serializers.UUIDField()
    name = serializers.CharField()
    archived = serializers.BooleanField()


class SubjectResponse(ClosedSerializer):
    """One school-authored subject."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    code = serializers.CharField()
    display_name = serializers.CharField()
    archived = serializers.BooleanField()


class StudentDTOResponse(ClosedSerializer):
    """The minimal student other modules consume. Deliberately has no version."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    admission_no = serializers.CharField()
    display_name = serializers.CharField()
    status = serializers.CharField()


class StudentRecordResponse(ClosedSerializer):
    """The versioned browser record. A different shape from StudentDTO."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    admission_no = serializers.CharField()
    display_name = serializers.CharField()
    status = serializers.CharField()
    profile = ProfileSerializer()
    external_ids = ExternalIdSerializer(many=True)
    archived = serializers.BooleanField()


class StudentRecordPageResponse(ClosedSerializer):
    """One cursor page of student records."""

    items = StudentRecordResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class DuplicateCandidateResponse(ClosedSerializer):
    """One student a proposed admission may duplicate, and why."""

    student_id = serializers.UUIDField()
    version = serializers.IntegerField()
    reason = serializers.CharField()


class DuplicateReviewResponse(ClosedSerializer):
    """A review token, the candidates it pins, and when it stops being usable."""

    review_id = serializers.UUIDField()
    review_version = serializers.IntegerField()
    candidates = DuplicateCandidateResponse(many=True)
    expires_at = serializers.DateTimeField()


class GuardianResponse(ClosedSerializer):
    """One guardian record. Holds no access rights by itself."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    display_name = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    phone = serializers.CharField(allow_null=True)
    external_ids = ExternalIdSerializer(many=True)
    archived = serializers.BooleanField()


class StaffResponse(ClosedSerializer):
    """One staff person record, independent of any login account."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    display_name = serializers.CharField()
    external_ids = ExternalIdSerializer(many=True)
    archived = serializers.BooleanField()
