"""Signed, expiring tokens for reading one file version through the API.

Every file read goes through ``/api/v1/file-bytes/<id>``: object storage stays
private (its hostname is internal to the server), and the link a browser gets
works for ``seconds`` only. The token is signed with the deployment secret, so
it cannot be forged or re-pointed at another file.
Does not handle: revocation before expiry (keep the lifetime short).
"""

from __future__ import annotations

from uuid import UUID

from django.core import signing

SALT = "files.read.v1"

#: Upper bound on any link's lifetime, whatever a policy row says.
MAXIMUM_SECONDS = 900


def mint(file_id: UUID, version: int) -> str:
    """Return a token authorising one read of ``file_id`` at ``version``."""
    return signing.dumps({"f": str(file_id), "v": int(version)}, salt=SALT, compress=True)


def verify(token: str, *, file_id: UUID, max_age_seconds: int) -> int | None:
    """Return the authorised version, or None if the token is bad, stale or foreign."""
    try:
        claims = signing.loads(token, salt=SALT, max_age=min(max_age_seconds, MAXIMUM_SECONDS))
    except signing.BadSignature:
        return None
    if claims.get("f") != str(file_id):
        return None
    try:
        return int(claims["v"])
    except (KeyError, TypeError, ValueError):
        return None
