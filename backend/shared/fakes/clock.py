"""Controllable clocks. Tests advance time explicitly instead of sleeping."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


class FixedClock:
    """A clock frozen at one instant, advanceable by the test.

    Satisfies ClockPort. Prefer this over freezegun where the code under test
    already takes a ClockPort, because the injection point stays visible.
    """

    def __init__(self, instant: datetime | None = None) -> None:
        """Create a clock at ``instant``, defaulting to a fixed term date.

        The default is inside the fixture school term so date-sensitive code
        behaves the same in every test that does not care about the date.
        """
        self._instant = instant or datetime(2026, 7, 15, 4, 30, tzinfo=UTC)
        if self._instant.tzinfo is None:
            raise ValueError("clock instant must be timezone-aware UTC")

    def now(self) -> datetime:
        """Return the frozen instant."""
        return self._instant

    def advance(self, **delta: float) -> datetime:
        """Move the clock forward and return the new instant.

        Accepts timedelta keywords (``minutes=20``). Refuses a negative delta:
        a test that needs to go backwards should construct a new clock, so the
        intent is explicit.
        """
        step = timedelta(**delta)
        if step < timedelta(0):
            raise ValueError("FixedClock cannot move backwards; build a new clock")
        self._instant = self._instant + step
        return self._instant

    def set(self, instant: datetime) -> None:
        """Jump the clock to an explicit timezone-aware instant."""
        if instant.tzinfo is None:
            raise ValueError("clock instant must be timezone-aware UTC")
        self._instant = instant
