"""Business module packages. Exactly one is installed per standalone profile.

A module here may import ``contracts`` and ``shared``. It may NEVER import
another module under this package: cross-module collaboration goes through the
typed service ports in ``contracts.ports``, bound by the host.
``scripts/arch_check.py`` fails CI on a violation.

Only ``demo`` (M00) has code in B00. The fourteen business modules hold a README
and no ``__init__.py``. Be precise about what that does and does not buy:
``import modules.attendance`` still succeeds, because Python treats the directory
as a namespace package and hands back an empty module. What fails is
``modules.attendance.registration`` -- and that is the failure the host relies on,
so ``scripts/dev.py up M04`` reports "not implemented" rather than booting an
empty Django app. ``scripts/arch_check.py`` also fails if anything imports a
module with no ``registration.py``.
"""
