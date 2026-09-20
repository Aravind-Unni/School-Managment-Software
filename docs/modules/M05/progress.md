# M05 progress

| | |
|---|---|
| Phase | Implementation complete; awaiting PostgreSQL/browser evidence |
| Status | Contracts frozen + implemented. **STANDALONE_VERIFIED=false** (Docker down). |
| Branch | `m05/assessments-grades` |
| Started from | `619e933a331c69d5262945dcc297142672e39e2d` (`origin/main`) |
| Manifest revision | `school-contracts-v6` |
| PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/6 (draft) |
| Head commit | `c2fb1857e6ae429e52d8970ae8bb465776879957` |
| Last recorded | 2026-09-20 |

## Original request

Build M05 assessments, grades and published answer sheets as an independently
runnable standalone module. Contracts first; then implement. May commit/push/draft
PR; no merge/deploy.

## Completed behavior

- Contracts approved and frozen (`school-contracts-v6`).
- Shared `FilesPort` / `FakeFiles` / `AssessmentPort`.
- Backend: create, marks, evidence bind/view, submit/approve/publish/reopen,
  revisions, publication idempotency, published-results port.
- Frontend: setup, marking grid, publish preview, published view (en+ml).
- Seeds: baseline published S1=73.50 confirmed v2; S2 absent.
- Acceptance cases covered in `tests/modules/M05/` (23 tests).

## Incomplete / not-run

- Standalone PostgreSQL suite — Docker daemon unavailable this session.
- Browser suite — not-run.
- PENDING integration: real M12 files, signed reads, report snapshots, guardian
  revocation, real M01 2FA, worker crash/retry.

## Test numbers observed

```
check M05 --suite contracts → PASS (manifest, arch 7, shared 105, M05 contract 6)
MODULE_ID=M05 pytest tests/modules/M05 (test_sqlite) → 23 passed
check M05 --suite standalone → not-run (no Docker)
frontend vitest → 65 passed
```

## Exact next step

1. Start Docker; `python3 scripts/dev.py up M05 --profile standalone`
2. migrate + seed baseline; `check M05 --suite standalone`
3. `check M05 --suite browser` if Playwright available
4. `evidence M05`; set STANDALONE_VERIFIED only after peer verify from fresh checkout
