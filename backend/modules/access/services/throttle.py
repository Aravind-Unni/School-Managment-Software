"""Throttling for authentication endpoints, by account AND by source address.

Two independent counters, because they stop different attacks: per-account slows
password guessing against one victim, per-address slows credential stuffing across
many accounts.

The cooldown is progressive but always FINITE. A permanent attacker-triggered
lockout is itself a denial of service against the legitimate account holder, so it
is deliberately not implemented.

Backed by Django's cache. In the standalone profile that is a real local cache, not
a no-op: a throttle that silently forgets is not a throttle.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.cache import cache

from contracts.errors import RateLimited

#: Failures allowed before a cooldown begins, per counter.
ACCOUNT_FAILURE_LIMIT = 5
ADDRESS_FAILURE_LIMIT = 20

#: How long a counter remembers failures.
COUNTER_WINDOW_SECONDS = 900

#: Progressive cooldown, in seconds, indexed by how far past the limit we are.
#: Finite by design, and capped: the last value is the maximum wait, ever.
COOLDOWN_LADDER_SECONDS: tuple[int, ...] = (30, 60, 300, 900)


@dataclass(frozen=True, slots=True)
class ThrottleKey:
    """One throttle counter's identity."""

    kind: str
    value: str

    @property
    def cache_key(self) -> str:
        """Return the namespaced cache key."""
        return f"m01:throttle:{self.kind}:{self.value}"


def cooldown_for(failures: int, limit: int) -> int:
    """Return the cooldown in seconds for a failure count, or 0 if under the limit.

    Climbs the ladder and then stays at its last rung, so the wait never becomes
    effectively permanent.
    """
    if failures < limit:
        return 0
    over = failures - limit
    index = min(over, len(COOLDOWN_LADDER_SECONDS) - 1)
    return COOLDOWN_LADDER_SECONDS[index]


def record_failure(key: ThrottleKey) -> int:
    """Increment a counter and return the new failure count."""
    current = cache.get(key.cache_key, 0) + 1
    cache.set(key.cache_key, current, COUNTER_WINDOW_SECONDS)
    return current


def clear(key: ThrottleKey) -> None:
    """Reset a counter after a successful authentication."""
    cache.delete(key.cache_key)


def enforce(key: ThrottleKey, limit: int) -> None:
    """Raise RateLimited when a counter is over its limit.

    Called BEFORE verifying a credential, so a throttled caller is refused without
    the expensive hash comparison -- which also removes the timing signal that
    would otherwise reveal whether the account exists.
    """
    failures = cache.get(key.cache_key, 0)
    cooldown = cooldown_for(failures, limit)
    if cooldown:
        raise RateLimited(retry_after_seconds=cooldown)


def account_key(school_id: object, login_name: str) -> ThrottleKey:
    """Return the per-account counter key.

    Keyed on the login NAME rather than a resolved user id, so failures against a
    non-existent account are counted too. Otherwise enumeration would be free.
    """
    return ThrottleKey("account", f"{school_id}:{login_name.strip().lower()}")


def address_key(remote_addr: str) -> ThrottleKey:
    """Return the per-source-address counter key."""
    return ThrottleKey("address", remote_addr or "unknown")
