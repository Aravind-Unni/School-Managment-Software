"""The admission-register details a school keeps about a pupil.

Pure: no database. ``DETAIL_FIELDS`` is the whole list (address, blood group,
parents' names, previous school ...), each with its kind and, for choices,
the allowed values. ``clean_details`` checks a submitted dict against it and
returns the cleaned dict or the problems, field by field. Empty values are
dropped rather than stored, so a record only holds what the office entered.

Does not handle: identity numbers such as Aadhaar (deliberately not
collected), or who may see these details (the view requires students.read,
which families do not hold).
"""

from __future__ import annotations

import re
from datetime import date

BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
GENDERS = ("female", "male", "other")
CATEGORIES = ("general", "obc", "sc", "st", "oec", "other")

#: field -> (kind, allowed values or max length)
DETAIL_FIELDS: dict[str, tuple[str, object]] = {
    "gender": ("choice", GENDERS),
    "blood_group": ("choice", BLOOD_GROUPS),
    "mother_tongue": ("text", 64),
    "religion": ("text", 64),
    "category": ("choice", CATEGORIES),
    "nationality": ("text", 64),
    "identification_marks": ("text", 200),
    "address_line": ("text", 300),
    "place": ("text", 100),
    "district": ("text", 100),
    "state": ("text", 100),
    "pin_code": ("pin", 6),
    "father_name": ("text", 200),
    "father_occupation": ("text", 100),
    "mother_name": ("text", 200),
    "mother_occupation": ("text", 100),
    "admission_date": ("date", None),
    "previous_school": ("text", 200),
    "tc_number": ("text", 64),
    "medical_notes": ("text", 500),
    "emergency_contact_name": ("text", 200),
    "emergency_contact_phone": ("phone", None),
}


def _problem(value: object, kind: str, rule: object) -> str | None:
    """Return a message key when ``value`` breaks its field's rule, else None."""
    text = str(value).strip()
    if kind == "choice" and text not in rule:  # type: ignore[operator]
        return "registry.details.bad_choice"
    if kind == "text" and len(text) > int(rule):  # type: ignore[arg-type]
        return "registry.details.too_long"
    if kind == "pin" and not re.fullmatch(r"\d{6}", text):
        return "registry.details.bad_pin"
    if kind == "phone" and not re.fullmatch(r"\+?\d{10,15}", re.sub(r"[\s-]", "", text)):
        return "registry.details.bad_phone"
    if kind == "date":
        try:
            date.fromisoformat(text)
        except ValueError:
            return "registry.details.bad_date"
    return None


def clean_details(submitted: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Return (cleaned details, problems by field). Unknown fields are problems."""
    cleaned: dict[str, str] = {}
    problems: dict[str, str] = {}
    for key, value in submitted.items():
        if key not in DETAIL_FIELDS:
            problems[key] = "registry.details.unknown_field"
            continue
        if value is None or str(value).strip() == "":
            continue
        kind, rule = DETAIL_FIELDS[key]
        problem = _problem(value, kind, rule)
        if problem is not None:
            problems[key] = problem
            continue
        text = str(value).strip()
        cleaned[key] = re.sub(r"[\s-]", "", text) if kind == "phone" else text
    return cleaned, problems
