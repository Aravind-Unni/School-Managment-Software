"""Namespaced resource names, so two developers never collide.

Every mutable resource -- Compose project, database, volume, queue, bucket -- is
named from the triple (developer, worktree, module). Two people running M04
standalone on the same machine, or one person running M03 and M04 side by side,
get entirely separate resources.

Worktree is part of the key, not just the checkout path, because
``using-git-worktrees`` style parallel work is normal here and two worktrees of
the same repository would otherwise share a database.
"""

from __future__ import annotations

import getpass
import hashlib
import os
import pathlib
import re
import subprocess

#: PostgreSQL identifiers are lowercase, alphanumeric plus underscore, and
#: effectively limited to 63 bytes. Bucket names are stricter still, so the
#: sanitiser targets the intersection.
SAFE_CHARS = re.compile(r"[^a-z0-9]+")
MAX_IDENTIFIER_LENGTH = 40


def developer() -> str:
    """Return the current developer's short identifier.

    Prefers SCHOOL_DEV_NAME so CI and containers can set it explicitly; falls
    back to the OS username. Never fails: an unknown user becomes "anon", because
    a naming helper must not be the reason a command cannot start.
    """
    explicit = os.environ.get("SCHOOL_DEV_NAME", "").strip()
    if explicit:
        return sanitise(explicit)
    try:
        return sanitise(getpass.getuser())
    except Exception:
        return "anon"


def worktree_label(repo_root: pathlib.Path) -> str:
    """Return a short, stable label for this checkout or worktree.

    Combines the directory name with a hash of its absolute path. The hash is
    what distinguishes two worktrees that happen to share a directory name, which
    the bare name alone would not.

    Does not handle: renaming a worktree. That produces a new label and therefore
    new resources; the old ones remain until ``down`` is run, which is the safe
    direction to fail.
    """
    digest = hashlib.sha256(str(repo_root.resolve()).encode()).hexdigest()[:6]
    return f"{sanitise(repo_root.name)}_{digest}"


def git_branch(repo_root: pathlib.Path) -> str:
    """Return the current branch name, or "detached" when there is none.

    Informational only -- it appears in ``doctor`` output and the evidence
    bundle. It is deliberately NOT part of resource names: switching branches
    must not orphan a developer's database.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    name = result.stdout.strip()
    if result.returncode != 0 or not name:
        return "unknown"
    return "detached" if name == "HEAD" else name


def sanitise(raw: str) -> str:
    """Reduce a string to lowercase alphanumerics and underscores.

    Collapses runs of unsafe characters to a single underscore and trims to
    MAX_IDENTIFIER_LENGTH, so a long email-style username cannot overflow a
    PostgreSQL identifier.
    """
    cleaned = SAFE_CHARS.sub("_", raw.strip().lower()).strip("_")
    return (cleaned or "anon")[:MAX_IDENTIFIER_LENGTH]


class ResourceNames:
    """Every namespaced name for one (developer, worktree, module) triple."""

    def __init__(self, *, module_id: str, repo_root: pathlib.Path) -> None:
        """Compute the namespace once from the environment and the checkout."""
        self.module_id = module_id.upper()
        self.developer = developer()
        self.worktree = worktree_label(repo_root)
        self.repo_root = repo_root

    @property
    def stem(self) -> str:
        """Return the shared prefix all this triple's resources derive from."""
        return sanitise(f"{self.developer}_{self.worktree}_{self.module_id}")

    @property
    def compose_project(self) -> str:
        """Return the Docker Compose project name.

        Compose uses this to prefix container, network and volume names, so
        setting it is what keeps two simultaneous profiles apart.
        """
        return f"school_{self.stem}"

    @property
    def database(self) -> str:
        """Return the PostgreSQL database name."""
        return f"school_{self.stem}"

    @property
    def bucket(self) -> str:
        """Return the private object-storage bucket name.

        Hyphens rather than underscores: S3 bucket naming rules forbid
        underscores, and a name that works locally but not in production would
        surface only at deployment.
        """
        return f"school-{self.stem}".replace("_", "-")

    @property
    def queue(self) -> str:
        """Return the broker queue name for this module's jobs."""
        return f"{self.stem}_jobs"

    @property
    def volume_prefix(self) -> str:
        """Return the prefix for named volumes. Never deleted by ``down``."""
        return f"{self.compose_project}_data"

    def describe(self) -> dict[str, str]:
        """Return every derived name, for doctor output and the evidence bundle."""
        return {
            "developer": self.developer,
            "worktree": self.worktree,
            "module_id": self.module_id,
            "compose_project": self.compose_project,
            "database": self.database,
            "bucket": self.bucket,
            "queue": self.queue,
            "volume_prefix": self.volume_prefix,
        }
