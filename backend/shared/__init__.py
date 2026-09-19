"""Shared harness runtime: port binding, HTTP plumbing, fakes and fixtures.

Importable by any module. This package may import ``backend.contracts`` and
Django, but MUST NOT import any ``backend.modules.*`` package -- enforced by
``scripts/arch_check.py``.
"""
