"""Production must refuse fake adapters, dev personas and demo fixtures.

Three independent mechanisms, each catching a different mistake. All three are
asserted because any one of them alone is a single point of failure.
"""

from __future__ import annotations

import pytest

from shared.ports import AdapterKind, PortRegistry, ProductionSafetyError


def test_registering_a_fake_under_production_raises_immediately():
    registry = PortRegistry(app_env="production")
    with pytest.raises(ProductionSafetyError, match="refusing to bind fake adapter"):
        registry.register("access", lambda: object(), kind=AdapterKind.FAKE)


def test_an_adapter_that_forgets_to_declare_its_kind_is_treated_as_fake():
    # The safe default is the one that fails loudly in production.
    registry = PortRegistry(app_env="production")
    with pytest.raises(ProductionSafetyError):
        registry.register("access", lambda: object())


def test_a_real_adapter_is_accepted_under_production():
    registry = PortRegistry(app_env="production")
    registry.register("access", lambda: "real", kind=AdapterKind.REAL)
    assert registry.resolve("access") == "real"


def test_an_active_dev_persona_refuses_production_startup():
    registry = PortRegistry(app_env="production")
    with pytest.raises(ProductionSafetyError, match="DEV_PERSONA_MODE"):
        registry.assert_production_safe(dev_persona_mode="fixed", demo_fixtures_enabled=False)


def test_demo_fixtures_refuse_production_startup():
    registry = PortRegistry(app_env="production")
    with pytest.raises(ProductionSafetyError, match="demo fixtures"):
        registry.assert_production_safe(dev_persona_mode="off", demo_fixtures_enabled=True)


def test_a_clean_production_configuration_is_accepted():
    registry = PortRegistry(app_env="production")
    registry.register("access", lambda: "real", kind=AdapterKind.REAL)
    registry.assert_production_safe(dev_persona_mode="off", demo_fixtures_enabled=False)


def test_non_production_profiles_skip_the_assertion_entirely():
    registry = PortRegistry(app_env="standalone")
    registry.register("access", lambda: "fake", kind=AdapterKind.FAKE)
    registry.assert_production_safe(dev_persona_mode="fixed", demo_fixtures_enabled=True)


def test_rebinding_a_port_is_refused():
    # Silent rebinding is how a real adapter gets replaced by a fake unnoticed.
    registry = PortRegistry(app_env="standalone")
    registry.register("access", lambda: "one", kind=AdapterKind.FAKE)
    with pytest.raises(ValueError, match="already bound"):
        registry.register("access", lambda: "two", kind=AdapterKind.FAKE)


def test_resolving_an_undeclared_consumer_fails_at_boot_not_at_request_time():
    registry = PortRegistry(app_env="standalone", declared_consumers=frozenset({"access"}))
    registry.register("access", lambda: "a", kind=AdapterKind.FAKE)
    with pytest.raises(LookupError, match="declared consumer"):
        registry.resolve("platform")


def test_resolving_an_unbound_port_is_a_clear_lookup_error():
    registry = PortRegistry(app_env="standalone")
    with pytest.raises(LookupError, match="not bound"):
        registry.resolve("platform")


def test_ports_are_singletons_within_a_registry():
    registry = PortRegistry(app_env="standalone")
    registry.register("clock", lambda: object(), kind=AdapterKind.FAKE)
    assert registry.resolve("clock") is registry.resolve("clock")


def test_a_module_declaring_an_unfakeable_port_is_refused():
    from contracts.registration import ModuleRegistration
    from shared.ports import build_fake_registry

    registration = ModuleRegistration(
        id="M00", slug="demo", api_prefix="/api/demo/", consumers=("telepathy",)
    )
    with pytest.raises(ValueError, match="cannot fake"):
        build_fake_registry(
            registration, app_env="standalone", clock=None, worker_available=False
        )


def test_a_sqlite_dsn_is_refused_so_tests_cannot_diverge_from_production():
    from config.env import ConfigurationError, parse_database_url

    with pytest.raises(ConfigurationError, match="postgresql"):
        parse_database_url("sqlite:////tmp/school.db")


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SESSION_SECRET", "hunter2"),
        ("TOTP_ENCRYPTION_KEY", "abcdefghijklmnop="),
        ("OBJECT_STORAGE_SECRET_KEY", "wJalrXUtnFEMI"),
    ],
)
def test_secrets_never_appear_in_diagnostic_output(name, value):
    from config.env import redact

    assert redact(name, value) == "<set>"
    assert value not in redact(name, value)


def test_a_dsn_keeps_its_structure_but_loses_its_password():
    from config.env import redact

    redacted = redact("DATABASE_URL", "postgresql://dev:s3cr3t@db:5432/school")
    assert "s3cr3t" not in redacted
    assert "db:5432/school" in redacted
