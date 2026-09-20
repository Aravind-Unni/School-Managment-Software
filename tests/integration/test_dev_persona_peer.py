"""Which peers may use the fixed development persona, and which never may.

The persona is the only identity a standalone stack has, so the rule for who may
present it is a security boundary, not a convenience. These assertions pin it.

Written when M03's browser suite became the first to run against a REAL
containerised stack and every request came back 401: the API's port is published
to 127.0.0.1 only, but Docker NATs the connection, so the peer the container sees
is the bridge gateway. The fix widens which peer ADDRESSES count for a profile
that explicitly says so; it does not widen who can reach the port, and it does
not touch production, which refuses the persona twice over.
"""

from __future__ import annotations

import pytest

from contracts.errors import Unauthenticated
from contracts.identity import AuthLevel
from shared import fixtures
from shared.fakes.clock import FixedClock
from shared.http.context import (
    DevPersona,
    is_trusted_persona_peer,
    resolve_request_context,
)

PERSONA = DevPersona(
    actor_id=fixtures.TEACHER_T1,
    school_id=fixtures.SCHOOL_A,
    auth_level=AuthLevel.TWO_FACTOR,
)
DOCKER_BRIDGE_NETWORKS = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")


def resolve(remote_addr: str, *, app_env: str = "standalone", trusted=()):
    """Resolve a context for one peer address under the given profile."""
    return resolve_request_context(
        meta={"REMOTE_ADDR": remote_addr},
        app_env=app_env,
        dev_persona_mode="fixed",
        persona=PERSONA,
        clock=FixedClock(),
        trusted_persona_networks=trusted,
    )


# --- the default: loopback only --------------------------------------------


@pytest.mark.parametrize("address", ["127.0.0.1", "::1", "localhost"])
def test_loopback_is_always_trusted(address):
    assert is_trusted_persona_peer(address) is True
    assert resolve(address).actor_id == fixtures.TEACHER_T1


@pytest.mark.parametrize("address", ["172.18.0.1", "10.4.2.9", "192.168.1.7", "203.0.113.5"])
def test_no_other_peer_is_trusted_by_default(address):
    """A profile that configures nothing keeps exactly the old behaviour."""
    assert is_trusted_persona_peer(address) is False
    with pytest.raises(Unauthenticated) as raised:
        resolve(address)
    assert raised.value.message_key == "error.dev_persona_requires_loopback"


# --- what a development profile may opt into --------------------------------


@pytest.mark.parametrize("address", ["172.18.0.1", "10.4.2.9", "192.168.1.7"])
def test_a_declared_private_network_is_trusted(address):
    """This is the containerised stack's case: the Docker bridge gateway."""
    assert is_trusted_persona_peer(address, trusted_networks=DOCKER_BRIDGE_NETWORKS) is True
    assert resolve(address, trusted=DOCKER_BRIDGE_NETWORKS).actor_id == fixtures.TEACHER_T1


@pytest.mark.parametrize("address", ["203.0.113.5", "8.8.8.8", "198.51.100.22"])
def test_a_public_address_is_still_refused(address):
    """Declaring the private ranges must not admit the open internet."""
    assert is_trusted_persona_peer(address, trusted_networks=DOCKER_BRIDGE_NETWORKS) is False
    with pytest.raises(Unauthenticated):
        resolve(address, trusted=DOCKER_BRIDGE_NETWORKS)


@pytest.mark.parametrize("address", ["", "not-an-address", "172.18.0.1.5"])
def test_an_unparseable_peer_is_refused(address):
    """A malformed REMOTE_ADDR is refused, never treated as "probably local"."""
    assert is_trusted_persona_peer(address, trusted_networks=DOCKER_BRIDGE_NETWORKS) is False


def test_a_malformed_network_entry_does_not_admit_anyone():
    """A typo in configuration must fail closed."""
    assert is_trusted_persona_peer("172.18.0.1", trusted_networks=("172.16/12",)) is False


# --- production is refused twice over ---------------------------------------


def test_production_refuses_the_persona_even_from_loopback():
    with pytest.raises(Unauthenticated) as raised:
        resolve("127.0.0.1", app_env="production")
    assert raised.value.message_key == "error.dev_persona_forbidden_in_production"


def test_production_refuses_the_persona_even_with_every_network_declared():
    """The allowlist cannot be used to smuggle a persona into production."""
    with pytest.raises(Unauthenticated) as raised:
        resolve("172.18.0.1", app_env="production", trusted=("0.0.0.0/0",))
    assert raised.value.message_key == "error.dev_persona_forbidden_in_production"


def test_the_production_profile_declares_no_trusted_network():
    """Read from the profile itself, so a later edit to it fails here."""
    import pathlib

    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "backend"
        / "config"
        / "settings"
        / "production.py"
    ).read_text()
    assert "DEV_PERSONA_TRUSTED_NETWORKS" not in source


def test_the_port_publication_is_what_actually_limits_reachability():
    """The generated stack must publish the API to loopback only.

    This is the guarantee the allowlist relies on. If the API were ever published
    on 0.0.0.0, widening the trusted peers would widen real exposure -- so the
    two are asserted together, here, rather than in two files that drift.
    """
    import pathlib
    import sys

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "dev"))
    from harness.compose import render
    from harness.modules import load
    from harness.naming import ResourceNames

    generated = render(
        repo_root=repo_root,
        declaration=load(repo_root, "M03"),
        names=ResourceNames(module_id="M03", repo_root=repo_root),
        ports={"postgres": 15432, "api": 18000, "frontend": 15173},
        profile="standalone",
    )
    assert '"127.0.0.1:18000:8000"' in generated
    assert "0.0.0.0:18000" not in generated
    assert "DEV_PERSONA_TRUSTED_NETWORKS" in generated
