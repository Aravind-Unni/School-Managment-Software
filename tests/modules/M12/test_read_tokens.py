"""Signed file-read links: bound to one file and version, and they expire."""

from __future__ import annotations

import time
import uuid

from modules.files.services import read_tokens


def test_a_token_reads_only_its_own_file_and_version():
    file_id = uuid.uuid4()
    token = read_tokens.mint(file_id, 3)
    assert read_tokens.verify(token, file_id=file_id, max_age_seconds=60) == 3
    assert read_tokens.verify(token, file_id=uuid.uuid4(), max_age_seconds=60) is None


def test_a_tampered_or_empty_token_is_refused():
    file_id = uuid.uuid4()
    token = read_tokens.mint(file_id, 1)
    assert read_tokens.verify(token[:-2] + "xx", file_id=file_id, max_age_seconds=60) is None
    assert read_tokens.verify("", file_id=file_id, max_age_seconds=60) is None


def test_an_expired_token_is_refused():
    file_id = uuid.uuid4()
    token = read_tokens.mint(file_id, 1)
    time.sleep(1.1)
    assert read_tokens.verify(token, file_id=file_id, max_age_seconds=1) is None
