"""Django app config for M02 registry."""

from __future__ import annotations

from django.apps import AppConfig


class RegistryConfig(AppConfig):
    """Registers the academic registry's tables."""

    name = "modules.registry"
    label = "registry"
    verbose_name = "M02 academic registry"
    default_auto_field = "django.db.models.BigAutoField"
