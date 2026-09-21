"""Wall-clock implementation of ClockPort for deployed profiles.

Kept outside ``shared.fakes`` so production settings can import it without
tripping the fake-adapter refusal in ``arch_check``.
"""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """Return the current UTC instant from the process clock.

    Satisfies ClockPort. Does not handle: freezing time in tests — inject a
    FixedClock there instead.
    """

    def now(self) -> datetime:
        """Return timezone-aware UTC now."""
        return datetime.now(tz=UTC)
