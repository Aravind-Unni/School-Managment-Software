"""M08 transport Django app."""

from __future__ import annotations

from django.apps import AppConfig


class TransportConfig(AppConfig):
    """Registers bus participation and billing request tables."""

    name = "modules.transport"
    label = "transport"
    verbose_name = "M08 bus participation and fee coordination"
    default_auto_field = "django.db.models.BigAutoField"
