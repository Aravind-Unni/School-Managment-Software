"""Development harness support for ``scripts/dev.py``.

STANDARD LIBRARY ONLY. These modules run before any dependency is installed --
``doctor`` in particular must work on a fresh checkout with no venv -- so
importing anything third-party here breaks the first command a new developer
runs.
"""
