"""Integrated profile smoke: real binder refuses missing ports and loads factories."""

from __future__ import annotations

from config.real_ports import REAL_PORT_FACTORIES, _bind_known_factories, required_ports_for


def test_real_port_factories_cover_declared_fakeable_set():
    """Every port the harness can fake must also have a real factory entry.

    Integrated mode must not silently omit a provider that standalone fakes.
    """
    from shared.ports.bindings import FAKEABLE_PORTS

    _bind_known_factories()
    missing = sorted(FAKEABLE_PORTS - set(REAL_PORT_FACTORIES))
    assert missing == [], f"real binder missing factories for {missing}"


def test_required_ports_for_unions_consumers():
    """Union of consumers across registrations is what integrated must bind."""

    class _Reg:
        def __init__(self, consumers):
            self.consumers = consumers

    ports = required_ports_for([_Reg(("access", "clock")), _Reg(("registry", "access"))])
    assert ports == frozenset({"access", "clock", "registry"})


def test_integrated_approved_module_ids_follow_assembly_order():
    """APPROVED_MODULE_IDS must match the C02 assembly sequence."""
    import ast
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "backend/config/settings/integrated.py"
    tree = ast.parse(path.read_text())
    approved = None
    for node in tree.body:
        target_id = getattr(getattr(node, "target", None), "id", None)
        if isinstance(node, ast.AnnAssign) and target_id == "APPROVED_MODULE_IDS":
            approved = ast.literal_eval(node.value)
            break
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, "id", None) == "APPROVED_MODULE_IDS":
                    approved = ast.literal_eval(node.value)
    assert approved is not None
    assert approved[0] == "M00"
    assert "M14" in approved
    assert "M02" in approved
    assert approved.index("M01") < approved.index("M03")
