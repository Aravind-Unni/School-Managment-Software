"""WSGI entrypoint. DJANGO_SETTINGS_MODULE selects the profile."""

from __future__ import annotations

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
