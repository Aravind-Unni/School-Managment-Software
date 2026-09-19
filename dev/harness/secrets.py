"""Generates local development secrets OUTSIDE Git.

``.env.example`` is committed and contains names only. The real values live in
``dev/secrets/<stem>.env``, which ``.gitignore`` excludes. Nothing in this module
ever writes a value into a tracked file.

Secrets are generated once per namespace and then reused, so restarting a stack
does not invalidate an encrypted TOTP seed a developer just enrolled.
"""

from __future__ import annotations

import base64
import pathlib
import secrets as secrets_module
import stat

SECRETS_DIRNAME = "dev/secrets"

#: Variables generated locally. Everything else in .env.example is derived from
#: the namespace or the allocated ports, not random.
GENERATED_NAMES = ("SESSION_SECRET", "TOTP_ENCRYPTION_KEY", "OBJECT_STORAGE_SECRET_KEY")


def _fernet_compatible_key() -> str:
    """Return a 32-byte urlsafe-base64 key, the shape Fernet requires.

    Generated with ``secrets``, not ``random``. The TOTP seeds encrypted under
    this key are authentication material, so a predictable PRNG would be a real
    vulnerability rather than a style problem.
    """
    return base64.urlsafe_b64encode(secrets_module.token_bytes(32)).decode()


class LocalSecrets:
    """The generated secret file for one namespace."""

    def __init__(self, *, repo_root: pathlib.Path, stem: str) -> None:
        """Locate (but do not yet create) the secret file."""
        self._path = repo_root / SECRETS_DIRNAME / f"{stem}.env"

    @property
    def path(self) -> pathlib.Path:
        """Return the secret file's path."""
        return self._path

    def ensure(self) -> dict[str, str]:
        """Return the secrets, generating and persisting them on first use.

        The file is created 0600. Existing values are preserved: regenerating
        SESSION_SECRET would log every developer out, and regenerating
        TOTP_ENCRYPTION_KEY would make enrolled seeds undecryptable.
        """
        existing = self.read()
        values = dict(existing)
        for name in GENERATED_NAMES:
            if not values.get(name):
                values[name] = (
                    _fernet_compatible_key()
                    if name == "TOTP_ENCRYPTION_KEY"
                    else secrets_module.token_urlsafe(48)
                )
        if values != existing:
            self._write(values)
        return values

    def read(self) -> dict[str, str]:
        """Return the current contents, or an empty dict when absent."""
        if not self._path.exists():
            return {}
        values: dict[str, str] = {}
        for line in self._path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            values[key.strip()] = value.strip()
        return values

    def _write(self, values: dict[str, str]) -> None:
        """Write the secret file with owner-only permissions."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        body = [
            "# GENERATED LOCAL DEVELOPMENT SECRETS -- NOT IN GIT, NOT FOR ANY",
            "# DEPLOYED ENVIRONMENT. Delete this file to rotate; doing so",
            "# invalidates sessions and any enrolled TOTP seed in this namespace.",
        ]
        body.extend(f"{key}={values[key]}" for key in sorted(values))
        self._path.write_text("\n".join(body) + "\n")
        self._path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def exists(self) -> bool:
        """Return whether the secret file has been generated."""
        return self._path.exists()
