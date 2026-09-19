"""The error envelope is frozen. These tests fail if its shape drifts."""

from __future__ import annotations

import dataclasses

import pytest

from contracts.errors import (
    HTTP_STATUS_BY_CODE,
    ActionDenied,
    ErrorCode,
    ErrorEnvelope,
    FieldError,
    ObjectInaccessible,
    StaleAuth,
    StateConflict,
    Unauthenticated,
    ValidationFailed,
    VersionConflict,
)

pytestmark = pytest.mark.contract

#: Exactly the four keys, in the contract. A fifth key is a breaking change.
EXPECTED_KEYS = {"code", "message_key", "request_id", "field_errors"}


def test_envelope_has_exactly_the_contracted_keys():
    envelope = ErrorEnvelope(ErrorCode.ACTION_DENIED, "error.action_denied", "req-1")
    assert set(envelope.to_wire()) == EXPECTED_KEYS


def test_field_errors_is_always_a_list_even_when_empty():
    # Clients must never have to branch on key absence.
    wire = ErrorEnvelope(ErrorCode.ACTION_DENIED, "error.x", "req-1").to_wire()
    assert wire["field_errors"] == []


def test_field_errors_serialise_as_field_and_message_key_only():
    envelope = ErrorEnvelope(
        ErrorCode.VALIDATION_FAILED,
        "error.validation_failed",
        "req-1",
        (FieldError("marks", "error.decimal_required"),),
    )
    assert envelope.to_wire()["field_errors"] == [
        {"field": "marks", "message_key": "error.decimal_required"}
    ]


@pytest.mark.parametrize(
    ("exception", "status"),
    [
        (Unauthenticated("k"), 401),
        (StaleAuth("k"), 401),
        (ActionDenied("k"), 403),
        (ObjectInaccessible("k"), 404),
        (VersionConflict(), 409),
        (StateConflict("k"), 409),
        (ValidationFailed("k"), 422),
    ],
)
def test_each_contract_error_maps_to_its_contracted_status(exception, status):
    assert exception.http_status == status


def test_status_map_covers_every_code_and_uses_only_contracted_statuses():
    assert set(HTTP_STATUS_BY_CODE) == set(ErrorCode)
    assert set(HTTP_STATUS_BY_CODE.values()) <= {401, 403, 404, 409, 422}


def test_code_values_are_stable_strings():
    # These strings are in the OpenAPI enum and in the TypeScript client.
    assert [code.value for code in ErrorCode] == [
        "unauthenticated",
        "stale_auth",
        "action_denied",
        "object_inaccessible",
        "version_conflict",
        "state_conflict",
        "validation_failed",
    ]


def test_version_conflict_carries_both_versions_for_a_useful_client_message():
    error = VersionConflict(expected_version=3, actual_version=5)
    assert (error.expected_version, error.actual_version) == (3, 5)


def test_envelope_is_immutable():
    envelope = ErrorEnvelope(ErrorCode.ACTION_DENIED, "error.x", "req-1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        envelope.code = ErrorCode.VALIDATION_FAILED  # type: ignore[misc]
