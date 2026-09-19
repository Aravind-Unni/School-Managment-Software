"""Deterministic synthetic fixtures. Same UUIDs on every machine, every run.

UUIDs are uuid5 over a fixed namespace, so they are stable across processes and
languages without being committed as opaque literals. Nothing here describes a
real person; all names are synthetic.

The cast is fixed by B00 so that every module's authorisation tests assert the
same relationships:

  School A (primary tenant)          School B (isolation counterparty)
  ---------------------------        --------------------------------
  S1, S2, S3  students               S1_B  student, used to prove that a
  G1          guardian of S1 and S2        School A actor gets 404, not 403
  G2          guardian, unrelated to S1
  T1          teacher assigned to class C1
  T2          teacher, unassigned

Does not handle: persistence. ``dev/harness`` seeds these into a database; this
module only supplies the identifiers and the expected relationship answers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

#: Fixed namespace for every synthetic id in this project. Changing it changes
#: every fixture UUID and is therefore a contract revision.
FIXTURE_NAMESPACE = uuid.UUID("6f1a9c2e-0b3d-4f5a-8c7b-1d2e3f4a5b6c")


def fixture_uuid(label: str) -> uuid.UUID:
    """Return the stable UUID for a fixture label.

    Deterministic across machines and runs. ``label`` is a dotted path such as
    ``"school_a.student.s1"``; two different labels never collide.
    """
    return uuid.uuid5(FIXTURE_NAMESPACE, label)


# --- Schools ---------------------------------------------------------------
SCHOOL_A = fixture_uuid("school.a")
SCHOOL_B = fixture_uuid("school.b")

# --- School A people -------------------------------------------------------
STUDENT_S1 = fixture_uuid("school_a.student.s1")
STUDENT_S2 = fixture_uuid("school_a.student.s2")
STUDENT_S3 = fixture_uuid("school_a.student.s3")
GUARDIAN_G1 = fixture_uuid("school_a.guardian.g1")
GUARDIAN_G2 = fixture_uuid("school_a.guardian.g2")
TEACHER_T1 = fixture_uuid("school_a.teacher.t1")
TEACHER_T2 = fixture_uuid("school_a.teacher.t2")
PRINCIPAL_P1 = fixture_uuid("school_a.principal.p1")

# --- School A structure ----------------------------------------------------
CLASS_C1 = fixture_uuid("school_a.section.c1")
CLASS_C2 = fixture_uuid("school_a.section.c2")
SUBJECT_MATHS = fixture_uuid("school_a.subject.maths")
SUBJECT_MALAYALAM = fixture_uuid("school_a.subject.malayalam")

# --- School B (isolation counterparty) -------------------------------------
STUDENT_S1_SCHOOL_B = fixture_uuid("school_b.student.s1")
TEACHER_T1_SCHOOL_B = fixture_uuid("school_b.teacher.t1")

#: The school term used by date-sensitive fixtures.
TERM_START = date(2026, 6, 1)
TERM_END = date(2027, 3, 31)
#: A date inside the term, used as the default effective_date in fixtures.
TERM_SAMPLE_DATE = date(2026, 7, 15)


@dataclass(frozen=True, slots=True)
class GuardianLink:
    """One guardian-to-student link in the fixture set."""

    guardian_id: uuid.UUID
    student_id: uuid.UUID
    school_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class TeacherAssignment:
    """One teacher-to-section assignment in the fixture set."""

    teacher_id: uuid.UUID
    section_id: uuid.UUID
    school_id: uuid.UUID
    is_class_teacher: bool = False


#: G1 guards S1 and S2. G2 guards only S3, which is what makes G2 unrelated
#: to S1 -- the negative case every module must test.
GUARDIAN_LINKS: tuple[GuardianLink, ...] = (
    GuardianLink(GUARDIAN_G1, STUDENT_S1, SCHOOL_A),
    GuardianLink(GUARDIAN_G1, STUDENT_S2, SCHOOL_A),
    GuardianLink(GUARDIAN_G2, STUDENT_S3, SCHOOL_A),
)

#: T1 is class teacher of C1. T2 has no assignment at all.
TEACHER_ASSIGNMENTS: tuple[TeacherAssignment, ...] = (
    TeacherAssignment(TEACHER_T1, CLASS_C1, SCHOOL_A, is_class_teacher=True),
)

#: Section membership: S1 and S2 in C1, S3 in C2.
SECTION_MEMBERSHIP: tuple[tuple[uuid.UUID, uuid.UUID], ...] = (
    (STUDENT_S1, CLASS_C1),
    (STUDENT_S2, CLASS_C1),
    (STUDENT_S3, CLASS_C2),
)

#: Human-readable labels, for seed data and test failure messages only.
FIXTURE_LABELS: dict[uuid.UUID, str] = {
    SCHOOL_A: "School A (Sunrise CBSE Campus, synthetic)",
    SCHOOL_B: "School B (isolation counterparty, synthetic)",
    STUDENT_S1: "S1",
    STUDENT_S2: "S2",
    STUDENT_S3: "S3",
    GUARDIAN_G1: "G1 (guardian of S1, S2)",
    GUARDIAN_G2: "G2 (guardian of S3; unrelated to S1)",
    TEACHER_T1: "T1 (class teacher of C1)",
    TEACHER_T2: "T2 (unassigned)",
    PRINCIPAL_P1: "P1 (principal)",
    CLASS_C1: "C1",
    CLASS_C2: "C2",
    STUDENT_S1_SCHOOL_B: "S1@SchoolB",
}


def section_of(student_id: uuid.UUID) -> uuid.UUID | None:
    """Return the fixture section for a student, or None if unplaced."""
    for candidate_student, section_id in SECTION_MEMBERSHIP:
        if candidate_student == student_id:
            return section_id
    return None


def guards(guardian_id: uuid.UUID, student_id: uuid.UUID) -> bool:
    """Return whether the fixture set links this guardian to this student.

    Used by the fake Registry and by tests asserting the deny case for G2/S1.
    """
    return any(
        link.guardian_id == guardian_id and link.student_id == student_id
        for link in GUARDIAN_LINKS
    )


def teaches(teacher_id: uuid.UUID, section_id: uuid.UUID) -> bool:
    """Return whether the fixture set assigns this teacher to this section."""
    return any(
        a.teacher_id == teacher_id and a.section_id == section_id for a in TEACHER_ASSIGNMENTS
    )
