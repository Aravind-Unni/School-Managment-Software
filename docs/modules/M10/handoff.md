# M10 handoff

## Where things stand

M10 alumni is implemented on branch `m10/alumni-records-contact-permissions`.
Contracts frozen under `school-contracts-v11`. Local SQLite module tests and
contracts suite are the verification target for this session. Standalone
PostgreSQL and browser suites not run.

## Source identity

| Item | Value |
|---|---|
| Branched from | `3ae3f8cbc25e09d04cb9a409411072cd6fd9a1bc` |
| Manifest | `school-contracts-v11` |
| Head | `76700d9883eddba0aebe0f773feba1d543bbfd07` (+ docs follow-up) |
| Draft PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/11 |

## Startup

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M10 --profile standalone
python3 scripts/dev.py migrate M10 --profile standalone
python3 scripts/dev.py seed M10 --scenario baseline
python3 scripts/dev.py check M10 --suite contracts
python3 scripts/dev.py check M10 --suite standalone
python3 scripts/dev.py check M10 --suite browser
python3 scripts/dev.py evidence M10
python3 scripts/dev.py down M10
```

## Fictional login (standalone)

Reviewer persona: `PRINCIPAL_P1` via localhost-only fake auth with fixture
grants for `alumni.*`. Scenario unrelated actor is denied. Never accept client
school/role headers.

## Manual smoke after seed

1. GET `/api/v1/alumni/candidates` → graduate + transfer pending.
2. POST approve graduate `include=true` → profile + `alumni.profile_approved`.
3. Transfer remains pending until explicit include.
4. PATCH contact preference `allowed=false` → not selectable for contact.
5. POST `/api/v1/alumni/exports` with `phone` → 422 `alumni.error.export_field_not_granted`.
6. As unrelated actor: GET `/api/v1/alumni` → 403.

## Migrations

- `alumni/migrations/0001_initial.py` — reversible create. No irreversible ops.

## PENDING integration

- real_student_left_ingestion
- real_account_lifecycle
- exchange_export_delivery
- real_m01_auth_2fa

## Next action for a fresh agent

1. Confirm contracts + SQLite suites green
2. Boot standalone stack and run PostgreSQL + browser suites
3. Update acceptance.json only after observed results
