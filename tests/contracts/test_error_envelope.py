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
    # 429 was added with rate_limited in M01. The invariant that matters is
    # unchanged: every code has exactly one status, and the renderer derives the
    # status from the code rather than the two being set independently.
    assert set(HTTP_STATUS_BY_CODE) == set(ErrorCode)
    assert set(HTTP_STATUS_BY_CODE.values()) <= {401, 403, 404, 409, 422, 429}


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
        "rate_limited",
    ]


def test_version_conflict_carries_both_versions_for_a_useful_client_message():
    error = VersionConflict(expected_version=3, actual_version=5)
    assert (error.expected_version, error.actual_version) == (3, 5)


def test_envelope_is_immutable():
    envelope = ErrorEnvelope(ErrorCode.ACTION_DENIED, "error.x", "req-1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        envelope.code = ErrorCode.VALIDATION_FAILED  # type: ignore[misc]


def test_rate_limited_renders_429_and_carries_a_finite_retry_hint():
    """A throttled client must be told how long to wait.

    The cooldown is always finite: a permanent lockout would let an attacker deny
    a legitimate user access to their own account.
    """
    from contracts.errors import RateLimited

    error = RateLimited(retry_after_seconds=45)
    assert error.http_status == 429
    assert error.code is ErrorCode.RATE_LIMITED
    assert error.retry_after_seconds == 45
    assert error.message_key == "error.too_many_attempts"


def test_rate_limited_has_a_default_cooldown():
    from contracts.errors import RateLimited

    assert RateLimited().retry_after_seconds > 0
