"""Acceptance cases: concurrent issue, return idempotency, overdues, isolation."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from shared import fixtures
from shared.harness.models import HarnessOutboxEvent

pytestmark = [pytest.mark.module]


def _issue(client, copy_id, borrower_id, due_date, key):
    """POST issue with Idempotency-Key."""
    return client.post(
        "/api/v1/library/loans",
        data=json.dumps(
            {
                "copy_id": copy_id,
                "borrower_person_id": borrower_id,
                "borrower_type": "student",
                "due_date": due_date,
            }
        ),
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=key,
    )


def test_concurrent_issue_one_winner(client, baseline):
    """Second issue of the same copy conflicts; one open loan remains."""
    copy_id = baseline["copy_id"]
    first = _issue(client, copy_id, baseline["student_s1"], "2026-10-01", "issue-1")
    assert first.status_code == 201, first.content
    second = _issue(client, copy_id, baseline["student_s2"], "2026-10-01", "issue-2")
    assert second.status_code == 409
    assert second.json()["message_key"] == "library.error.copy_not_available"
    from modules.library.models import Loan

    assert Loan.objects.filter(copy_id=copy_id, returned_at__isnull=True).count() == 1


def test_repeat_return_harmless(client, baseline):
    """Returning twice leaves one return and one return event."""
    issued = _issue(
        client, baseline["copy_id"], baseline["student_s1"], "2026-10-01", "ret-issue"
    )
    assert issued.status_code == 201
    loan = issued.json()
    body = {
        "returned_at": "2026-09-21T05:00:00Z",
        "condition": "ok",
        "expected_version": loan["version"],
    }
    first = client.post(
        f"/api/v1/library/loans/{loan['id']}/return",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert first.status_code == 200, first.content
    assert first.json()["returned_at"] is not None
    second = client.post(
        f"/api/v1/library/loans/{loan['id']}/return",
        data=json.dumps({**body, "expected_version": 99}),
        content_type="application/json",
    )
    assert second.status_code == 200
    assert second.json()["id"] == loan["id"]
    assert HarnessOutboxEvent.objects.filter(event_type="library.loan_returned").count() == 1


def test_overdue_date_correct_in_school_timezone(client, baseline, clock):
    """due_date < as_of is overdue; equal as_of is not."""
    from datetime import date
    from uuid import UUID

    from modules.library.models import Copy, CopyState, Loan

    copy = Copy.objects.get(id=UUID(baseline["copy_id"]))
    Loan.objects.create(
        school_id=fixtures.SCHOOL_A,
        copy_id=copy.id,
        borrower_person_id=fixtures.STUDENT_S1,
        borrower_type="student",
        issued_at=datetime(2026, 8, 1, 4, 30, tzinfo=UTC),
        due_date=date(2026, 9, 1),
        returned_at=None,
        version=1,
    )
    copy.state = CopyState.ON_LOAN
    copy.save(update_fields=["state"])

    before = client.get("/api/v1/library/overdues?as_of=2026-09-01")
    assert before.status_code == 200
    assert before.json()["items"] == []

    after = client.get("/api/v1/library/overdues?as_of=2026-09-02")
    assert after.status_code == 200
    assert len(after.json()["items"]) == 1
    assert after.json()["items"][0]["due_date"] == "2026-09-01"
    assert HarnessOutboxEvent.objects.filter(event_type="library.overdue_detected").count() == 1


def test_unauthorized_loans_hidden(client, baseline, as_persona):
    """S2 cannot view S1 loans (404)."""
    issued = _issue(
        client, baseline["copy_id"], baseline["student_s1"], "2026-10-01", "hide-issue"
    )
    assert issued.status_code == 201
    as_persona(fixtures.STUDENT_S2)
    res = client.get(f"/api/v1/library/borrowers/{baseline['student_s1']}/loans")
    assert res.status_code == 404


def test_duplicate_accession_rejected(client, baseline):
    """Second copy with same accession_no is 422."""
    res = client.post(
        "/api/v1/library/copies",
        data=json.dumps({"title_id": baseline["title_id"], "accession_no": "ACC-1001"}),
        content_type="application/json",
    )
    assert res.status_code == 422
    assert res.json()["message_key"] == "library.error.duplicate_accession"


def test_withdrawn_borrower_history_retained(client, baseline):
    """Withdrawing a copy keeps closed loan history for the borrower."""
    issued = _issue(
        client, baseline["copy_id"], baseline["student_s1"], "2026-10-01", "wd-issue"
    )
    loan = issued.json()
    client.post(
        f"/api/v1/library/loans/{loan['id']}/return",
        data=json.dumps(
            {
                "returned_at": "2026-09-21T05:00:00Z",
                "condition": "ok",
                "expected_version": loan["version"],
            }
        ),
        content_type="application/json",
    )
    from modules.library.models import Copy

    copy = Copy.objects.get(id=baseline["copy_id"])
    adj = client.post(
        f"/api/v1/library/copies/{baseline['copy_id']}/adjust",
        data=json.dumps(
            {
                "new_state": "withdrawn",
                "reason": "damaged beyond repair",
                "expected_version": copy.version,
            }
        ),
        content_type="application/json",
    )
    assert adj.status_code == 200, adj.content
    history = client.get(f"/api/v1/library/borrowers/{baseline['student_s1']}/loans")
    assert history.status_code == 200
    assert len(history.json()["items"]) == 1


def test_renewal_and_version_conflict(client, baseline):
    """Renew advances due_date; stale expected_version is 409."""
    issued = _issue(
        client, baseline["copy_id"], baseline["student_s1"], "2026-10-01", "rn-issue"
    )
    loan = issued.json()
    stale = client.post(
        f"/api/v1/library/loans/{loan['id']}/renew",
        data=json.dumps({"new_due_date": "2026-10-15", "expected_version": 99}),
        content_type="application/json",
    )
    assert stale.status_code == 409
    ok = client.post(
        f"/api/v1/library/loans/{loan['id']}/renew",
        data=json.dumps({"new_due_date": "2026-10-15", "expected_version": loan["version"]}),
        content_type="application/json",
    )
    assert ok.status_code == 200
    assert ok.json()["due_date"] == "2026-10-15"
    from modules.library.models import Renewal

    assert Renewal.objects.filter(loan_id=loan["id"]).count() == 1


def test_cross_school_title_is_404(client, baseline):
    """Other-school title id is 404."""
    from modules.library.models import Title

    foreign = Title.objects.create(
        school_id=fixtures.SCHOOL_B,
        name="Foreign",
        author="X",
        language="en",
        version=1,
    )
    res = client.get(f"/api/v1/library/titles/{foreign.id}/availability")
    assert res.status_code == 404


def test_audit_and_events_on_issue(client, baseline):
    """Issue writes audit + library.loan_issued outbox event."""
    from shared.harness.models import HarnessAuditRecord

    issued = _issue(
        client, baseline["copy_id"], baseline["student_s1"], "2026-10-01", "evt-issue"
    )
    assert issued.status_code == 201
    assert HarnessAuditRecord.objects.filter(action="library.loan_issued").exists()
    assert HarnessOutboxEvent.objects.filter(event_type="library.loan_issued").count() == 1


def test_unicode_title_search(client, baseline):
    """Search finds Malayalam title by substring."""
    res = client.get("/api/v1/library/titles?q=കേരള")
    assert res.status_code == 200
    assert len(res.json()["items"]) == 1
    assert res.json()["items"][0]["id"] == baseline["title_id"]
