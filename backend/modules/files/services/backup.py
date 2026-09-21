"""Module-local backup verifier fake: verified or unverified."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class BackupVerifier:
    """Fixture stand-in for independent backup restoration checks.

    Defaults to verified so economical purge can proceed in baseline seeds.
    Tests flip mode to unverified to assert purge blocking.
    """

    mode: str = "verified"
    _overrides: dict[UUID, bool] = field(default_factory=dict)

    def set_mode(self, mode: str) -> None:
        """Set global verified/unverified mode."""
        if mode not in {"verified", "unverified"}:
            raise ValueError(f"unknown backup mode: {mode!r}")
        self.mode = mode

    def set_source(self, source_id: UUID, *, verified: bool) -> None:
        """Override verification for one source object."""
        self._overrides[source_id] = verified

    def clear(self) -> None:
        """Reset overrides and default to verified."""
        self._overrides.clear()
        self.mode = "verified"

    def is_verified(self, source_id: UUID) -> bool:
        """Return whether the source may be treated as backup-verified."""
        if source_id in self._overrides:
            return self._overrides[source_id]
        return self.mode == "verified"


_VERIFIER = BackupVerifier()


def backup_verifier() -> BackupVerifier:
    """Return the process-wide verifier used by purge and tests."""
    return _VERIFIER
