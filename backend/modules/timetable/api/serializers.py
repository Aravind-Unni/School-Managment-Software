"""Request and response shapes for M03, mirroring the frozen contract.

Every request serializer is CLOSED: an unknown field is a 422, not something
quietly ignored. That is what stops a client asserting ``school_id``, ``id`` or
``version`` and having it silently dropped -- dropping a spoofed field hides an
attack and a bug equally well.

Local times cross the wire as "HH:MM" school wall-clock strings and instants as
UTC ISO-8601. The two are never mixed: a period is stated in school time because
that is how a school states it, and an instant is stored in UTC because that is
the only representation that survives a timezone database update.

Does not handle: authorisation or persistence. Views parse, services decide.
"""

from __future__ import annotations

from rest_framework import serializers

from ..models import CALENDAR_KINDS, TIMETABLE_STATES

#: Wire format for a school wall-clock time. Matches the frozen schema pattern.
LOCAL_TIME_FORMATS = ["%H:%M"]
KIND_CHOICES = tuple(kind for kind, _label in CALENDAR_KINDS)
STATE_CHOICES = tuple(state for state, _label in TIMETABLE_STATES)


class ClosedSerializer(serializers.Serializer):
    """A serializer that refuses fields it does not declare.

    DRF's default is to ignore unknown keys. For a write that carries identity
    and version, ignoring is the wrong default: the caller believes it sent
    something and the server believes it did not.

    Overrides ``to_internal_value`` rather than ``validate`` because ``validate``
    cannot see the raw payload of a NESTED serializer -- only the outermost one
    has ``initial_data``. Checking here means a closed object stays closed at
    every depth, which is where a spoofed field would hide.
    """

    def to_internal_value(self, data):
        """Reject any key the serializer does not declare, then parse normally."""
        if isinstance(data, dict):
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise serializers.ValidationError(
                    dict.fromkeys(unknown, "error.field_not_accepted")
                )
        return super().to_internal_value(data)


# --- request shapes ---------------------------------------------------------


class PeriodTemplateRequest(ClosedSerializer):
    """One bell-time row in a draft grid."""

    day_of_week = serializers.IntegerField(min_value=1, max_value=7)
    slot_code = serializers.CharField(min_length=1, max_length=16)
    starts_at_local = serializers.TimeField(input_formats=LOCAL_TIME_FORMATS, format="%H:%M")
    ends_at_local = serializers.TimeField(input_formats=LOCAL_TIME_FORMATS, format="%H:%M")


class SlotRequest(ClosedSerializer):
    """One cell in a draft grid.

    The period is named by weekday and slot code rather than by id, so a whole
    week can be sent before its period rows exist.
    """

    day_of_week = serializers.IntegerField(min_value=1, max_value=7)
    slot_code = serializers.CharField(min_length=1, max_length=16)
    section_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    teacher_id = serializers.UUIDField()
    room_code = serializers.CharField(
        max_length=32, allow_null=True, required=False, default=None
    )


class CreateTimetableRequest(ClosedSerializer):
    """Create a draft revision. Never creates a published one."""

    year_id = serializers.UUIDField()
    effective_from = serializers.DateField()
    effective_to = serializers.DateField(allow_null=True, required=False, default=None)
    periods = PeriodTemplateRequest(many=True)
    slots = SlotRequest(many=True)


class ReplaceTimetableRequest(ClosedSerializer):
    """Replace a draft's whole grid under optimistic locking."""

    effective_from = serializers.DateField()
    effective_to = serializers.DateField(allow_null=True, required=False, default=None)
    periods = PeriodTemplateRequest(many=True)
    slots = SlotRequest(many=True)
    expected_version = serializers.IntegerField(min_value=1)


class PublishRequest(ClosedSerializer):
    """Publish the draft the caller last read."""

    expected_version = serializers.IntegerField(min_value=1)


class CalendarExceptionRequest(ClosedSerializer):
    """Record one exception to the weekly pattern."""

    date = serializers.DateField()
    kind = serializers.ChoiceField(choices=KIND_CHOICES)
    reason_key = serializers.CharField(
        max_length=64, allow_null=True, required=False, default=None
    )


class UpdateCalendarExceptionRequest(ClosedSerializer):
    """Amend or withdraw an exception. Withdrawn, never deleted."""

    kind = serializers.ChoiceField(choices=KIND_CHOICES)
    reason_key = serializers.CharField(
        max_length=64, allow_null=True, required=False, default=None
    )
    withdrawn = serializers.BooleanField()
    expected_version = serializers.IntegerField(min_value=1)


class TeacherUnavailableRequest(ClosedSerializer):
    """Record a staff member's unavailability as a half-open UTC interval."""

    staff_id = serializers.UUIDField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    reason_key = serializers.CharField(
        max_length=64, allow_null=True, required=False, default=None
    )


class UpdateTeacherUnavailableRequest(ClosedSerializer):
    """Amend or withdraw an unavailability interval."""

    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    reason_key = serializers.CharField(
        max_length=64, allow_null=True, required=False, default=None
    )
    withdrawn = serializers.BooleanField()
    expected_version = serializers.IntegerField(min_value=1)


class SubstitutionRequest(ClosedSerializer):
    """Assign a substitute to one dated period."""

    date = serializers.DateField()
    slot_id = serializers.UUIDField()
    teacher_id = serializers.UUIDField()
    reason = serializers.CharField(min_length=1, max_length=200)
    valid_until = serializers.DateTimeField(allow_null=True, required=False, default=None)


class UpdateSubstitutionRequest(ClosedSerializer):
    """Withdraw a substitution. A register may already cite it."""

    withdrawn = serializers.BooleanField()
    expected_version = serializers.IntegerField(min_value=1)


class SessionCancellationRequest(ClosedSerializer):
    """Cancel or restore one dated period without touching the recurring grid."""

    cancelled = serializers.BooleanField()
    reason_key = serializers.CharField(
        max_length=64, allow_null=True, required=False, default=None
    )
    #: Null on the first cancellation of a session, which has no record yet.
    expected_version = serializers.IntegerField(min_value=1, allow_null=True)


# --- response shapes, for the generated schema ------------------------------


class FieldErrorResponse(serializers.Serializer):
    """One field-scoped validation problem."""

    field = serializers.CharField()
    message_key = serializers.CharField()


class ErrorEnvelopeResponse(serializers.Serializer):
    """The frozen error body. M03 adds no field to it."""

    code = serializers.CharField()
    message_key = serializers.CharField()
    request_id = serializers.CharField()
    field_errors = FieldErrorResponse(many=True)


class PeriodTemplateResponse(serializers.Serializer):
    """One bell-time row as served."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    timetable_id = serializers.UUIDField()
    day_of_week = serializers.IntegerField()
    slot_code = serializers.CharField()
    starts_at_local = serializers.CharField()
    ends_at_local = serializers.CharField()


class SlotResponse(serializers.Serializer):
    """One grid cell as served."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    timetable_id = serializers.UUIDField()
    period_template_id = serializers.UUIDField()
    day_of_week = serializers.IntegerField()
    slot_code = serializers.CharField()
    section_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    teacher_id = serializers.UUIDField()
    room_code = serializers.CharField(allow_null=True)


class TimetableVersionResponse(serializers.Serializer):
    """One revision with its whole grid."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    year_id = serializers.UUIDField()
    effective_from = serializers.DateField()
    effective_to = serializers.DateField(allow_null=True)
    state = serializers.ChoiceField(choices=STATE_CHOICES)
    published_at = serializers.DateTimeField(allow_null=True)
    periods = PeriodTemplateResponse(many=True)
    slots = SlotResponse(many=True)


class TimetableSummaryResponse(serializers.Serializer):
    """One revision without its grid, for listing."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    year_id = serializers.UUIDField()
    effective_from = serializers.DateField()
    effective_to = serializers.DateField(allow_null=True)
    state = serializers.ChoiceField(choices=STATE_CHOICES)
    published_at = serializers.DateTimeField(allow_null=True)
    period_count = serializers.IntegerField()
    slot_count = serializers.IntegerField()


class TimetablePageResponse(serializers.Serializer):
    """A page of revisions."""

    items = TimetableSummaryResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class ConflictResponse(serializers.Serializer):
    """One detected conflict."""

    code = serializers.CharField()
    message_key = serializers.CharField()
    blocking = serializers.BooleanField()
    slot_ids = serializers.ListField(child=serializers.UUIDField())
    teacher_id = serializers.UUIDField(allow_null=True)
    section_id = serializers.UUIDField(allow_null=True)
    date = serializers.DateField(allow_null=True)


class ValidationReportResponse(serializers.Serializer):
    """The result of validating a draft."""

    timetable_id = serializers.UUIDField()
    version = serializers.IntegerField()
    conflicts = ConflictResponse(many=True)


class PublishResultResponse(serializers.Serializer):
    """The outcome of publishing a draft."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    state = serializers.CharField()
    effective_from = serializers.DateField()
    effective_to = serializers.DateField(allow_null=True)
    superseded_timetable_id = serializers.UUIDField(allow_null=True)


class PeriodSessionResponse(serializers.Serializer):
    """One dated teaching period."""

    timetable_session_id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    date = serializers.DateField()
    slot_id = serializers.UUIDField()
    slot_code = serializers.CharField()
    subject_id = serializers.UUIDField()
    assigned_teacher_id = serializers.UUIDField()
    substitute_teacher_id = serializers.UUIDField(allow_null=True)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    starts_at_local = serializers.CharField()
    ends_at_local = serializers.CharField()
    cancelled = serializers.BooleanField()
    cancellation_reason_key = serializers.CharField(allow_null=True)
    room_code = serializers.CharField(allow_null=True)
    timetable_id = serializers.UUIDField()
    timetable_version = serializers.IntegerField()


class SectionDayResponse(serializers.Serializer):
    """One section's effective schedule for a date."""

    section_id = serializers.UUIDField()
    date = serializers.DateField()
    is_school_day = serializers.BooleanField()
    reason_key = serializers.CharField(allow_null=True)
    timetable_id = serializers.UUIDField(allow_null=True)
    timetable_version = serializers.IntegerField(allow_null=True)
    sessions = PeriodSessionResponse(many=True)


class TeacherDayResponse(serializers.Serializer):
    """One teacher's dated schedule, including cover duties."""

    staff_id = serializers.UUIDField()
    date = serializers.DateField()
    is_school_day = serializers.BooleanField()
    reason_key = serializers.CharField(allow_null=True)
    sessions = PeriodSessionResponse(many=True)


class StudentSessionResponse(serializers.Serializer):
    """One session as a pupil sees it."""

    session = PeriodSessionResponse()
    enrolled = serializers.BooleanField()


class StudentDayResponse(serializers.Serializer):
    """One pupil's dated schedule."""

    student_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    date = serializers.DateField()
    is_school_day = serializers.BooleanField()
    reason_key = serializers.CharField(allow_null=True)
    sessions = StudentSessionResponse(many=True)


class CalendarDayResponse(serializers.Serializer):
    """Whether one date is a teaching day."""

    date = serializers.DateField()
    is_school_day = serializers.BooleanField()
    reason_key = serializers.CharField(allow_null=True)
    kinds = serializers.ListField(child=serializers.CharField())


class CalendarResponse(serializers.Serializer):
    """A dated range of calendar answers."""

    from_date = serializers.DateField()
    to_date = serializers.DateField()
    days = CalendarDayResponse(many=True)


class CalendarExceptionResponse(serializers.Serializer):
    """One school-authored exception."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    date = serializers.DateField()
    kind = serializers.ChoiceField(choices=KIND_CHOICES)
    reason_key = serializers.CharField(allow_null=True)
    withdrawn = serializers.BooleanField()


class CalendarExceptionPageResponse(serializers.Serializer):
    """A page of calendar exceptions."""

    items = CalendarExceptionResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class TeacherUnavailableResponse(serializers.Serializer):
    """One unavailability interval."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    staff_id = serializers.UUIDField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    reason_key = serializers.CharField(allow_null=True)
    withdrawn = serializers.BooleanField()


class TeacherUnavailablePageResponse(serializers.Serializer):
    """A page of unavailability intervals."""

    items = TeacherUnavailableResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class SubstitutionResponse(serializers.Serializer):
    """One dated substitution."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    version = serializers.IntegerField()
    date = serializers.DateField()
    slot_id = serializers.UUIDField()
    timetable_session_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    original_teacher_id = serializers.UUIDField()
    substitute_teacher_id = serializers.UUIDField()
    reason = serializers.CharField()
    valid_until = serializers.DateTimeField()
    withdrawn = serializers.BooleanField()


class SubstitutionPageResponse(serializers.Serializer):
    """A page of substitutions."""

    items = SubstitutionResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)
