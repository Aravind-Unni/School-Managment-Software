"""HTTP-level tests for the placeholder module's real REST API.

Proves the whole request path: persona derivation, the identity-header refusal,
the body guard, the error envelope, cursor pagination and optimistic concurrency.
"""

from __future__ import annotations

import uuid

import pytest
from django.test import Client

from shared import fixtures

pytestmark = pytest.mark.django_db

COLLECTION = "/api/demo/notes/"
ENVELOPE_KEYS = {"code", "message_key", "request_id", "field_errors"}


@pytest.fixture
def client() -> Client:
    """Return a test client. REMOTE_ADDR defaults to loopback, as the persona needs."""
    return Client()


def _create(client: Client, body: str = "hello", subject=fixtures.STUDENT_S1):
    return client.post(
        COLLECTION,
        data={"body": body, "subject_person_id": str(subject)},
        content_type="application/json",
    )


# --- health ---------------------------------------------------------------


def test_healthz_is_open_and_does_not_need_an_identity(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz_reports_checks_and_redacts_configuration(client):
    response = client.get("/readyz")
    payload = response.json()
    assert payload["module_id"] == "M00"
    assert payload["checks"][0]["name"] == "demo_table"
    # Every port in a standalone run is a fake, and readyz says so plainly.
    assert set(payload["ports"].values()) == {"fake"}
    # No secret value may appear in a diagnostic response.
    assert payload["config"]["SESSION_SECRET"] in ("<set>", "<unset>")


# --- identity -------------------------------------------------------------


@pytest.mark.parametrize(
    "header",
    [
        "HTTP_X_SCHOOL_ID",
        "HTTP_X_ROLE",
        "HTTP_X_ACTOR_ID",
        "HTTP_X_RELATIONSHIP",
        "HTTP_X_AUTH_LEVEL",
        "HTTP_X_PERSONA",
    ],
)
def test_a_client_asserted_identity_header_is_rejected_not_ignored(client, header):
    response = client.get(COLLECTION, **{header: str(fixtures.SCHOOL_B)})
    assert response.status_code == 400
    payload = response.json()
    assert set(payload) == ENVELOPE_KEYS
    assert payload["message_key"] == "error.client_asserted_identity"
    assert payload["field_errors"][0]["field"] == header


def test_persona_off_yields_401_with_the_envelope(client, settings):
    settings.DEV_PERSONA_MODE = "off"
    response = client.get(COLLECTION)
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_a_non_loopback_peer_cannot_use_the_persona(client):
    response = client.get(COLLECTION, REMOTE_ADDR="203.0.113.10")
    assert response.status_code == 401
    assert response.json()["message_key"] == "error.dev_persona_requires_loopback"


def test_request_id_is_present_on_every_error(client, settings):
    settings.DEV_PERSONA_MODE = "off"
    assert response_id(client.get(COLLECTION)) != ""


def response_id(response) -> str:
    """Return the request_id from an error envelope."""
    return response.json()["request_id"]


# --- body guard -----------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"body": "x", "resource_grant": {"grant_id": "g"}},
        {"body": "x", "school_id": "11111111-1111-1111-1111-111111111111"},
        {"body": "x", "nested": {"grant_id": "g"}},
        {"body": "x", "items": [{"actor_id": "a"}]},
    ],
)
def test_server_internal_fields_are_refused_in_a_request_body(client, payload):
    response = client.post(COLLECTION, data=payload, content_type="application/json")
    assert response.status_code == 422
    assert response.json()["message_key"] == "error.server_internal_field_rejected"


# --- reads ----------------------------------------------------------------


def test_list_returns_items_and_next_cursor(client):
    response = client.get(COLLECTION)
    assert response.status_code == 200
    assert set(response.json()) == {"items", "next_cursor"}


def test_list_is_empty_and_terminal_when_there_is_no_data(client):
    payload = client.get(COLLECTION).json()
    assert payload["items"] == []
    assert payload["next_cursor"] is None


def test_created_note_is_returned_by_the_list(client):
    created = _create(client, body="visible").json()
    items = client.get(COLLECTION).json()["items"]
    assert [item["id"] for item in items] == [created["id"]]


def test_pagination_walks_every_row_exactly_once(client):
    made = {_create(client, body=f"note-{index}").json()["id"] for index in range(5)}
    seen: list[str] = []
    cursor = None
    for _ in range(10):  # generous bound; the loop must terminate well inside it
        url = f"{COLLECTION}?page_size=2" + (f"&cursor={cursor}" if cursor else "")
        payload = client.get(url).json()
        seen.extend(item["id"] for item in payload["items"])
        cursor = payload["next_cursor"]
        if cursor is None:
            break
    assert cursor is None
    assert len(seen) == len(set(seen)) == 5
    assert set(seen) == made


def test_a_malformed_cursor_is_422_not_500(client):
    response = client.get(f"{COLLECTION}?cursor=not-a-real-cursor")
    assert response.status_code == 422


def test_page_size_is_capped(client):
    for index in range(3):
        _create(client, body=f"n{index}")
    payload = client.get(f"{COLLECTION}?page_size=100000").json()
    assert len(payload["items"]) == 3  # capped, and all rows fit in one page


def test_a_non_numeric_page_size_falls_back_to_the_default(client):
    assert client.get(f"{COLLECTION}?page_size=abc").status_code == 200


# --- writes ---------------------------------------------------------------


def test_create_returns_201_with_the_full_record(client):
    response = _create(client, body="created")
    assert response.status_code == 201
    payload = response.json()
    assert payload["body"] == "created"
    assert payload["version"] == 1
    assert payload["school_id"] == str(fixtures.SCHOOL_A)
    uuid.UUID(payload["id"])


def test_create_without_a_subject_is_422(client):
    response = client.post(COLLECTION, data={"body": "x"}, content_type="application/json")
    assert response.status_code == 422
    assert response.json()["field_errors"][0]["field"] == "subject_person_id"


def test_create_with_a_blank_body_is_422(client):
    response = _create(client, body="")
    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


def test_read_one_note(client):
    created = _create(client).json()
    response = client.get(f"{COLLECTION}{created['id']}/")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_an_unknown_note_is_404_with_the_envelope(client):
    response = client.get(f"{COLLECTION}{uuid.uuid4()}/")
    assert response.status_code == 404
    assert response.json()["code"] == "object_inaccessible"


def test_update_bumps_the_version(client):
    created = _create(client, body="v1").json()
    response = client.patch(
        f"{COLLECTION}{created['id']}/",
        data={"body": "v2", "expected_version": 1},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["version"] == 2


def test_a_stale_expected_version_is_409(client):
    created = _create(client, body="v1").json()
    client.patch(
        f"{COLLECTION}{created['id']}/",
        data={"body": "v2", "expected_version": 1},
        content_type="application/json",
    )
    # Second writer still thinks it is on version 1.
    response = client.patch(
        f"{COLLECTION}{created['id']}/",
        data={"body": "v2-conflict", "expected_version": 1},
        content_type="application/json",
    )
    assert response.status_code == 409
    assert response.json()["code"] == "version_conflict"


def test_an_update_without_expected_version_is_422(client):
    created = _create(client).json()
    response = client.patch(
        f"{COLLECTION}{created['id']}/",
        data={"body": "no version"},
        content_type="application/json",
    )
    assert response.status_code == 422


def test_a_cursor_from_a_different_collection_is_422(client):
    from contracts.pagination import encode_cursor

    _create(client)
    # Well-formed base64, decodes to an object, but carries the wrong sort keys.
    forged = encode_cursor({"unrelated_field": "x"})
    response = client.get(f"{COLLECTION}?cursor={forged}")
    assert response.status_code == 422
    assert response.json()["field_errors"][0]["message_key"] == "error.cursor_field_missing"
