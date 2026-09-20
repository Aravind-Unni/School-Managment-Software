"""Deterministic fake adapters for every dependency port.

Bound in standalone mode so a module under development never imports an
unfinished provider. None of these is an ``allow_all`` or a no-op:
  * FakeAccess evaluates an explicit policy table and denies by default.
  * FakeRegistry answers only RelationshipFacts, from committed fixtures.
  * TestPlatformAdapter writes real rows in the caller's transaction and
    refuses to fake asynchronous behaviour.
  * FakeNotifications has no network code at all.
  * FakeObjectStorage still enforces school prefixes and grant expiry.

Every adapter accepts a FailureInjector so a module can test what it does when a
dependency fails.
"""

from .access import DEFAULT_STALE_AUTH_WINDOW, FakeAccess, PolicyRule, stale_context
from .assessment import FakeAssessment
from .attendance import FakeAttendance
from .clock import FixedClock
from .failures import FailureInjector, InjectedFailure
from .fees import FakeFees, FeePlanSeed, FeesCommitTimeout
from .files import FakeFiles
from .notifications import FakeNotifications, SentMessage
from .platform import EagerModeNotAsserted, TestPlatformAdapter
from .registry import FakeRegistry
from .storage import FakeObjectStorage
from .timetable import FakeTimetable

__all__ = [
    "DEFAULT_STALE_AUTH_WINDOW",
    "EagerModeNotAsserted",
    "FailureInjector",
    "FakeAccess",
    "FakeAssessment",
    "FakeAttendance",
    "FakeFees",
    "FakeFiles",
    "FakeNotifications",
    "FakeObjectStorage",
    "FakeRegistry",
    "FakeTimetable",
    "FeePlanSeed",
    "FeesCommitTimeout",
    "FixedClock",
    "InjectedFailure",
    "PolicyRule",
    "SentMessage",
    "TestPlatformAdapter",
    "stale_context",
]
