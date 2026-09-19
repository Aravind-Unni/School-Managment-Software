"""Secret handling for M01. The only place credential material is transformed.

Rules this module exists to enforce:
  * TOTP seeds are encrypted with a key from the ENVIRONMENT, never from the
    database, so a database dump alone yields no working seed.
  * Recovery codes are stored as hashes only. Nobody -- not support, not an
    administrator -- can re-display one.
  * Session tokens are stored hashed, so a leaked row is not a usable cookie.
  * Nothing here logs its inputs or outputs.

Does not handle: passwords. Django's configured hasher does that, and adding a
second scheme here would mean two places to get it wrong.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

#: Recovery codes use an unambiguous alphabet: no 0/O, no 1/I/L, and no 8/B
#: confusion, because these codes are read off a screen (or a printout) and typed
#: back by hand, often by a parent on a phone. 30 characters, so ten of them carry
#: ~49 bits -- far beyond guessable inside any rate limit.
RECOVERY_ALPHABET = "ACDEFGHJKMNPQRSTUVWXYZ2345679"
RECOVERY_GROUP_LENGTH = 5
RECOVERY_CODE_COUNT = 10

#: Base32 secret length for TOTP. 160 bits, which is what RFC 4226 recommends and
#: what every mainstream authenticator handles.
TOTP_SECRET_BYTES = 20


class SecretConfigurationError(RuntimeError):
    """Raised when the encryption key is missing or unusable.

    Raised at first use rather than swallowed: a profile that cannot encrypt seeds
    must not accept an enrolment and store something unrecoverable.
    """


def _fernet() -> Fernet:
    """Return the Fernet instance built from TOTP_ENCRYPTION_KEY.

    Reads the key from settings each call rather than caching it at import, so a
    test can supply its own key without reloading the module.
    """
    key = getattr(settings, "TOTP_ENCRYPTION_KEY", "") or ""
    if not key:
        raise SecretConfigurationError(
            "TOTP_ENCRYPTION_KEY is not configured; refusing to handle TOTP seeds. "
            "The key must live outside the database."
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise SecretConfigurationError(
            "TOTP_ENCRYPTION_KEY is not a valid Fernet key (32 url-safe base64 encoded bytes)"
        ) from exc


def new_totp_secret() -> str:
    """Return a fresh base32 TOTP secret.

    Uses ``secrets``, not ``random``: an authenticator seed generated from a
    predictable PRNG is not a second factor.
    """
    return base64.b32encode(secrets.token_bytes(TOTP_SECRET_BYTES)).decode().rstrip("=")


def encrypt_secret(secret_base32: str) -> bytes:
    """Encrypt a TOTP secret for storage."""
    return _fernet().encrypt(secret_base32.encode())


def decrypt_secret(ciphertext: bytes) -> str:
    """Decrypt a stored TOTP secret.

    Raises SecretConfigurationError on an undecryptable value, which in practice
    means the key was rotated. Failing loudly is correct: silently treating it as
    "no factor" would downgrade the account's security without telling anyone.
    """
    try:
        return _fernet().decrypt(bytes(ciphertext)).decode()
    except InvalidToken as exc:
        raise SecretConfigurationError(
            "stored TOTP secret could not be decrypted; TOTP_ENCRYPTION_KEY may "
            "have been rotated. Affected accounts must re-enrol."
        ) from exc


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> tuple[str, ...]:
    """Return ``count`` fresh high-entropy recovery codes.

    Format ``XXXXX-XXXXX`` over the unambiguous alphabet: ~48 bits per code, far
    beyond guessable inside any rate limit.
    """
    return tuple(f"{_group()}-{_group()}" for _ in range(count))


def _group() -> str:
    """Return one unambiguous 5-character group."""
    return "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(RECOVERY_GROUP_LENGTH))


def hash_recovery_code(code: str, *, school_id: object) -> str:
    """Return the stored hash of a recovery code.

    Salted with the school id so an identical code in two deployments does not
    produce an identical hash. Uses SHA-256 rather than a slow KDF deliberately:
    the code carries ~49 bits of entropy and is rate-limited, so stretching buys
    nothing while making the hot verification path slow.
    """
    normalised = normalise_recovery_code(code)
    return hashlib.sha256(f"{school_id}:{normalised}".encode()).hexdigest()


def normalise_recovery_code(code: str) -> str:
    """Return a recovery code in canonical form for comparison.

    Uppercases and strips spaces, so a user typing a code with different spacing
    still matches. Does NOT strip the hyphen, because the hyphen is part of the
    format and accepting it optionally would double the input space to hash.
    """
    return code.strip().upper().replace(" ", "")


def hash_session_token(token: str) -> str:
    """Return the stored hash of a session token."""
    return hashlib.sha256(token.encode()).hexdigest()


def new_session_token() -> str:
    """Return a fresh opaque session token.

    43 url-safe characters, ~256 bits. The value is returned to the client once
    and only its hash is stored.
    """
    return secrets.token_urlsafe(32)


def constant_time_equals(left: str, right: str) -> bool:
    """Compare two secrets without leaking their relationship through timing."""
    return hmac.compare_digest(left.encode(), right.encode())
