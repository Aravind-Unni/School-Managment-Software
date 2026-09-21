"""CSV parsing and writing that cannot become a spreadsheet formula.

A cell beginning ``=``, ``+``, ``-``, ``@`` or a leading tab/CR is executed by
Excel and LibreOffice when the file is opened. That is the injection this module
exists to stop, in both directions:

  * on IMPORT the cell is stored with a neutralising prefix and is NOT an error
    row (review-decisions item 9): the value is legitimate data that merely
    looks like a formula, so refusing it would lose it.
  * on EXPORT the same prefix is applied before the value reaches the file.

Pure functions only: no IO, no clock, no Django.
"""

from __future__ import annotations

import csv
import io

#: Leading characters a spreadsheet interprets as the start of a formula.
FORMULA_TRIGGERS: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")

#: The prefixes the frozen fixture policy permits. Tab is the default because it
#: survives a round trip through ``csv`` without becoming part of the value the
#: way an apostrophe does in some readers.
ALLOWED_PREFIXES: tuple[str, ...] = ("\t", "'")

DEFAULT_PREFIX = "\t"


def looks_like_formula(value: str) -> bool:
    """Return whether a cell would be evaluated as a formula by a spreadsheet.

    Assumes ``value`` is the raw cell text. An already-neutralised value starts
    with the prefix and so still reports True; callers check
    ``is_neutralized`` first.
    """
    return value.startswith(FORMULA_TRIGGERS)


def is_neutralized(value: str, prefix: str = DEFAULT_PREFIX) -> bool:
    """Return whether a cell already carries a neutralising prefix."""
    return value.startswith(prefix)


def neutralize(value: str, prefix: str = DEFAULT_PREFIX) -> str:
    """Return a cell that a spreadsheet will treat as text, not a formula.

    Idempotent: a value already carrying the prefix is returned unchanged, so
    validate-then-commit cannot stack prefixes.

    Does not handle: the cell's meaning. Neutralising is a rendering concern;
    the domain adapter still validates the value.
    """
    if prefix not in ALLOWED_PREFIXES:
        raise ValueError(f"neutralisation prefix must be tab or apostrophe: {prefix!r}")
    if not value or is_neutralized(value, prefix):
        return value
    if looks_like_formula(value):
        return prefix + value
    return value


def strip_neutralization(value: str, prefix: str = DEFAULT_PREFIX) -> str:
    """Return the original cell text with one neutralising prefix removed.

    Needed when a stored value is compared against a domain key: the prefix is
    presentation, not identity.
    """
    return value[len(prefix) :] if is_neutralized(value, prefix) else value


def parse_rows(body: str, *, prefix: str = DEFAULT_PREFIX) -> tuple[list[str], list[dict]]:
    """Parse CSV text into a header and neutralised row dictionaries.

    Returns ``(columns, rows)`` where each row is
    ``{"number": int, "values": {column: cell}, "malformed": bool}``. ``number``
    is the 1-based source row number EXCLUDING the header, matching the frozen
    ``ImportRowErrorDTO.row`` minimum of 1.

    A row whose cell count differs from the header is marked malformed rather
    than dropped, so the reviewer is told which line to fix.

    Does not handle: XLSX. The frozen packet allows it at upload; parsing it is
    recorded as pending in docs/modules/M13/handoff.md.
    """
    reader = csv.reader(io.StringIO(body, newline=""))
    try:
        header = next(reader)
    except StopIteration:
        return [], []
    columns = [cell.strip() for cell in header]
    rows: list[dict] = []
    for number, raw in enumerate(reader, start=1):
        if not raw or all(cell == "" for cell in raw):
            continue
        malformed = len(raw) != len(columns)
        padded = list(raw) + [""] * max(0, len(columns) - len(raw))
        values = {
            column: neutralize(padded[index].strip(), prefix)
            for index, column in enumerate(columns)
        }
        rows.append({"number": number, "values": values, "malformed": malformed})
    return columns, rows


def write_rows(columns: list[str], rows: list[dict], *, prefix: str = DEFAULT_PREFIX) -> str:
    """Render rows to CSV text with every cell neutralised.

    Only ``columns`` are emitted, in order, so a field withheld by the export
    allowlist cannot reach the file even if the adapter returned it.
    """
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([neutralize(str(column), prefix) for column in columns])
    for row in rows:
        writer.writerow([neutralize(str(row.get(column, "")), prefix) for column in columns])
    return buffer.getvalue()
