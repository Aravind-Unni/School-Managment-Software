"""GET/PUT /students/{id}/details and detail columns in the import."""

from __future__ import annotations

import pytest

from modules.registry.services.student_details import clean_details
from modules.registry.services.student_import_parse import normalise_blood_group, parse_file

pytestmark = pytest.mark.django_db


def _admit(api):
    return api.post(
        "/students",
        {
            "admission_no": "D1",
            "display_name": "Diya Menon",
            "profile": {"date_of_birth": None, "preferred_language": "en"},
            "guardian_links": [],
            "external_ids": [],
            "duplicate_review": None,
        },
    ).json()


def test_clean_details_checks_each_kind():
    cleaned, problems = clean_details(
        {
            "blood_group": "B+",
            "pin_code": "68201",
            "emergency_contact_phone": "98470 12345",
            "gender": "",
            "shoe_size": "4",
        }
    )
    assert cleaned == {"blood_group": "B+", "emergency_contact_phone": "9847012345"}
    assert problems == {
        "pin_code": "registry.details.bad_pin",
        "shoe_size": "registry.details.unknown_field",
    }


def test_blood_group_spellings():
    assert normalise_blood_group("B +ve") == "B+"
    assert normalise_blood_group("o negative") == "O-"
    assert normalise_blood_group("AB+") == "AB+"


def test_details_round_trip(api, configured):
    student = _admit(api)
    first = api.get(f"/students/{student['id']}/details")
    assert first.status_code == 200, first.content
    body = first.json()
    assert body["details"] == {}
    assert "O+" in body["choices"]["blood_group"]
    saved = api.put(
        f"/students/{student['id']}/details",
        {
            "details": {"blood_group": "O+", "address_line": "TC 12/345, MG Road"},
            "expected_version": body["version"],
        },
    )
    assert saved.status_code == 200, saved.content
    assert api.get(f"/students/{student['id']}/details").json()["details"] == {
        "blood_group": "O+",
        "address_line": "TC 12/345, MG Road",
    }


def test_bad_detail_is_refused_per_field(api, configured):
    student = _admit(api)
    version = api.get(f"/students/{student['id']}/details").json()["version"]
    response = api.put(
        f"/students/{student['id']}/details",
        {"details": {"blood_group": "Z"}, "expected_version": version},
    )
    assert response.status_code == 422, response.content
    assert "details.blood_group" in response.content.decode()


def test_import_reads_detail_columns():
    parsed = parse_file(
        "Adm No,Name,Class,Gender,Blood Group,Address,PIN,Father's Name\n"
        "A1,Diya,5A,F,B +ve,MG Road,682011,Ravi Menon\n"
        "A2,Arun,5A,M,X,,68201,\n"
    )
    assert parsed.rows[0].details == {
        "gender": "female",
        "blood_group": "B+",
        "address_line": "MG Road",
        "pin_code": "682011",
        "father_name": "Ravi Menon",
    }
    assert {problem.column for problem in parsed.problems} == {"blood_group", "pin_code"}
