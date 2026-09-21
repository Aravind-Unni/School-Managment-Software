"""M13 exchange Django app."""

from __future__ import annotations

from django.apps import AppConfig


class ExchangeConfig(AppConfig):
    """Registers import, export, report-card and snapshot tables."""

    name = "modules.exchange"
    label = "exchange"
    verbose_name = "M13 reports, imports and exports"
    default_auto_field = "django.db.models.BigAutoField"
