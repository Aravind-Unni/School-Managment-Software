# M00 demo (placeholder)

**This is not a business module.** It owns no school domain and must never grow
one. It exists to prove the foundation: the runner, the profiles, the fakes, the
error envelope, pagination, optimistic concurrency, and the audit/outbox
transaction guarantee.

It stays in the repository permanently as the regression test for the
foundation itself.

- Contract: [`contracts/M00/openapi.yaml`](../../../contracts/M00/openapi.yaml)
  (generated from the real DRF views, not hand-written)
- Consumer fixtures: [`contracts/M00/fixtures/`](../../../contracts/M00/fixtures/)
- Code: `backend/modules/demo/`, `frontend/src/features/demo/`

## What it demonstrates

| Concern | Where |
|---|---|
| UUID + trusted school_id + integer version | `models.py` |
| authorise via host ScopeResolver, never inline | `services.py` |
| audit + outbox in the caller's transaction | `services.py::_write_trail` |
| optimistic concurrency and 409 | `services.py::update_note` |
| cursor pagination, capped page size | `services.py::list_notes` |
| thin views, no authorisation logic of their own | `views.py` |

## Running it

```bash
python scripts/dev.py up M00 --profile standalone
python scripts/dev.py seed M00 --scenario baseline
python scripts/dev.py check M00 --suite standalone
```
