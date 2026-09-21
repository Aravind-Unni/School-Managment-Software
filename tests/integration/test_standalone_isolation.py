"""Standalone mode installs exactly one business app and no other.

These assertions are what make "other business apps must be absent from
INSTALLED_APPS and from imports" verifiable rather than aspirational.
"""

from __future__ import annotations

import sys

import pytest
from django.conf import settings

from shared.module_catalog import BUSINESS_MODULE_IDS, MODULE_SLUGS, address_for


def target_app() -> str:
    """Return the one module app this profile installed.

    Read from MODULE_ID rather than hardcoded. These assertions were written
    against the M00 placeholder and passed for it alone, so `dev.py check <ID>
    --suite standalone` failed for every other module -- which nobody saw,
    because until M03 no module's standalone suite had ever been run against a
    real stack. Generalising them makes the isolation property verifiable for
    whichever module is under test, which is what it was always meant to assert.
    """
    return address_for(settings.MODULE_ID).django_app


def test_only_the_target_module_app_is_installed():
    module_apps = [app for app in settings.INSTALLED_APPS if app.startswith("modules.")]
    assert module_apps == [target_app()]


def test_no_other_business_module_is_installed():
    installed = set(settings.INSTALLED_APPS)
    for module_id in BUSINESS_MODULE_IDS:
        app = f"modules.{MODULE_SLUGS[module_id]}"
        if app == target_app():
            continue
        assert app not in installed


def test_no_other_business_module_is_even_imported():
    # Absent from INSTALLED_APPS is not enough: an import would still couple them.
    imported = {name for name in sys.modules if name.startswith("modules.")}
    foreign = {
        name for name in imported if not name.startswith(target_app()) and name != "modules"
    }
    assert foreign == set()


def test_the_harness_app_is_installed_in_a_development_profile():
    assert "shared.harness" in settings.INSTALLED_APPS


def test_every_bound_port_is_a_fake_or_m14_real_platform():
    """Standalone binds fakes; M14 alone binds its real PlatformAdapter.

    M14 owns PlatformPort, so its profile must not receive TestPlatformAdapter.
    Every other consumer port stays a fake.
    """
    # Read through the runtime holder, not settings.SCHOOL_PORTS: the holder
    # builds on demand, where the setting is only populated once something has
    # imported the URLconf. Depending on that made this test's result an accident
    # of collection order.
    from shared.ports import runtime

    kinds = dict(runtime.get_registry().kinds())
    if settings.MODULE_ID == "M14":
        assert kinds.pop("platform") == "real"
        assert all(kind == "fake" for kind in kinds.values())
    else:
        assert set(kinds.values()) == {"fake"}


def test_the_bound_ports_are_exactly_what_the_module_declared():
    import importlib

    from shared.ports import runtime

    registration = importlib.import_module(
        address_for(settings.MODULE_ID).registration_path
    ).REGISTRATION

    assert set(runtime.get_registry().kinds()) == set(registration.consumers)


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


def test_hiding_registration_makes_a_module_fail_honestly_rather_than_booting_empty():
    """Simulate unimplemented by hiding registration.py; import must fail.

    All M00-M14 modules ship registration.py. The empty-namespace failure mode
    is still required, so this test recreates it without leaving a permanent
    half-module in the tree.
    """
    import importlib
    import pathlib

    registration = (
        pathlib.Path(__file__).resolve().parents[2]
        / "backend"
        / "modules"
        / "alumni"
        / "registration.py"
    )
    hidden = registration.with_suffix(".py.hidden_for_isolation_test")
    registration.rename(hidden)
    try:
        # Drop any prior successful import from this process.
        for name in list(sys.modules):
            if name == "modules.alumni" or name.startswith("modules.alumni."):
                del sys.modules[name]
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(address_for("M10").registration_path)
    finally:
        if hidden.exists():
            hidden.rename(registration)
