"""Deterministic failure injection for dependency ports.

Lets a module test what it does when Registry is down or Platform rejects a
write, without patching internals. Injection is explicit and per-call-count so
a test can fail the second call only.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class InjectedFailure(RuntimeError):
    """Raised by a fake because a test asked it to fail here."""


@dataclass
class FailureInjector:
    """Records which calls should fail.

    Usage: ``injector.fail("registry.relationship_facts", on_call=2)`` then pass
    the injector into the fake. Call counting starts at 1.

    Does not handle: random or probabilistic failure. Flaky tests are worse than
    missing ones, so failures are always deterministic and addressed by index.
    """

    _planned: dict[str, set[int]] = field(default_factory=dict)
    _counts: dict[str, int] = field(default_factory=dict)

    def fail(self, operation: str, *, on_call: int = 1) -> None:
        """Plan a failure for the Nth invocation of ``operation``."""
        if on_call < 1:
            raise ValueError("on_call is 1-based")
        self._planned.setdefault(operation, set()).add(on_call)

    def maybe_fail(self, operation: str) -> None:
        """Increment the call counter for ``operation`` and raise if planned.

        Fakes call this at the top of each method. A fake that forgets to call
        it simply cannot be failure-tested, which the contract suite checks.
        """
        count = self._counts.get(operation, 0) + 1
        self._counts[operation] = count
        if count in self._planned.get(operation, ()):
            raise InjectedFailure(f"{operation} failed on call {count} as planned")

    def call_count(self, operation: str) -> int:
        """Return how many times ``operation`` was invoked."""
        return self._counts.get(operation, 0)
