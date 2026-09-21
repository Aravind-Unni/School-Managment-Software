"""Fee setup: GET /fee-heads and POST /fees/charge-classes."""

from __future__ import annotations

import json

import pytest

from shared import fixtures

pytestmark = [pytest.mark.module]


def _charge(client, **overrides):
    body = {
        "fee_name": "Annual day fee",
        "amount_paise": 50000,
        "due_date": "2026-07-15",
        "section_ids": [str(fixtures.CLASS_C1)],
    }
    body.update(overrides)
    return client.post(
        "/api/v1/fees/charge-classes", data=json.dumps(body), content_type="application/json"
    )


def test_charge_classes_charges_every_pupil_in_the_class(client, baseline):
    """C1 holds S1 and S2: both are charged and the new fee type is created."""
    res = _charge(client)
    assert res.status_code == 200, res.content
    body = res.json()
    assert body["charged"] == 2
    assert body["already_charged"] == 0
    assert body["label_key"] == "Annual day fee"
    from modules.fees.models import Charge

    charged = set(
        Charge.objects.filter(fee_head_id=body["fee_head_id"]).values_list(
            "student_id", flat=True
        )
    )
    assert charged == {fixtures.STUDENT_S1, fixtures.STUDENT_S2}


def test_repeating_the_same_charge_skips_pupils_already_charged(client, baseline):
    """Running it again charges nobody twice."""
    first = _charge(client).json()
    again = _charge(client, fee_head_id=first["fee_head_id"], fee_name="")
    assert again.status_code == 200, again.content
    assert again.json()["charged"] == 0
    assert again.json()["already_charged"] == 2


def test_new_fee_needs_a_name(client, baseline):
    """No fee type and no name is a validation failure."""
    res = _charge(client, fee_name="")
    assert res.status_code == 422, res.content


def test_fee_heads_list_totals(client, baseline):
    """The charged fee type shows 2 pupils, ₹1,000 charged, all still owed."""
    head_id = _charge(client).json()["fee_head_id"]
    res = client.get("/api/v1/fee-heads")
    assert res.status_code == 200, res.content
    row = next(item for item in res.json()["items"] if item["id"] == head_id)
    assert row["pupils"] == 2
    assert row["charged_paise"] == 100000
    assert row["outstanding_paise"] == 100000
    assert row["first_due"] == "2026-07-15"
