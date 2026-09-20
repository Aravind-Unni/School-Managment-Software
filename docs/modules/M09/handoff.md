# M09 handoff

## Where things stand

M09 library is implemented on branch `m09/library-catalogue-lending`. Contracts
frozen under `school-contracts-v10`. Local SQLite module tests and contracts
suite are the verification target for this session. Standalone PostgreSQL and
browser suites not run.

## Source identity

| Item | Value |
|---|---|
| Branched from | `b046ad6e567e3a1e6d165d17ffd101c3821300be` |
| Manifest | `school-contracts-v10` |
| Draft PR | (set after open) |
| Head commit | (see git log -1) |

## Startup

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M09 --profile standalone
python3 scripts/dev.py migrate M09 --profile standalone
python3 scripts/dev.py seed M09 --scenario baseline
python3 scripts/dev.py check M09 --suite contracts
python3 scripts/dev.py check M09 --suite standalone
python3 scripts/dev.py check M09 --suite browser
python3 scripts/dev.py evidence M09
python3 scripts/dev.py down M09
```

## Fictional login (standalone)

Librarian persona: `PRINCIPAL_P1` via localhost-only fake auth with fixture
grants for `library.*`. S1 may read own loans; S2 gets 404 on S1 loans.
Never accept client school/role headers.

## Manual smoke after seed

1. GET `/api/v1/library/titles?q=കേരള` → one title.
2. POST `/api/v1/library/loans` with Idempotency-Key for S1 / ACC-1001 copy → 201.
3. Second issue of same copy → 409 `library.error.copy_not_available`.
4. Return twice → one `library.loan_returned` event.
5. GET `/api/v1/library/overdues?as_of=2026-09-02` after seeding overdue due → item.
6. As S2: GET S1 borrower loans → 404.

## Migrations

- `library/migrations/0001_initial.py` — reversible create. No irreversible ops.

## PENDING integration

- real_m01_auth_2fa
- real_m02_registry_borrower_contacts
- library_fines_out_of_scope

## Next action for a fresh agent

1. Confirm contracts + SQLite suites green
2. Start Docker; run standalone + browser suites
3. Update evidence and acceptance.json with observed results
