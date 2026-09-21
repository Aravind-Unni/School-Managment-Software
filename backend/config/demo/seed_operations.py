"""Demo operations: fees, library, notices, and a performance rebuild.

Fees: Term 1 tuition and exam fee charged to everyone; most families have
paid, some partly, some not at all (so the overdue list has entries). Term 2
tuition is charged but not yet due. Library: a small catalogue with loans.
Notices: one per class, published.
"""

from __future__ import annotations

import random
import uuid
from datetime import date, timedelta

from .api_actor import ApiActor, DemoApiError
from .seed_people import DemoCast

#: (code, label key, amount in rupees by standard band, due date)
FEE_SCHEDULE = (
    (
        "TUITION_T1",
        "fees.head.tuition_term1",
        {6: 11000, 7: 11000, 8: 12500, 9: 12500},
        "2026-06-15",
    ),
    ("EXAM_T1", "fees.head.exam", {6: 1200, 7: 1200, 8: 1500, 9: 1500}, "2026-09-10"),
    (
        "TUITION_T2",
        "fees.head.tuition_term2",
        {6: 11000, 7: 11000, 8: 12500, 9: 12500},
        "2026-10-15",
    ),
)

LIBRARY_TITLES = (
    ("Malgudi Days", "R. K. Narayan", "English"),
    ("Swami and Friends", "R. K. Narayan", "English"),
    ("Wings of Fire", "A. P. J. Abdul Kalam", "English"),
    ("The Story of My Experiments with Truth", "M. K. Gandhi", "English"),
    ("Panchatantra Stories", "Vishnu Sharma", "English"),
    ("Randamoozham", "M. T. Vasudevan Nair", "Malayalam"),
    ("Pathummayude Aadu", "Vaikom Muhammad Basheer", "Malayalam"),
    ("Balyakalasakhi", "Vaikom Muhammad Basheer", "Malayalam"),
    ("Chemmeen", "Thakazhi Sivasankara Pillai", "Malayalam"),
    ("Aithihyamala", "Kottarathil Sankunni", "Malayalam"),
    ("Alice's Adventures in Wonderland", "Lewis Carroll", "English"),
    ("Treasure Island", "Robert Louis Stevenson", "English"),
    ("The Jungle Book", "Rudyard Kipling", "English"),
    ("Around the World in Eighty Days", "Jules Verne", "English"),
    ("NCERT Mathematics Class 8", "NCERT", "English"),
    ("NCERT Science Class 9", "NCERT", "English"),
    ("Oxford School Atlas", "Oxford", "English"),
    ("Children's Encyclopedia of India", "Various", "English"),
)


def seed_fees(accountant: ApiActor, cast: DemoCast, school_id, *, rng: random.Random) -> int:
    """Create the fee plan, charge every student, and record payments."""
    from modules.fees.models import FeeHead

    accountant.post(
        "/fee-plans",
        {
            "fee_heads": [
                {"code": code, "label_key": label} for code, label, _, _ in FEE_SCHEDULE
            ],
            "applicability": {"standards": sorted(cast.sections)},
            "schedule": [
                {"fee_head_code": code, "amount_paise": amounts[6] * 100, "due_date": due}
                for code, _, amounts, due in FEE_SCHEDULE
            ],
            "version": 1,
        },
    )
    heads = {row.code: str(row.id) for row in FeeHead.objects.filter(school_id=school_id)}
    payments = 0
    for student in cast.students:
        charges = []
        for code, label, amounts, due in FEE_SCHEDULE:
            charge = accountant.post(
                "/charges",
                {
                    "student_id": student["id"],
                    "fee_head_id": heads[code],
                    "amount_paise": amounts[student["standard"]] * 100,
                    "due_date": due,
                    "source_key": f"demo:{code}:{student['id']}",
                    "description_key": label,
                },
            )
            charges.append((code, charge))
        roll = rng.random()
        due_now = [charge for code, charge in charges if code != "TUITION_T2"]
        if roll < 0.12:
            continue  # nothing paid: shows on the overdue list
        allocations = []
        for charge in due_now:
            amount = charge["amount_paise"]
            if roll < 0.25 and charge is due_now[-1]:
                amount = amount // 2  # part-paid exam fee
            allocations.append({"charge_id": charge["id"], "amount_paise": amount})
        accountant.post(
            "/payments",
            {
                "student_id": student["id"],
                "amount_paise": sum(row["amount_paise"] for row in allocations),
                "method": rng.choice(["upi", "upi", "cash", "bank"]),
                "reference": f"DEMO-{rng.randint(100000, 999999)}",
                "allocations": allocations,
            },
            idempotency_key=f"demo-payment-{student['id']}",
        )
        payments += 1
    return payments


def seed_library(
    librarian: ApiActor, cast: DemoCast, *, today: date, rng: random.Random
) -> int:
    """Create titles and copies, then lend books to some students."""
    copies = []
    for index, (name, author, language) in enumerate(LIBRARY_TITLES, start=1):
        title = librarian.post(
            "/library/titles", {"name": name, "author": author, "language": language}
        )
        for copy_number in range(1, 3):
            copy = librarian.post(
                "/library/copies",
                {"title_id": title["id"], "accession_no": f"LIB-{index:03d}-{copy_number}"},
            )
            copies.append(copy["id"])
    loans = 0
    borrowers = rng.sample(cast.students, k=min(20, len(cast.students)))
    for copy_id, student in zip(copies, borrowers, strict=False):
        # Issue refuses a past due date, so demo loans are current; some fall due soon.
        due = today + timedelta(days=rng.choice([1, 2, 3, 7, 10, 14]))
        librarian.post(
            "/library/loans",
            {
                "copy_id": copy_id,
                "borrower_person_id": student["id"],
                "borrower_type": "student",
                "due_date": due.isoformat(),
            },
            idempotency_key=f"demo-loan-{copy_id}",
        )
        loans += 1
    return loans


NOTICES = (
    (
        "Parent-teacher meeting",
        "The Term 1 parent-teacher meeting is on Saturday, 3 October, 10 am to 1 pm. "
        "Unit Test 1 results can be discussed with each subject teacher.",
    ),
    (
        "Sports day practice",
        "Sports day practice starts next week after the last period. "
        "Students should bring their PE kit on Tuesdays and Thursdays.",
    ),
    (
        "Science exhibition",
        "Students interested in the district science exhibition should register "
        "with their class teacher by Friday.",
    ),
)


def seed_notices(actors: dict[str, ApiActor], cast: DemoCast) -> int:
    """Publish one notice per class, written by a teacher."""
    teachers = [login for login, row in cast.staff.items() if row["subject"] is not None]
    published = 0
    for index, section_id in enumerate(cast.sections.values()):
        actor = actors[teachers[index % len(teachers)]]
        title, body = NOTICES[index % len(NOTICES)]
        notice = actor.post(
            "/notices",
            {
                "title": title,
                "body": body,
                "locale": "en",
                "audience": {"kind": "section", "section_id": section_id},
            },
        )
        try:
            actors["principal"].post(
                f"/notices/{notice['id']}/publish",
                {"expected_version": notice.get("version", 1)},
                idempotency_key=str(uuid.uuid4()),
            )
            published += 1
        except DemoApiError:
            continue
    return published


def rebuild_performance(principal: ApiActor) -> int:
    """Recompute dashboards and open attendance/missing-work warnings."""
    result = principal.post("/performance/rebuild", {})
    return int(result.get("count", 0))
