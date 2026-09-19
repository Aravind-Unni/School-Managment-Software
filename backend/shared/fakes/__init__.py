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
from .clock import FixedClock
from .failures import FailureInjector, InjectedFailure
from .notifications import FakeNotifications, SentMessage
from .platform import EagerModeNotAsserted, TestPlatformAdapter
from .registry import FakeRegistry
from .storage import FakeObjectStorage

__all__ = [
    "DEFAULT_STALE_AUTH_WINDOW",
    "EagerModeNotAsserted",
    "FailureInjector",
    "FakeAccess",
    "FakeNotifications",
    "FakeObjectStorage",
    "FakeRegistry",
    "FixedClock",
    "InjectedFailure",
    "PolicyRule",
    "SentMessage",
    "TestPlatformAdapter",
    "stale_context",
]
