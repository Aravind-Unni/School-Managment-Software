"""Queued jobs are dispatched after commit, run once, and record their outcome."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db


def _adapter(clock):
    from modules.platform.services.adapter import PlatformAdapter

    return PlatformAdapter(worker_available=True, clock=clock)


def test_enqueue_stores_the_handler_and_payload_and_tolerates_missing_identity(
    settings, clock, django_capture_on_commit_callbacks
):
    from modules.platform.models import Job

    with django_capture_on_commit_callbacks() as callbacks:
        job_id = _adapter(clock).enqueue(
            "modules.platform.tasks.dispatch_outbox", payload={"file_id": "x"}
        )
    job = Job.objects.get(id=job_id)
    assert job.task_path == "modules.platform.tasks.dispatch_outbox"
    assert job.payload == {"file_id": "x"}
    assert str(job.school_id) == str(settings.SCHOOL_ID)
    # One dispatch registered, to run only after the transaction commits.
    assert len(callbacks) == 1


def test_a_bookkeeping_kind_is_recorded_but_not_dispatched(
    clock, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks() as callbacks:
        _adapter(clock).enqueue("assessment.report_snapshot", payload={})
    assert callbacks == []


def test_running_a_job_marks_it_succeeded_and_a_second_delivery_is_a_no_op(clock):
    from modules.platform.models import Job, JobState
    from modules.platform.services.job_runner import run_job

    job_id = _adapter(clock).enqueue("modules.platform.tasks.dispatch_outbox", payload={})
    assert run_job(job_id, now=clock.now) == JobState.SUCCEEDED
    assert Job.objects.get(id=job_id).state == JobState.SUCCEEDED
    assert run_job(job_id, now=clock.now) == JobState.SUCCEEDED


def test_a_failing_handler_marks_the_job_failed_with_the_error_class(clock, monkeypatch):
    from modules.platform import tasks
    from modules.platform.models import Job, JobState
    from modules.platform.services.job_runner import run_job

    def boom():
        raise RuntimeError("provider down")

    monkeypatch.setattr(tasks, "dispatch_outbox", boom)
    job_id = _adapter(clock).enqueue("modules.platform.tasks.dispatch_outbox", payload={})
    assert run_job(job_id, now=clock.now) == JobState.FAILED
    assert Job.objects.get(id=job_id).error_code == "RuntimeError"


def test_payload_keys_are_matched_to_handler_parameters():
    from modules.platform.services.job_runner import call_with_payload

    def takes_payload(payload):
        return payload["a"]

    def takes_names(file_id, profile="default"):
        return (file_id, profile)

    assert call_with_payload(takes_payload, {"a": 1}) == 1
    assert call_with_payload(takes_names, {"file_id": "f", "unused": 2}) == ("f", "default")
