"""Fixtures for M12's suite. MODULE_ID=M12; fake Access/Platform."""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime

import pytest
from django.test import Client

from contracts.identity import AuthLevel
from shared import fixtures
from shared.http.context import DevPersona

pytestmark = pytest.mark.module

FROZEN_INSTANT = datetime(2026, 9, 21, 4, 30, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _school_id(settings):
    """Pin deployment school to School A."""
    settings.SCHOOL_ID = str(fixtures.SCHOOL_A)
    return fixtures.SCHOOL_A


@pytest.fixture(autouse=True)
def _persona(settings):
    """Default persona is teacher uploader/reviewer with recent 2FA."""
    settings.DEV_PERSONA_MODE = "fixed"
    settings.DEV_PERSONA = DevPersona(
        actor_id=fixtures.TEACHER_T1,
        school_id=fixtures.SCHOOL_A,
        auth_level=AuthLevel.TWO_FACTOR,
    )
    return settings


@pytest.fixture
def clock(settings):
    """Freeze the shared SCHOOL_CLOCK."""
    clk = settings.SCHOOL_CLOCK
    clk.set(FROZEN_INSTANT)
    return clk


@pytest.fixture
def as_persona(settings):
    """Switch the server-side persona mid-test."""

    def switch(actor_id, *, school_id=fixtures.SCHOOL_A, auth_level=AuthLevel.TWO_FACTOR):
        settings.DEV_PERSONA = DevPersona(
            actor_id=actor_id, school_id=school_id, auth_level=auth_level
        )
        return settings.DEV_PERSONA

    return switch


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def baseline(db, clock):
    """Seed policy, pages, candidate, accepted and hold files."""
    from modules.files.seeds import seed_baseline

    return seed_baseline()


def make_png_bytes(*, width: int = 80, height: int = 100) -> bytes:
    """Small valid PNG for upload tests."""
    from PIL import Image

    image = Image.new("RGB", (width, height), color=(200, 200, 200))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def make_animated_webp() -> bytes:
    """Two-frame WebP that must be rejected as animated."""
    from PIL import Image

    frames = [
        Image.new("RGB", (32, 32), color=(255, 0, 0)),
        Image.new("RGB", (32, 32), color=(0, 0, 255)),
    ]
    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
    )
    return buf.getvalue()


def sha256_hex(body: bytes) -> str:
    """Hex digest helper."""
    return hashlib.sha256(body).hexdigest()


def upload_and_process(client, body: bytes, *, mime: str = "image/png") -> dict:
    """HTTP begin → PUT → complete; returns complete JSON (processing then ready)."""
    begin = client.post(
        "/api/v1/uploads",
        data={
            "purpose": "answer_sheet",
            "client_name": "page.png",
            "declared_bytes": len(body),
            "mime": mime,
        },
        content_type="application/json",
    )
    assert begin.status_code == 201, begin.content
    session = begin.json()
    put = client.put(
        session["upload_url"],
        data=body,
        content_type=mime,
    )
    assert put.status_code == 204, put.content
    complete = client.post(
        f"/api/v1/uploads/{session['id']}/complete",
        data={"source_sha256": sha256_hex(body)},
        content_type="application/json",
    )
    assert complete.status_code == 201, complete.content
    return complete.json()


@pytest.fixture(autouse=True)
def _inline_platform(db):
    """Run enqueued work inline, which is what these assertions describe.

    The standalone harness sets WORKER_AVAILABLE for modules that declare a
    worker, but the pytest process shares no database with that worker, so a
    queued job could never complete here.
    """
    from django.urls import get_resolver

    from shared.ports import runtime

    get_resolver()
    platform = runtime.get_registry().resolve("platform")
    previous = getattr(platform, "_worker_available", None)
    if previous is not None:
        platform._worker_available = False
    yield
    if previous is not None:
        platform._worker_available = previous
