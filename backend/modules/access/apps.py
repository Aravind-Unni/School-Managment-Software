"""Django app config for M01 access."""

from __future__ import annotations

from django.apps import AppConfig


class AccessConfig(AppConfig):
    """Registers M01's tables under the ``access`` label."""

    name = "modules.access"
    label = "access"
    verbose_name = "M01 access (identity, permissions, 2FA)"
    default_auto_field = "django.db.models.BigAutoField"
