# M11 handoff

## State

Contracts **proposed**, not frozen. No implementation. Resume only after review
of `contracts/M11/review-decisions.md`.

| | |
|---|---|
| Branch | `m11/notices-third-party-sms` |
| From | `8d84c00` (`origin/main`) |
| Manifest | `school-contracts-v11` |
| Proposed freeze | `school-contracts-v12` |

## Startup (after implementation)

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M11 --profile standalone
python3 scripts/dev.py migrate M11 --profile standalone
python3 scripts/dev.py seed M11 --scenario baseline
```

Use printed URLs from `up`. Fictional localhost persona only; never real SMS.

## PENDING integration

- Real provider credentials, templates, Unicode delivery, charges (sandbox).
- Real Registry verified contacts / guardian revocation.
- Real M01 auth/2FA for `sms.configure` when policy on.
- Production refusal of fake adapters (integrate with profile guards).
