"""RegistryPort basics against real M02 tables (SQLite test profile)."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from django.conf import settings

from contracts.errors import ObjectInaccessible
from contracts.identity import AuthLevel, RequestContext
from contracts.people import StudentStatus
from contracts.scope import Relationship
from shared import fixtures


@pytest.fixture
def registry_cast(db):
    """Install the integrated synthetic cast into the test database."""
    from config.integration_seed import integration

    return integration()


def _context(*, actor_id=fixtures.TEACHER_T1) -> RequestContext:
    """Build a school-A context for port reads."""
    return RequestContext(
        actor_id=actor_id,
        school_id=fixtures.SCHOOL_A,
        request_id=uuid4(),
        auth_level=AuthLevel.TWO_FACTOR,
        auth_time=settings.SCHOOL_CLOCK.now(),
    )


@pytest.mark.django_db
def test_registry_port_get_student_and_roster(registry_cast):
    """Real RegistryPort returns fixture students and a filtered roster."""
    from modules.registry.services.port import registry_service

    port = registry_service()
    context = _context()
    student = port.get_student(context, fixtures.STUDENT_S1)
    assert student.status == StudentStatus.ACTIVE
    assert student.admission_no == "S1-2026"

    roster = port.get_roster(context, fixtures.CLASS_C1, date(2026, 7, 15))
    assert {entry.student_id for entry in roster.students} == {
        fixtures.STUDENT_S1,
        fixtures.STUDENT_S2,
    }

    filtered = port.get_roster(
        context, fixtures.CLASS_C1, date(2026, 7, 15), subject_id=fixtures.SUBJECT_MATHS
    )
    assert len(filtered.students) == 2


@pytest.mark.django_db
def test_registry_port_relationships_and_assignments(registry_cast):
    """Guardian and class-teacher relationships resolve from stored links."""
    from modules.registry.services.port import registry_service

    port = registry_service()
    on = date(2026, 7, 15)
    guardian = port.get_relationships(
        _context(actor_id=fixtures.GUARDIAN_G1),
        fixtures.GUARDIAN_G1,
        fixtures.STUDENT_S1,
        on,
    )
    assert guardian.relationship == Relationship.GUARDIAN

    assignments = port.get_teaching_assignments(
        _context(), fixtures.TEACHER_T1, on
    )
    assert len(assignments) == 1
    assert assignments[0].section_id == fixtures.CLASS_C1


@pytest.mark.django_db
def test_registry_port_cross_school_student_is_inaccessible(registry_cast):
    """Missing and other-school students both raise ObjectInaccessible."""
    from modules.registry.services.port import registry_service

    port = registry_service()
    with pytest.raises(ObjectInaccessible):
        port.get_student(_context(), fixtures.STUDENT_S1_SCHOOL_B)
