"""Demo people: staff with logins, students in four classes, parents, links.

Returns a ``DemoCast`` the later stages use. Every write goes through the API
as the owner, so admission, linking and enrolment follow the product's rules
(including automatic subject enrolment).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date

from .api_actor import ApiActor
from .names import parent_name, student_name

#: The one password every demo account gets. Demo only; printed at the end.
DEMO_PASSWORD = "DemoPass@2026"

#: Standards (with section "A") that get demo students.
DEMO_STANDARDS = (6, 7, 8, 9)
STUDENTS_PER_SECTION = 25

#: (display name, login, role key, subject code taught or None)
DEMO_STAFF = (
    ("Sreekumar Menon", "principal", "administrator", None),
    ("Anita Nair", "anita.nair", "teacher", "MATH"),
    ("Joseph Mathew", "joseph.mathew", "teacher", "ENG"),
    ("Lakshmi Pillai", "lakshmi.pillai", "teacher", "SCI"),
    ("Rahim Ali", "rahim.ali", "teacher", "SST"),
    ("Deepa Warrier", "deepa.warrier", "teacher", "MAL"),
    ("Bindu George", "accounts", "accountant", None),
    ("Rekha Das", "library", "librarian", None),
)


@dataclass
class DemoCast:
    """Ids of everything created, for the later stages."""

    school_id: str = ""
    year_id: str = ""
    term_id: str = ""
    year_start: date | None = None
    sections: dict[int, str] = field(default_factory=dict)  # standard -> section id
    subjects: dict[str, str] = field(default_factory=dict)  # code -> subject id
    staff: dict[str, dict] = field(default_factory=dict)  # login -> {id, subject, name}
    students: list[dict] = field(default_factory=list)  # {id, name, section_id, standard, ...}
    guardians: list[dict] = field(default_factory=list)
    logins: list[tuple[str, str, str]] = field(default_factory=list)  # (role, login, name)


def _load_structure(school_id, cast: DemoCast) -> None:
    """Read the installed year, term, sections and subjects (ORM reads only)."""
    from modules.registry.models import AcademicYear, Section, Subject, Term

    year = AcademicYear.objects.get(school_id=school_id, state="active")
    cast.school_id = str(school_id)
    cast.year_id = str(year.id)
    cast.year_start = year.start
    term = Term.objects.filter(school_id=school_id, year=year).order_by("start").first()
    cast.term_id = str(term.id)
    for number in DEMO_STANDARDS:
        section = Section.objects.get(
            school_id=school_id, year=year, standard__number=number, name="A"
        )
        cast.sections[number] = str(section.id)
    for subject in Subject.objects.filter(school_id=school_id):
        cast.subjects[subject.code] = str(subject.id)


def _create_login(owner: ApiActor, cast: DemoCast, *, login, name, person_id, role_id, role):
    """Create an account with the demo password, linked to a Registry person."""
    owner.post(
        "/accounts",
        {
            "login_name": login,
            "display_name": name,
            "person_id": person_id,
            "role_ids": [role_id],
            "password": DEMO_PASSWORD,
        },
    )
    cast.logins.append((role, login, name))


def seed_people(owner: ApiActor, school_id, *, rng: random.Random) -> DemoCast:
    """Create staff, parents, students, enrolments and teaching assignments."""
    from config.school_install_access import role_id_for

    cast = DemoCast()
    _load_structure(school_id, cast)
    start = max(cast.year_start, date(2026, 6, 1))

    for name, login, role, subject in DEMO_STAFF:
        staff = owner.post("/staff", {"display_name": name, "external_ids": []})
        _create_login(
            owner,
            cast,
            login=login,
            name=name,
            person_id=staff["id"],
            role_id=str(role_id_for(school_id, role)),
            role=role,
        )
        cast.staff[login] = {"id": staff["id"], "subject": subject, "name": name}

    for teacher in cast.staff.values():
        if teacher["subject"] is None:
            continue
        for section_id in cast.sections.values():
            owner.post(
                "/teaching-assignments",
                {
                    "staff_id": teacher["id"],
                    "section_id": section_id,
                    "subject_id": cast.subjects[teacher["subject"]],
                    "from_date": start.isoformat(),
                    "to_date": None,
                },
            )

    guardian_role = str(role_id_for(school_id, "guardian"))
    student_role = str(role_id_for(school_id, "student"))
    for standard, section_id in cast.sections.items():
        for number in range(1, STUDENTS_PER_SECTION + 1):
            admission_no = f"A{standard:02d}{number:02d}"
            reuse = cast.guardians and rng.random() < 0.12
            if reuse:
                guardian = rng.choice(cast.guardians)
                name = f"{student_name(rng).split()[0]} {guardian['surname']}"
            else:
                name = student_name(rng)
                surname = name.split()[-1]
                display = parent_name(rng, surname)
                created = owner.post(
                    "/guardians",
                    {
                        "display_name": display,
                        "email": None,
                        "phone": f"98{rng.randint(10000000, 99999999)}",
                        "external_ids": [],
                    },
                )
                guardian = {"id": created["id"], "name": display, "surname": surname}
                cast.guardians.append(guardian)
                _create_login(
                    owner,
                    cast,
                    login=f"parent.{admission_no.lower()}",
                    name=display,
                    person_id=guardian["id"],
                    role_id=guardian_role,
                    role="guardian",
                )
            birth_year = 2026 - (standard + 5)
            student = owner.post(
                "/students",
                {
                    "admission_no": admission_no,
                    "display_name": name,
                    "profile": {
                        "date_of_birth": date(
                            birth_year, rng.randint(1, 12), rng.randint(1, 28)
                        ).isoformat(),
                        "preferred_language": "ml" if rng.random() < 0.3 else "en",
                    },
                    "guardian_links": [
                        {
                            "guardian_id": guardian["id"],
                            "visibility": "academic",
                            "from_date": start.isoformat(),
                            "to_date": None,
                        }
                    ],
                    "external_ids": [],
                    "duplicate_review": None,
                },
            )
            owner.post(
                "/enrolments",
                {
                    "student_id": student["id"],
                    "year_id": cast.year_id,
                    "section_id": section_id,
                    "from_date": start.isoformat(),
                    "to_date": None,
                },
            )
            _create_login(
                owner,
                cast,
                login=admission_no.lower(),
                name=name,
                person_id=student["id"],
                role_id=student_role,
                role="student",
            )
            cast.students.append(
                {
                    "id": student["id"],
                    "name": name,
                    "admission_no": admission_no,
                    "section_id": section_id,
                    "standard": standard,
                    "guardian_id": guardian["id"],
                }
            )
    return cast
