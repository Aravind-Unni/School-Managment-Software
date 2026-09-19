"""Business module packages. Exactly one is installed per standalone profile.

A module here may import ``contracts`` and ``shared``. It may NEVER import
another module under this package: cross-module collaboration goes through the
typed service ports in ``contracts.ports``, bound by the host.
``scripts/arch_check.py`` fails CI on a violation.

Only ``demo`` (M00) has code in B00. The fourteen business modules hold a README
and no ``__init__.py`` on purpose: they are not importable, so nothing can
accidentally depend on an unimplemented module, and ``scripts/dev.py up M04``
fails honestly instead of booting an empty app.
"""
