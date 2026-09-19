"""Dynamic host port allocation.

Ports are never hardcoded: two developers, or two modules for one developer, must
be able to run at once. The allocator asks the OS for a free port, then records
the choice so ``up`` can print real URLs and later commands can find the running
services.

Does not handle: guaranteeing the port is still free when the container starts.
There is an unavoidable race between releasing the probe socket and Compose
binding it. ``up`` therefore verifies the binding afterwards and reports a clear
conflict rather than leaving a half-started stack.
"""

from __future__ import annotations

import json
import pathlib
import socket

#: Where allocations are recorded. Inside dev/, which .gitignore excludes.
ALLOCATION_DIRNAME = "dev/state"


def free_port() -> int:
    """Return a port the OS reports as free right now.

    Binding to port 0 lets the kernel choose, which avoids the "scan a range and
    hope" pattern that collides under parallel starts.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def is_listening(port: int, *, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Return whether something accepts connections on a port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(timeout)
        return probe.connect_ex((host, port)) == 0


class PortAllocation:
    """The ports assigned to one module's stack, persisted between commands."""

    def __init__(self, *, repo_root: pathlib.Path, stem: str) -> None:
        """Locate the allocation file for this namespace."""
        self._path = repo_root / ALLOCATION_DIRNAME / f"{stem}.ports.json"

    @property
    def path(self) -> pathlib.Path:
        """Return the allocation file path."""
        return self._path

    def load(self) -> dict[str, int]:
        """Return the recorded allocation, or an empty dict if there is none."""
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text())
        except ValueError:
            return {}
        return {key: int(value) for key, value in data.items()}

    def allocate(self, names: tuple[str, ...], *, reuse: bool = True) -> dict[str, int]:
        """Assign a free port to each name and persist the result.

        With ``reuse`` (the default) an existing allocation is kept, so running
        ``up`` twice does not move the URLs a developer has already bookmarked.
        Distinctness is enforced within a single call.
        """
        existing = self.load() if reuse else {}
        assigned: dict[str, int] = {}
        for name in names:
            if name in existing:
                assigned[name] = existing[name]
                continue
            candidate = free_port()
            while candidate in assigned.values() or candidate in existing.values():
                candidate = free_port()
            assigned[name] = candidate
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(assigned, indent=2, sort_keys=True) + "\n")
        return assigned

    def clear(self) -> None:
        """Remove the allocation record.

        Called by ``down``. Removing the record does NOT remove any volume; data
        outlives the port assignment on purpose.
        """
        self._path.unlink(missing_ok=True)
