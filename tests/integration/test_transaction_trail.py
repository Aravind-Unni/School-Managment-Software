"""Audit and outbox writes must join the caller's transaction.

This is the behavioural contract the Platform TEST adapter shares with M14's
real implementation. If these pass against the harness tables and fail against
M14, the contract is broken, not the tests.
"""

from __future__ import annotations

import uuid

import pytest
from django.db import transaction

from contracts.errors import VersionConflict
from modules.demo.models import DemoNote
from modules.demo.services import DemoNoteService
from shared import fixtures
from shared.harness.models import HarnessAuditRecord, HarnessOutboxEvent

pytestmark = pytest.mark.django_db


@pytest.fixture
def service(resolver, fake_platform, clock) -> DemoNoteService:
    """Return the demo service over the fakes and the controlled clock."""
    return DemoNoteService(resolver=resolver, platform=fake_platform, clock=clock)


def test_a_committed_write_leaves_exactly_one_audit_row_and_one_event(
    service, teacher_t1_context
):
    view = service.create_note(
        teacher_t1_context, body="first", subject_person_id=fixtures.STUDENT_S1
    )
    assert HarnessAuditRecord.objects.filter(resource_id=view.id).count() == 1
    assert HarnessOutboxEvent.objects.filter(aggregate_id=view.id).count() == 1


def test_the_audit_row_records_actor_action_and_request_id(service, teacher_t1_context):
    view = service.create_note(
        teacher_t1_context, body="first", subject_person_id=fixtures.STUDENT_S1
    )
    audit = HarnessAuditRecord.objects.get(resource_id=view.id)
    assert audit.actor_id == fixtures.TEACHER_T1
    assert audit.school_id == fixtures.SCHOOL_A
    assert audit.action == "demo.create_note"
    assert audit.request_id == teacher_t1_context.request_id


def test_the_event_carries_the_post_write_aggregate_version(service, teacher_t1_context):
    view = service.create_note(
        teacher_t1_context, body="first", subject_person_id=fixtures.STUDENT_S1
    )
    event = HarnessOutboxEvent.objects.get(aggregate_id=view.id)
    assert event.aggregate_version == view.version == 1
    assert event.event_type == "demo.create_noted"
    assert event.school_id == fixtures.SCHOOL_A


def test_an_update_records_before_and_after(service, teacher_t1_context):
    view = service.create_note(
        teacher_t1_context, body="first", subject_person_id=fixtures.STUDENT_S1
    )
    service.update_note(teacher_t1_context, view.id, body="second", expected_version=1)
    audit = HarnessAuditRecord.objects.get(resource_id=view.id, action="demo.update_note")
    assert audit.before == {"body": "first", "version": 1}
    assert audit.after == {"body": "second", "version": 2}


@pytest.mark.django_db(transaction=True)
def test_rolling_back_the_caller_removes_the_audit_row_and_the_event(
    service, teacher_t1_context
):
    """The central rollback assertion.

    The adapter must not open its own transaction. If it did, the audit row
    would survive a rolled-back domain write and the trail would lie.
    """
    before_audit = HarnessAuditRecord.objects.count()
    before_events = HarnessOutboxEvent.objects.count()
    before_notes = DemoNote.objects.count()

    class DeliberateRollbackError(Exception):
        pass

    with pytest.raises(DeliberateRollbackError):
        with transaction.atomic():
            service.create_note(
                teacher_t1_context, body="doomed", subject_person_id=fixtures.STUDENT_S1
            )
            # Prove the rows existed inside the transaction before rolling back.
            assert HarnessAuditRecord.objects.count() == before_audit + 1
            assert HarnessOutboxEvent.objects.count() == before_events + 1
            raise DeliberateRollbackError

    assert DemoNote.objects.count() == before_notes
    assert HarnessAuditRecord.objects.count() == before_audit
    assert HarnessOutboxEvent.objects.count() == before_events


@pytest.mark.django_db(transaction=True)
def test_a_denied_write_leaves_no_trail_at_all(service, guardian_g1_context):
    from contracts.errors import ActionDenied

    before = (HarnessAuditRecord.objects.count(), HarnessOutboxEvent.objects.count())
    with pytest.raises(ActionDenied):
        service.create_note(
            guardian_g1_context, body="nope", subject_person_id=fixtures.STUDENT_S1
        )
    assert (HarnessAuditRecord.objects.count(), HarnessOutboxEvent.objects.count()) == before


def test_a_version_conflict_leaves_no_second_audit_row(service, teacher_t1_context):
    view = service.create_note(
        teacher_t1_context, body="first", subject_person_id=fixtures.STUDENT_S1
    )
    with pytest.raises(VersionConflict) as raised:
        service.update_note(teacher_t1_context, view.id, body="stale", expected_version=99)
    assert raised.value.expected_version == 99
    assert raised.value.actual_version == 1
    assert HarnessAuditRecord.objects.filter(resource_id=view.id).count() == 1


def test_version_increments_by_one_per_write(service, teacher_t1_context):
    view = service.create_note(
        teacher_t1_context, body="v1", subject_person_id=fixtures.STUDENT_S1
    )
    assert view.version == 1
    view = service.update_note(teacher_t1_context, view.id, body="v2", expected_version=1)
    assert view.version == 2
    view = service.update_note(teacher_t1_context, view.id, body="v3", expected_version=2)
    assert view.version == 3


def test_a_note_in_another_school_is_invisible_not_forbidden(service, teacher_t1_context):
    from contracts.errors import ObjectInaccessible

    other = DemoNote.objects.create(
        id=uuid.uuid4(),
        school_id=fixtures.SCHOOL_B,
        subject_person_id=fixtures.STUDENT_S1_SCHOOL_B,
        body="other school",
        version=1,
        created_at=teacher_t1_context.auth_time,
        updated_at=teacher_t1_context.auth_time,
    )
    with pytest.raises(ObjectInaccessible):
        service.get_note(teacher_t1_context, other.id)


def test_enqueue_refuses_to_fake_async_work(fake_platform):
    """Eager mode must not be mistaken for a working worker."""
    from shared.fakes import EagerModeNotAsserted

    assert fake_platform.supports_worker_assertions is False
    with pytest.raises(EagerModeNotAsserted, match="requires a real broker"):
        fake_platform.enqueue("modules.demo.tasks.noop", payload={})


def test_records_are_uuid_keyed_and_school_scoped(service, teacher_t1_context):
    view = service.create_note(
        teacher_t1_context, body="x", subject_person_id=fixtures.STUDENT_S1
    )
    note = DemoNote.objects.get(id=view.id)
    assert isinstance(note.id, uuid.UUID)
    assert note.school_id == fixtures.SCHOOL_A
    assert note.version == 1
