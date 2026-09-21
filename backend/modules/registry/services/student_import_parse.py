"""Read a school's admissions spreadsheet (saved as CSV) into checked rows.

Pure: no database, no clock. The office's own column names are accepted
("Adm No", "Student Name", "DOB", "Mobile" ...) and so are the ways Indian
schools write a class ("6A", "6 - A", "Std 6 A", "VI-A") and a date
(31/05/2014, 31-05-2014, 2014-05-31). Every problem is reported against its
row and column so the office can fix the spreadsheet and try again.

Does not handle: several guardians per pupil (one parent per row), Excel
.xlsx files (save as CSV first), or deciding whether a pupil already exists
(the service checks the school's records).
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date

MAX_ROWS = 2000

#: Accepted spellings of each column, compared after lower-casing and
#: collapsing spaces, dots and underscores.
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "admission_no": ("admission no", "admission number", "adm no", "admission", "adm number"),
    "name": ("name", "student name", "full name", "pupil name", "name of student"),
    "class": ("class", "section", "std", "standard", "class section", "class and section"),
    "date_of_birth": ("date of birth", "dob", "birth date", "birthday"),
    "parent_name": (
        "parent name",
        "guardian name",
        "parent",
        "guardian",
        "father name",
        "mother name",
        "name of parent",
    ),
    "parent_phone": (
        "parent phone",
        "phone",
        "mobile",
        "mobile number",
        "phone number",
        "contact number",
        "guardian phone",
        "parent mobile",
    ),
    "parent_email": ("parent email", "email", "guardian email", "email id"),
    "language": ("language", "preferred language"),
}
REQUIRED_COLUMNS = ("admission_no", "name", "class")

ROMAN = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6,
    "vii": 7, "viii": 8, "ix": 9, "x": 10, "xi": 11, "xii": 12,
}  # fmt: skip
CLASS_PATTERN = re.compile(
    r"^(?:std\.?|class|grade|standard)?\s*([0-9]{1,2}|[ivx]{1,4})(?:st|nd|rd|th)?\s*[-–/\s]*\s*([a-z0-9]{1,8})$",  # noqa: RUF001 -- en dash as typed in labels
    re.IGNORECASE,
)
DATE_PATTERNS = (
    re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$"),  # 2014-05-31
    re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$"),  # 31/05/2014
)


@dataclass(frozen=True, slots=True)
class RowProblem:
    """One problem: spreadsheet row number (header is row 1), column, message key."""

    row: int
    column: str
    message_key: str
    value: str = ""

    def to_wire(self) -> dict:
        """Serialise for the API."""
        return {
            "row": self.row,
            "column": self.column,
            "message_key": self.message_key,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class ParsedRow:
    """One pupil as read from the file, before it is matched to the school."""

    row: int
    admission_no: str
    name: str
    standard: int | None
    section_name: str
    class_text: str
    date_of_birth: date | None
    parent_name: str
    parent_phone: str
    parent_email: str
    language: str


@dataclass(slots=True)
class ParsedFile:
    """Every row read, and every problem found while reading."""

    rows: list[ParsedRow] = field(default_factory=list)
    problems: list[RowProblem] = field(default_factory=list)


def _normalise_header(text: str) -> str:
    """Lower-case a header and collapse punctuation, so 'Adm. No' == 'adm no'."""
    return re.sub(r"[\s._]+", " ", text.strip().lower()).strip()


def match_columns(headers: list[str]) -> dict[str, int]:
    """Map each known column to its position in the header row."""
    found: dict[str, int] = {}
    for position, header in enumerate(headers):
        normal = _normalise_header(header)
        for column, aliases in COLUMN_ALIASES.items():
            if column not in found and (
                normal == column.replace("_", " ") or normal in aliases
            ):
                found[column] = position
    return found


def parse_class(text: str) -> tuple[int | None, str]:
    """Return (standard number, section name) from '6A', 'VI - A', 'Std 6 B'."""
    match = CLASS_PATTERN.match(text.strip())
    if match is None:
        return None, ""
    number_text, section = match.group(1).lower(), match.group(2).upper()
    number = int(number_text) if number_text.isdigit() else ROMAN.get(number_text)
    if number is None or not 1 <= number <= 12:
        return None, ""
    return number, section


def parse_date(text: str) -> date | None:
    """Return a date from 2014-05-31 or 31/05/2014 (day first), else None."""
    cleaned = text.strip()
    for position, pattern in enumerate(DATE_PATTERNS):
        match = pattern.match(cleaned)
        if match is None:
            continue
        first, second, third = (int(part) for part in match.groups())
        year, month, day = (first, second, third) if position == 0 else (third, second, first)
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def clean_phone(text: str) -> str | None:
    """Return a phone number as digits (with + kept), or None when it is not one."""
    cleaned = re.sub(r"[\s().-]", "", text.strip())
    if cleaned.startswith("+"):
        digits = cleaned[1:]
        return cleaned if digits.isdigit() and 10 <= len(digits) <= 15 else None
    return cleaned if cleaned.isdigit() and 10 <= len(cleaned) <= 15 else None


def parse_file(text: str) -> ParsedFile:
    """Read CSV text into rows and problems. Does not look anything up."""
    parsed = ParsedFile()
    reader = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    reader = [line for line in reader if any(cell.strip() for cell in line)]
    if not reader:
        parsed.problems.append(RowProblem(1, "file", "registry.import.empty_file"))
        return parsed
    columns = match_columns(reader[0])
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    for column in missing:
        parsed.problems.append(RowProblem(1, column, "registry.import.missing_column"))
    if missing:
        return parsed
    body = reader[1:]
    if len(body) > MAX_ROWS:
        parsed.problems.append(RowProblem(1, "file", "registry.import.too_many_rows"))
        return parsed

    def cell(line: list[str], column: str) -> str:
        position = columns.get(column)
        return line[position].strip() if position is not None and position < len(line) else ""

    for offset, line in enumerate(body):
        number = offset + 2
        row = _parse_row(number, line, cell, parsed.problems)
        if row is not None:
            parsed.rows.append(row)
    _flag_repeated_admission_numbers(parsed)
    return parsed


def _parse_row(number: int, line: list[str], cell, problems: list[RowProblem]):
    """Read one line; append its problems; return the row or None when unusable."""
    admission_no = cell(line, "admission_no")
    name = cell(line, "name")
    class_text = cell(line, "class")
    before = len(problems)
    if not admission_no:
        problems.append(RowProblem(number, "admission_no", "registry.import.required"))
    if not name:
        problems.append(RowProblem(number, "name", "registry.import.required"))
    standard, section = parse_class(class_text) if class_text else (None, "")
    if not class_text:
        problems.append(RowProblem(number, "class", "registry.import.required"))
    elif standard is None:
        problems.append(RowProblem(number, "class", "registry.import.bad_class", class_text))
    dob_text = cell(line, "date_of_birth")
    dob = parse_date(dob_text) if dob_text else None
    if dob_text and dob is None:
        problems.append(
            RowProblem(number, "date_of_birth", "registry.import.bad_date", dob_text)
        )
    phone_text = cell(line, "parent_phone")
    phone = clean_phone(phone_text) if phone_text else ""
    if phone_text and phone is None:
        problems.append(
            RowProblem(number, "parent_phone", "registry.import.bad_phone", phone_text)
        )
    email = cell(line, "parent_email")
    if email and "@" not in email:
        problems.append(RowProblem(number, "parent_email", "registry.import.bad_email", email))
    language = "ml" if cell(line, "language").lower() in {"ml", "malayalam", "മലയാളം"} else "en"
    if len(problems) > before:
        return None
    return ParsedRow(
        row=number,
        admission_no=admission_no,
        name=name,
        standard=standard,
        section_name=section,
        class_text=class_text,
        date_of_birth=dob,
        parent_name=cell(line, "parent_name"),
        parent_phone=phone or "",
        parent_email=email,
        language=language,
    )


def _flag_repeated_admission_numbers(parsed: ParsedFile) -> None:
    """Report an admission number used twice in the file, on its later rows."""
    seen: dict[str, int] = {}
    kept: list[ParsedRow] = []
    for row in parsed.rows:
        key = row.admission_no.strip()  # case is significant, as on admission
        if key in seen:
            parsed.problems.append(
                RowProblem(
                    row.row, "admission_no", "registry.import.repeated", row.admission_no
                )
            )
            continue
        seen[key] = row.row
        kept.append(row)
    parsed.rows = kept
