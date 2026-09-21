"""Install or update one school's configuration from a TOML file.

Reads ``config/school_defaults.toml`` and deep-merges the deployment's own file
(``SCHOOL_CONFIG_FILE``, e.g. infra/prod/school.toml) over it, then writes the
configuration rows every module needs to function: school identity, academic
year and terms, standards, sections, subjects and offerings, roles and their
grants, module policies, and a first draft timetable with the bell schedule.

Idempotent by natural keys: re-running after an edit updates rows in place.
Never deletes people, marks, payments, attendance or anything a person entered.
Does not handle: removing a section or subject that was dropped from the file
(archive it in the product instead), or multi-school deployments.
"""

from __future__ import annotations

import copy
import tomllib
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from django.db import transaction

DEFAULTS_PATH = Path(__file__).with_name("school_defaults.toml")

#: Installed grants are open-ended and in force from a fixed past date, so a
#: change of academic year in the file never switches staff off.
GRANTS_VALID_FROM = date(2000, 1, 1)


@dataclass
class InstallReport:
    """Counts of what an install created or updated, for the operator."""

    created: dict[str, int] = field(default_factory=dict)
    updated: dict[str, int] = field(default_factory=dict)

    def note(self, kind: str, created: bool) -> None:
        """Count one row as created or updated."""
        bucket = self.created if created else self.updated
        bucket[kind] = bucket.get(kind, 0) + 1


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return ``base`` with ``override`` merged in; tables merge, lists replace.

    Lists replace rather than append, so a school that lists its own subjects
    gets exactly those subjects. Does not mutate either argument.
    """
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_school_config(path: str | Path | None) -> dict[str, Any]:
    """Return the defaults merged with the file at ``path`` (if given and present)."""
    with DEFAULTS_PATH.open("rb") as handle:
        config = tomllib.load(handle)
    if path:
        override_path = Path(path)
        if not override_path.exists():
            raise FileNotFoundError(f"school config file not found: {override_path}")
        with override_path.open("rb") as handle:
            config = deep_merge(config, tomllib.load(handle))
    validate_school_config(config)
    return config


def validate_school_config(config: dict[str, Any]) -> None:
    """Refuse a configuration that would install inconsistent rows.

    Raises ValueError naming every problem at once, so an operator fixes the
    file in one pass. Does not check anything against the database.
    """
    problems: list[str] = []
    year = config["academic_year"]
    if year["end"] < year["start"]:
        problems.append("academic_year.end is before academic_year.start")
    for term in year.get("terms", []):
        if term["end"] < term["start"]:
            problems.append(f"term {term['name']!r} ends before it starts")
        if term["start"] < year["start"] or term["end"] > year["end"]:
            problems.append(f"term {term['name']!r} is outside the academic year")
    standards = config["structure"]["standards"]
    if any(not 1 <= number <= 12 for number in standards):
        problems.append("structure.standards must be between 1 and 12")
    codes = [subject["code"] for subject in config.get("subjects", [])]
    if len(codes) != len(set(codes)):
        problems.append("subject codes must be unique")
    for subject in config.get("subjects", []):
        unknown = sorted(set(subject["standards"]) - set(standards))
        if unknown:
            problems.append(f"subject {subject['code']} lists unknown standards {unknown}")
    if config["school"]["default_language"] not in ("en", "ml"):
        problems.append("school.default_language must be 'en' or 'ml'")
    bands = config.get("grading", {}).get("bands", [])
    minimums = [band["min_percent"] for band in bands]
    if bands and (minimums != sorted(minimums, reverse=True) or minimums[-1] != 0):
        problems.append("grading.bands must run highest first and end at min_percent = 0")
    for period in config["timetable"]["periods"]:
        if _parse_time(period["end"]) <= _parse_time(period["start"]):
            problems.append(f"period {period['code']} ends before it starts")
    if problems:
        raise ValueError("invalid school config:\n  - " + "\n  - ".join(problems))


def _parse_time(text: str) -> time:
    """Parse "HH:MM" into a time."""
    hours, minutes = text.split(":")
    return time(int(hours), int(minutes))


def _stable_id(school_id: uuid.UUID, label: str) -> uuid.UUID:
    """Return a deterministic id for an installed row, so re-runs match it."""
    return uuid.uuid5(school_id, f"install.{label}")


def install_school(
    config: dict[str, Any], *, school_id: uuid.UUID, now: datetime
) -> InstallReport:
    """Write every configuration row described by ``config``. One transaction."""
    from config.school_install_access import _install_policies, _install_roles

    report = InstallReport()
    with transaction.atomic():
        _install_identity(config, school_id, now, report)
        year = _install_year(config, school_id, now, report)
        sections = _install_structure(config, school_id, year, now, report)
        _install_subjects(config, school_id, year, sections, now, report)
        _install_timetable_draft(config, school_id, year, now, report)
        _install_policies(config, school_id, report)
        _install_roles(config, school_id, now, report)
    return report


# --- registry ---------------------------------------------------------------


def _install_identity(config, school_id, now, report) -> None:
    """Create or update the one SchoolConfig row, including shared settings."""
    from modules.registry.models import SchoolConfig

    school = config["school"]
    settings_blob = {
        "timezone": school["timezone"],
        "currency": school["currency"],
        "working_days": list(config["timetable"]["working_days"]),
        "grading_bands": list(config.get("grading", {}).get("bands", [])),
        "low_attendance_percent": config["attendance"]["low_attendance_percent"],
    }
    row = SchoolConfig.objects.filter(school_id=school_id).first()
    if row is None:
        SchoolConfig.objects.create(
            id=_stable_id(school_id, "school_config"),
            school_id=school_id,
            display_name=school["name"],
            board=school["board"],
            default_language=school["default_language"],
            settings=settings_blob,
            version=1,
            created_at=now,
            updated_at=now,
        )
        report.note("school_config", True)
        return
    changed = (
        row.display_name != school["name"]
        or row.board != school["board"]
        or row.default_language != school["default_language"]
        or row.settings != settings_blob
    )
    if changed:
        row.display_name = school["name"]
        row.board = school["board"]
        row.default_language = school["default_language"]
        row.settings = settings_blob
        row.version += 1
        row.updated_at = now
        row.save()
        report.note("school_config", False)


def _install_year(config, school_id, now, report):
    """Create or update the configured academic year and its terms."""
    from modules.registry.models import AcademicYear, Term

    spec = config["academic_year"]
    year = AcademicYear.objects.filter(school_id=school_id, name=spec["name"]).first()
    created = year is None
    if created:
        year = AcademicYear(
            school_id=school_id, name=spec["name"], version=1, created_at=now, state="draft"
        )
    before = (year.start, year.end, year.state)
    year.start = spec["start"]
    year.end = spec["end"]
    if spec.get("activate", True) and year.state == "draft":
        # One active year at a time: an older active year is closed by the
        # school's year-end process, not silently here.
        if (
            not AcademicYear.objects.filter(school_id=school_id, state="active")
            .exclude(id=year.id)
            .exists()
        ):
            year.state = "active"
    if created or before != (year.start, year.end, year.state):
        year.updated_at = now
        if not created:
            year.version += 1
        year.save()
        report.note("academic_year", created)

    for term_spec in spec.get("terms", []):
        term = Term.objects.filter(
            school_id=school_id, year=year, name=term_spec["name"]
        ).first()
        term_created = term is None
        if term_created:
            term = Term(
                school_id=school_id,
                year=year,
                name=term_spec["name"],
                version=1,
                created_at=now,
            )
        elif term.start == term_spec["start"] and term.end == term_spec["end"]:
            continue
        else:
            term.version += 1
        term.start = term_spec["start"]
        term.end = term_spec["end"]
        term.updated_at = now
        term.save()
        report.note("term", term_created)
    return year


def _install_structure(config, school_id, year, now, report) -> dict[int, list]:
    """Create standards and this year's sections. Returns {standard: [sections]}."""
    from modules.registry.models import Section, Standard

    structure = config["structure"]
    overrides = {int(key): value for key, value in structure.get("sections", {}).items()}
    sections_by_standard: dict[int, list] = {}
    for number in structure["standards"]:
        standard, created = Standard.objects.get_or_create(
            school_id=school_id,
            number=number,
            defaults={"archived": False, "version": 1, "created_at": now, "updated_at": now},
        )
        if created:
            report.note("standard", True)
        sections_by_standard[number] = []
        for name in overrides.get(number, structure["default_sections"]):
            section, created = Section.objects.get_or_create(
                school_id=school_id,
                year=year,
                standard=standard,
                name=name,
                defaults={
                    "archived": False,
                    "version": 1,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            if created:
                report.note("section", True)
            sections_by_standard[number].append(section)
    return sections_by_standard


def _install_subjects(config, school_id, year, sections, now, report) -> None:
    """Create subjects and offer each to every section of its standards."""
    from modules.registry.models import Subject, SubjectOffering
    from modules.registry.services.subject_defaults import enrol_section_pupils_in_offering

    for spec in config.get("subjects", []):
        subject = Subject.objects.filter(school_id=school_id, code=spec["code"]).first()
        if subject is None:
            subject = Subject.objects.create(
                school_id=school_id,
                code=spec["code"],
                display_name=spec["name"],
                archived=False,
                version=1,
                created_at=now,
                updated_at=now,
            )
            report.note("subject", True)
        elif subject.display_name != spec["name"]:
            subject.display_name = spec["name"]
            subject.version += 1
            subject.updated_at = now
            subject.save()
            report.note("subject", False)
        for number in spec["standards"]:
            for section in sections.get(number, []):
                offering, created = SubjectOffering.objects.get_or_create(
                    school_id=school_id,
                    year=year,
                    section=section,
                    subject=subject,
                    defaults={
                        "optional_group": None,
                        "archived": False,
                        "version": 1,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                if created:
                    report.note("subject_offering", True)
                    enrol_section_pupils_in_offering(
                        offering, on=max(year.start, min(now.date(), year.end)), now=now
                    )


# --- timetable ----------------------------------------------------------------


def _install_timetable_draft(config, school_id, year, now, report) -> None:
    """Create a first DRAFT timetable carrying the bell schedule, once per year.

    Only when the year has no timetable at all: an existing draft or published
    timetable is the school's own work and is never touched.
    """
    from modules.timetable.models import PeriodTemplate, TimetableVersion

    if TimetableVersion.objects.filter(school_id=school_id, year_id=year.id).exists():
        return
    draft = TimetableVersion.objects.create(
        school_id=school_id,
        year_id=year.id,
        effective_from=max(year.start, min(now.date(), year.end)),
        effective_to=None,
        state="draft",
        version=1,
        created_at=now,
        updated_at=now,
    )
    report.note("timetable_draft", True)
    for weekday in config["timetable"]["working_days"]:
        for period in config["timetable"]["periods"]:
            PeriodTemplate.objects.create(
                school_id=school_id,
                timetable=draft,
                day_of_week=weekday,
                slot_code=period["code"],
                starts_at_local=_parse_time(period["start"]),
                ends_at_local=_parse_time(period["end"]),
                created_at=now,
                updated_at=now,
            )
            report.note("period", True)
