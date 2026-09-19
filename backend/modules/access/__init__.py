"""M01 access: school-scoped accounts, roles, sessions and the 2FA lifecycle.

This module IS Access. Unlike every other module it binds no fake Access adapter,
because it provides the real one; it binds a fake Registry only.

Never stores or logs: a plaintext password, a TOTP seed, a QR/otpauth URI, a
recovery-code value, or a session cookie. Seeds are encrypted with a key held
outside the database; recovery codes are stored as hashes only.
"""
