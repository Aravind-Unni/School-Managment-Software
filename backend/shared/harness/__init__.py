"""Harness-owned Django app: audit and outbox tables for the test Platform.

These tables belong to the HARNESS, not to M14 platform. They exist so that a
module developed standalone can assert that its audit row and its outbox event
were written in the same transaction as its domain write, and vanish on
rollback.

This app is installed in standalone and integrated test profiles. It is NOT
installed in production: M14 owns the real tables there.
"""
