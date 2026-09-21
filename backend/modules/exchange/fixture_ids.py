"""Scenario ids and synthetic names from contracts/M13 fixtures.

Not production policy and not real people. The Malayalam display names are
synthetic labels for the synthetic cast in ``shared.fixtures``; they exist so a
Malayalam report card has real Malayalam text to render rather than a
transliterated placeholder.
"""

from __future__ import annotations

import json
import pathlib
from uuid import UUID

from shared import fixtures

SCENARIO_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "contracts"
    / "M13"
    / "fixtures"
    / "scenario.json"
)


def load_scenario() -> dict:
    """Load the frozen M13 scenario fixture."""
    return json.loads(SCENARIO_PATH.read_text())


#: Malayalam labels for the synthetic cast. Same students as FIXTURE_LABELS.
MALAYALAM_DISPLAY_NAMES: dict[UUID, str] = {
    fixtures.STUDENT_S1: "വിദ്യാർത്ഥി എസ്1",
    fixtures.STUDENT_S2: "വിദ്യാർത്ഥി എസ്2",
    fixtures.STUDENT_S3: "വിദ്യാർത്ഥി എസ്3",
}

#: The Malayalam word for the language itself. Asserted in the PDF byte test.
MALAYALAM_LANGUAGE_WORD = "മലയാളം"

#: Actors the fixture treats as non-staff. Staff-wide import and export actions
#: are refused for them before Access is consulted, so a guardian cannot reach a
#: bulk endpoint even if a rule were mis-declared.
NON_STAFF_ACTORS: frozenset[UUID] = frozenset(
    {
        fixtures.STUDENT_S1,
        fixtures.STUDENT_S2,
        fixtures.STUDENT_S3,
        fixtures.GUARDIAN_G1,
        fixtures.GUARDIAN_G2,
        fixtures.STUDENT_S1_SCHOOL_B,
    }
)

#: Staff actors the baseline scenario grants exchange work to.
STAFF_ACTORS: frozenset[UUID] = frozenset(
    {
        fixtures.PRINCIPAL_P1,
        fixtures.TEACHER_T1,
        fixtures.TEACHER_T2,
        fixtures.TEACHER_T3,
    }
)


def malayalam_name(student_id: UUID) -> str:
    """Return the synthetic Malayalam label for a student.

    Falls back to the Malayalam word for 'student' so a report card for an
    unlabelled pupil still renders Malayalam rather than Latin text.
    """
    return MALAYALAM_DISPLAY_NAMES.get(student_id, "വിദ്യാർത്ഥി")
