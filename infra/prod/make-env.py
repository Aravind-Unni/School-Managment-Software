#!/usr/bin/env python3
"""Write infra/prod/.env with freshly generated secrets.

Usage: python3 infra/prod/make-env.py school.example.in
Refuses to overwrite an existing .env (secrets must never be regenerated on a
live install: the 2FA key would orphan every enrolled authenticator).
Standard library only, so it runs on a bare server.
"""

from __future__ import annotations

import base64
import os
import secrets
import sys
import uuid
from pathlib import Path


def main() -> int:
    """Generate the file or explain why not."""
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    domain = sys.argv[1]
    target = Path(__file__).with_name(".env")
    if target.exists():
        print(f"refusing: {target} already exists")
        return 1
    fernet_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    owner_password = secrets.token_urlsafe(12)
    target.write_text(
        f"""DOMAIN={domain}
ALLOWED_HOSTS={domain}
SCHOOL_ID={uuid.uuid4()}
POSTGRES_USER=school
POSTGRES_PASSWORD={secrets.token_urlsafe(24)}
POSTGRES_DB=school_prod
SESSION_SECRET={secrets.token_urlsafe(48)}
TOTP_ENCRYPTION_KEY={fernet_key}
OBJECT_STORAGE_BUCKET=school-private
OBJECT_STORAGE_ACCESS_KEY=school{secrets.token_hex(4)}
OBJECT_STORAGE_SECRET_KEY={secrets.token_urlsafe(24)}
HOST_HTTP_PORT=80
HOST_HTTPS_PORT=443
BACKUP_KEEP_DAYS=14
BACKUP_HOUR_UTC=20
GUNICORN_WORKERS=3
PLATFORM_OPS_ACTOR_IDS=
OWNER_LOGIN=owner
OWNER_PASSWORD={owner_password}
OWNER_DISPLAY_NAME=School Owner
"""
    )
    target.chmod(0o600)
    print(f"wrote {target}")
    print(f"first owner login: owner / {owner_password}  (change it after first sign-in)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
