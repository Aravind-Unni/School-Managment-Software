"""The shapes M03 hands to another module in-process.

Re-exports the shared contract DTOs so existing M03 imports keep working.
Ownership of the shape is ``backend/contracts/timetable.py`` after the M04
shared revision that added ``TimetablePort``.

Does not handle: the browser wire shape. ``api/wire.py`` renders that.
"""

from __future__ import annotations

from contracts.timetable import (
    CalendarDayDTO,
    PeriodSessionDTO,
    TeachingAuthorityDTO,
)

__all__ = [
    "CalendarDayDTO",
    "PeriodSessionDTO",
    "TeachingAuthorityDTO",
]
