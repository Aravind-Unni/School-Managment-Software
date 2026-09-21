# M11 handoff

## State

Contracts **frozen** under `school-contracts-v12`. Module implemented on
`m11/notices-third-party-sms`. Local SQLite module tests and contracts suite
green. Standalone PostgreSQL + browser **not-run**.

| | |
|---|---|
| Branch | `m11/notices-third-party-sms` |
| From | `8d84c00` (`origin/main`) |
| Manifest | `school-contracts-v12` |
| Draft PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/12 |

## Startup

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M11 --profile standalone
python3 scripts/dev.py migrate M11 --profile standalone
python3 scripts/dev.py seed M11 --scenario baseline
```

Use printed URLs from `up`. Fixed synthetic persona (publisher =
PRINCIPAL_P1). Never real SMS.

## Expected outcomes (baseline)

- One English + one Malayalam draft notice.
- Duplicate dedupe → one provider send.
- Forged callback → 401; delivery unchanged.
- Timeout → reconcile via lookup; no second send.
- Revoked guardian contact → skipped_revoked; no SMS.
- Malayalam template Unicode preserved.
- Logs use `secret_ref` only.

## Migrations

- `modules/communications/migrations/0001_initial.py` — reversible CreateModel
  set. Document: dropping tables loses notice/delivery history (irreversible
  data loss on reverse in production).

## PENDING integration

- Real provider credentials, templates, Unicode delivery, charges (sandbox).
- Real Registry verified contacts / guardian revocation.
- Real M01 auth/2FA for `sms.configure` when policy on.
- Production refusal of fake adapters (profile guards).
