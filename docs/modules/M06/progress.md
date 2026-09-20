# M06 progress

| | |
|---|---|
| Phase | Implementation complete; awaiting PostgreSQL/browser evidence |
| Status | Contracts frozen + implemented. **STANDALONE_VERIFIED=false** |
| Branch | `m06/analytics-warnings-interventions` |
| Started from | `abe35b7c4621df8b6ebf111293401e80b4b255a1` (`origin/main`) |
| Manifest revision | `school-contracts-v7` |
| PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/7 (draft) |
| Head commit | `00626e53f031dba52705ffcc8f00363be87a9601` |
| Last recorded | 2026-09-20 |

## Original request

Build M06 analytics, warnings and academic interventions as an independently
runnable standalone module. Contracts first; then implement steps 1–4. May
commit/push/draft PR; no merge/deploy.

## Completed behavior

- Contracts frozen (`school-contracts-v7`): OpenAPI, DTOs, events, errors, ports,
  fixtures, review-decisions.
- Shared `PerformancePort` + `FakeAssessment` / `FakeAttendance` harness bindings.
- Backend: projections (simple_mean_v1), warning rules/lifecycle, interventions,
  meetings, scoped export (restricted observations omitted), rebuild endpoint,
  Celery reconcile task registration, broker+worker in module.json.
- Frontend: dashboard, at-risk list, interventions pages (en+ml).
- Seeds: S1 mean 65.00 / attendance 80.00; S2 missing; topic insufficient_data;
  S1 low_attendance warning open.
- Acceptance: 19 module tests + 6 contract tests observed green on SQLite.

## Incomplete / not-run

- Standalone PostgreSQL suite — not run this session (use `dev.py up` when Docker up).
- Browser suite — not-run.
- PENDING integration: rebuild against real M04/M05; comparable grading policies;
  real M01 2FA; worker crash/retry on real broker.

## Test numbers observed

```
check M06 --suite contracts → PASS (manifest, arch 7, shared 105, M06 contract 6)
MODULE_ID=M06 pytest tests/modules/M06 → 19 passed
frontend vitest → 65 passed
check M06 --suite standalone → not-run
check M06 --suite browser → not-run
```

## Exact next step

1. Start Docker; `python3 scripts/dev.py up M06 --profile standalone`
2. migrate + seed baseline; `check M06 --suite standalone`
3. `check M06 --suite browser` if Playwright available
4. `evidence M06`; set STANDALONE_VERIFIED only after peer verify from fresh checkout
