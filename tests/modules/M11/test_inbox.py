"""Notice inbox: parents see notices sent to their child's class, no others."""

from __future__ import annotations

import json

import pytest

from shared import fixtures

pytestmark = [pytest.mark.module]


def _publish(client, notice_id):
    response = client.post(
        f"/api/v1/notices/{notice_id}/publish",
        data=json.dumps({"expected_version": 1}),
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    return response.json()


def test_a_parent_sees_a_notice_sent_to_their_childs_class(client, baseline, as_persona):
    published = _publish(client, baseline["notice_en_id"])
    recipients = set(published["audience_snapshot"]["recipient_ids"])
    guardian = next(
        link.guardian_id
        for link in fixtures.GUARDIAN_LINKS
        if str(link.student_id) in recipients
    )
    as_persona(guardian)
    items = client.get("/api/v1/notices/inbox").json()["items"]
    assert [row["id"] for row in items] == [baseline["notice_en_id"]]


def test_an_unrelated_parent_sees_nothing(client, baseline, as_persona):
    published = _publish(client, baseline["notice_en_id"])
    recipients = set(published["audience_snapshot"]["recipient_ids"])
    outsiders = [
        link.guardian_id
        for link in fixtures.GUARDIAN_LINKS
        if str(link.student_id) not in recipients
        and not any(
            other.guardian_id == link.guardian_id and str(other.student_id) in recipients
            for other in fixtures.GUARDIAN_LINKS
        )
    ]
    if not outsiders:
        pytest.skip("fixture cast has no guardian outside the audience")
    as_persona(outsiders[0])
    assert client.get("/api/v1/notices/inbox").json()["items"] == []
