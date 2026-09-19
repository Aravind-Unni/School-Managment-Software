"""Per-profile Django settings.

Choose with DJANGO_SETTINGS_MODULE:
  config.settings.standalone  -- one business app + harness + fakes
  config.settings.integrated  -- approved apps + real ports
  config.settings.production  -- real only; refuses fakes, personas, demo data
  config.settings.test_sqlite -- LOCAL-ONLY unit tests without a database server

``test_sqlite`` is not a deployment profile and is never selected by Compose.
PostgreSQL-specific behaviour is asserted by the standalone suite against a real
PostgreSQL container, and by CI against a PostgreSQL service.
"""
