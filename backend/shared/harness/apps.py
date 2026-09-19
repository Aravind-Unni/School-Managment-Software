"""Django app config for the shared harness."""

from __future__ import annotations

from django.apps import AppConfig


class HarnessConfig(AppConfig):
    """Registers the harness's audit/outbox tables.

    ``label`` is explicit so the table prefix stays ``harness_`` regardless of
    the dotted path this app is imported under.
    """

    name = "shared.harness"
    label = "harness"
    verbose_name = "Development harness (audit/outbox test tables)"
    default_auto_field = "django.db.models.BigAutoField"
