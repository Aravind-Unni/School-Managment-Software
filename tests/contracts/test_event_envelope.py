"""The outbox event envelope and audit record are frozen."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from contracts.events import EVENT_ENVELOPE_VERSION, AuditRecord, EventEnvelope

pytestmark = pytest.mark.contract

#: The wire shape as of school-contracts-v3-draft, after M01's additive
#: revision. "schema_version" is M01's name for the number B00 called
#: "envelope_version"; BOTH are emitted for one revision so neither side breaks.
#: The v4 revision should retire "envelope_version".
EXPECTED_EVENT_KEYS = {
    "event_id",
    "school_id",
    "event_type",
    "occurred_at",
    "aggregate_id",
    "aggregate_version",
    "payload",
    "envelope_version",
    "schema_version",
    "correlation_id",
}


def _event(**overrides) -> EventEnvelope:
    defaults = {
        "event_id": uuid.uuid4(),
        "school_id": uuid.uuid4(),
        "event_type": "demo.note_created",
        "occurred_at": datetime(2026, 7, 15, 4, 30, tzinfo=UTC),
        "aggregate_id": uuid.uuid4(),
        "aggregate_version": 1,
    }
    defaults.update(overrides)
    return EventEnvelope(**defaults)


def test_event_wire_shape_is_exactly_the_contract():
    assert set(_event().to_wire()) == EXPECTED_EVENT_KEYS


def test_event_type_must_be_module_namespaced():
    # An un-namespaced type would collide across modules in one outbox table.
    with pytest.raises(ValueError, match="module"):
        _event(event_type="note_created")


def test_naive_occurred_at_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        _event(occurred_at=datetime(2026, 7, 15, 4, 30))


def test_timestamps_serialise_as_iso_8601():
    assert _event().to_wire()["occurred_at"] == "2026-07-15T04:30:00+00:00"


def test_envelope_version_is_stamped_and_defaults_to_the_contract_version():
    assert _event().to_wire()["envelope_version"] == EVENT_ENVELOPE_VERSION


def test_payload_defaults_to_empty_and_is_copied_not_aliased():
    source = {"a": 1}
    event = _event(payload=source)
    source["b"] = 2
    assert event.to_wire()["payload"] == {"a": 1}


def test_audit_record_wire_shape_is_exactly_the_contract():
    record = AuditRecord(
        audit_id=uuid.uuid4(),
        school_id=uuid.uuid4(),
        actor_id=uuid.uuid4(),
        action="demo.update_note",
        resource_id=uuid.uuid4(),
        occurred_at=datetime(2026, 7, 15, 4, 30, tzinfo=UTC),
        request_id="req-9",
        before={"version": 1},
        after={"version": 2},
    )
    assert set(record.to_wire()) == {
        "audit_id",
        "school_id",
        "actor_id",
        "action",
        "resource_id",
        "occurred_at",
        "request_id",
        "before",
        "after",
    }


def test_schema_version_and_envelope_version_carry_the_same_number():
    """Two names for one field during the transition; they must never diverge."""
    wire = _event().to_wire()
    assert wire["schema_version"] == wire["envelope_version"] == EVENT_ENVELOPE_VERSION


def test_correlation_id_is_optional_and_defaults_to_null():
    """A worker-originated event need not invent a correlation id."""
    assert _event().to_wire()["correlation_id"] is None
    assert _event(correlation_id="req-7").to_wire()["correlation_id"] == "req-7"
