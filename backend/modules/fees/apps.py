"""M07 fees Django app."""

from __future__ import annotations

from django.apps import AppConfig


class FeesConfig(AppConfig):
    """Registers fee ledger tables."""

    name = "modules.fees"
    label = "fees"
    verbose_name = "M07 fees payments balances and receipts"
    default_auto_field = "django.db.models.BigAutoField"
