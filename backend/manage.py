#!/usr/bin/env python
"""Django management entrypoint.

Defaults to the standalone profile. ``scripts/dev.py`` always passes an explicit
DJANGO_SETTINGS_MODULE, so this default only helps interactive use.
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    """Run a Django management command."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.standalone")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
