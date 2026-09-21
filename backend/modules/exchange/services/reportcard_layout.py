"""Report-card content: the lines printed for one pupil. Pure; no IO.

Grades come from the school's grade bands (installed from its config file);
with no bands configured, no grade letter is printed rather than a guessed one.
Does not handle: page layout, fonts or multiple pages (pdf_render does that).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True, slots=True)
class SubjectLine:
    """One subject's published total."""

    subject: str
    score: Decimal
    max_score: Decimal


def grade_for(percent: Decimal, bands: list[dict]) -> str | None:
    """Return the first band (highest first) whose min_percent ``percent`` reaches."""
    for band in bands:
        if percent >= Decimal(str(band["min_percent"])):
            return str(band["grade"])
    return None


def percent_of(score: Decimal, max_score: Decimal) -> Decimal | None:
    """Return score as a percentage of max, to one decimal, or None if max is 0."""
    if max_score <= 0:
        return None
    return (score * 100 / max_score).quantize(Decimal("0.1"))


def subject_lines(items: list[dict], subject_names: dict[str, str]) -> list[SubjectLine]:
    """Sum each subject's published scores; skip items without a numeric score."""
    totals: dict[str, list[Decimal]] = {}
    for item in items:
        try:
            score = Decimal(str(item["score"]))
            max_score = Decimal(str(item["max_score"]))
        except (KeyError, InvalidOperation, TypeError):
            continue
        name = subject_names.get(str(item.get("subject_id")), "Subject")
        running = totals.setdefault(name, [Decimal(0), Decimal(0)])
        running[0] += score
        running[1] += max_score
    return [
        SubjectLine(subject=name, score=score, max_score=max_score)
        for name, (score, max_score) in sorted(totals.items())
    ]


def report_card_lines(
    *,
    locale: str,
    school_name: str,
    student_name: str,
    admission_no: str,
    class_label: str | None,
    subjects: list[SubjectLine],
    bands: list[dict],
    language_word: str,
    template_version: str,
) -> list[str]:
    """Return the report card's lines of text, in the requested language."""
    ml = locale == "ml"
    label = {
        "student": "വിദ്യാർത്ഥി" if ml else "Student",
        "admission": "പ്രവേശന നമ്പർ" if ml else "Admission no.",
        "class": "ക്ലാസ്" if ml else "Class",
        "language": "ഭാഷ" if ml else "Language",
        "subject": "വിഷയം" if ml else "Subject",
        "marks": "മാർക്ക്" if ml else "Marks",
        "grade": "ഗ്രേഡ്" if ml else "Grade",
        "total": "ആകെ" if ml else "Total",
        "none": "പ്രസിദ്ധീകരിച്ച ഫലങ്ങളില്ല" if ml else "No published results yet",
    }
    lines = [
        school_name,
        "",
        f"{label['student']}: {student_name}",
        f"{label['admission']}: {admission_no}",
    ]
    if class_label:
        lines.append(f"{label['class']}: {class_label}")
    lines.append(f"{label['language']}: {language_word}")
    lines.append("")
    if not subjects:
        lines.append(label["none"])
    else:
        lines.append(f"{label['subject']} | {label['marks']} | % | {label['grade']}")
        for row in subjects:
            percent = percent_of(row.score, row.max_score)
            grade = grade_for(percent, bands) if percent is not None and bands else None
            lines.append(
                f"{row.subject} | {row.score.normalize():f} / {row.max_score.normalize():f}"
                f" | {percent if percent is not None else '-'} | {grade or '-'}"
            )
        total = sum((row.score for row in subjects), Decimal(0))
        total_max = sum((row.max_score for row in subjects), Decimal(0))
        overall = percent_of(total, total_max)
        overall_grade = grade_for(overall, bands) if overall is not None and bands else None
        lines.append(
            f"{label['total']} | {total.normalize():f} / {total_max.normalize():f}"
            f" | {overall if overall is not None else '-'} | {overall_grade or '-'}"
        )
    lines.append("")
    lines.append(f"template: {template_version}")
    return lines
