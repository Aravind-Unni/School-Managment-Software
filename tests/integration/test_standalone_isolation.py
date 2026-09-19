"""Standalone mode installs exactly one business app and no other.

These assertions are what make "other business apps must be absent from
INSTALLED_APPS and from imports" verifiable rather than aspirational.
"""

from __future__ import annotations

import sys

import pytest
from django.conf import settings

from shared.module_catalog import BUSINESS_MODULE_IDS, MODULE_SLUGS


def test_only_the_target_module_app_is_installed():
    module_apps = [app for app in settings.INSTALLED_APPS if app.startswith("modules.")]
    assert module_apps == ["modules.demo"]


def test_no_other_business_module_is_installed():
    installed = set(settings.INSTALLED_APPS)
    for module_id in BUSINESS_MODULE_IDS:
        assert f"modules.{MODULE_SLUGS[module_id]}" not in installed


def test_no_other_business_module_is_even_imported():
    # Absent from INSTALLED_APPS is not enough: an import would still couple them.
    imported = {name for name in sys.modules if name.startswith("modules.")}
    foreign = {
        name for name in imported if not name.startswith("modules.demo") and name != "modules"
    }
    assert foreign == set()


def test_the_harness_app_is_installed_in_a_development_profile():
    assert "shared.harness" in settings.INSTALLED_APPS


def test_every_bound_port_is_a_fake_in_standalone():
    assert set(settings.SCHOOL_PORTS.kinds().values()) == {"fake"}


def test_the_bound_ports_are_exactly_what_the_module_declared():
    from modules.demo.registration import REGISTRATION

    assert set(settings.SCHOOL_PORTS.kinds()) == set(REGISTRATION.consumers)


def test_atomic_requests_is_off_so_rollback_assertions_are_meaningful():
    # A hidden per-request transaction would make "same transaction" ambiguous.
    assert settings.DATABASES["default"]["ATOMIC_REQUESTS"] is False


def test_timestamps_are_utc_and_timezone_aware():
    assert settings.USE_TZ is True
    assert settings.TIME_ZONE == "UTC"


def test_both_product_languages_are_configured():
    assert dict(settings.LANGUAGES) == {"en": "English", "ml": "Malayalam"}


def test_drf_has_no_permissive_defaults():
    # Authorisation comes from the Access port, never from a DRF default.
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == []
    assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == []


def test_the_shared_exception_handler_is_installed():
    assert (
        settings.REST_FRAMEWORK["EXCEPTION_HANDLER"] == "shared.http.errors.exception_handler"
    )


def test_an_unimplemented_module_fails_honestly_rather_than_booting_empty():
    import importlib

    from shared.module_catalog import address_for

    # M04 has no code yet. Importing its registration must fail, which is what
    # makes `dev.py up M04` report absence instead of serving an empty app.
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(address_for("M04").registration_path)
