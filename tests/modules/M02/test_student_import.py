"""POST /students/import: admissions spreadsheet preview and apply."""

from __future__ import annotations

from datetime import date

import pytest

from modules.registry.services.student_import_parse import (
    clean_phone,
    parse_class,
    parse_date,
    parse_file,
)

pytestmark = pytest.mark.django_db

GOOD = (
    "Adm No,Student Name,Class,DOB,Parent Name,Mobile\n"
    "A101,Anjali Nair,5A,31/05/2015,Suresh Nair,98470 12345\n"
    "A102,Arjun Nair,Std 5 - A,2015-01-02,Suresh Nair,9847012345\n"
    "A103,Rohan Das,V-A,,,\n"
)


def test_parse_class_accepts_the_ways_schools_write_it():
    assert parse_class("6A") == (6, "A")
    assert parse_class("Std 6 - B") == (6, "B")
    assert parse_class("VI-a") == (6, "A")
    assert parse_class("10th C") == (10, "C")
    assert parse_class("Class 13 A") == (None, "")
    assert parse_class("Nursery") == (None, "")


def test_parse_date_is_day_first_for_slashes():
    assert parse_date("31/05/2015") == date(2015, 5, 31)
    assert parse_date("2015-05-31") == date(2015, 5, 31)
    assert parse_date("31/13/2015") is None
    assert parse_date("May 31") is None


def test_clean_phone():
    assert clean_phone("98470 12345") == "9847012345"
    assert clean_phone("+91 98470-12345") == "+919847012345"
    assert clean_phone("12345") is None


def test_file_without_required_columns_says_which():
    parsed = parse_file("Name,DOB\nAnjali,2015-01-01\n")
    missing = {problem.column for problem in parsed.problems}
    assert missing == {"admission_no", "class"}


def test_repeated_admission_number_in_file_is_reported():
    parsed = parse_file("Adm No,Name,Class\nA1,One,5A\nA1,Two,5A\n")
    assert [row.name for row in parsed.rows] == ["One"]
    assert parsed.problems[0].row == 3
    assert parsed.problems[0].message_key == "registry.import.repeated"


def test_preview_writes_nothing_and_counts_per_class(api, configured):
    response = api.post("/students/import", {"csv": GOOD})
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["applied"] is False
    assert body["ready"] == 3
    assert body["problems"] == []
    assert sum(body["per_class"].values()) == 3
    assert api.get("/students").json()["items"] == []


def test_apply_admits_places_and_links_siblings_to_one_parent(api, configured):
    body = api.post("/students/import", {"csv": GOOD, "apply": True}).json()
    assert body["applied"] is True
    assert body["parents_created"] == 1  # the two Nairs share one phone
    students = api.get("/students").json()["items"]
    assert sorted(row["admission_no"] for row in students) == ["A101", "A102", "A103"]
    roster = api.get(
        f"/sections/{configured['section']['id']}/roster?date={configured['year']['end']}"
    )
    assert roster.status_code == 200, roster.content
    assert len(roster.json()["students"]) == 3
    guardians = api.get("/guardians").json()["items"]
    assert [row["display_name"] for row in guardians] == ["Suresh Nair"]


def test_any_problem_means_nobody_is_admitted(api, configured):
    text = GOOD + "A104,Meera,9Z,,,\n"
    body = api.post("/students/import", {"csv": text, "apply": True}).json()
    assert body["applied"] is False
    assert body["problems"][0]["row"] == 5
    assert body["problems"][0]["message_key"] == "registry.import.unknown_class"
    assert api.get("/students").json()["items"] == []


def test_admission_number_already_on_roll_is_a_problem(api, configured):
    api.post("/students/import", {"csv": GOOD, "apply": True})
    again = api.post("/students/import", {"csv": GOOD}).json()
    keys = {problem["message_key"] for problem in again["problems"]}
    assert keys == {"registry.import.already_admitted"}
    assert again["ready"] == 0
