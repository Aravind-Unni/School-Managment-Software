# M13 review decisions

## Review outcome — APPROVED AS PROPOSED

**Reviewed against Development Manual v3.1 (M13 packet) supplied in the module
task.** Items 1–16 approved as proposed for freeze under `school-contracts-v14`.
Reviewer of record for this freeze: Abhinav M (task owner / collaborator pattern
matching M02–M12). Peer review of the implementation PR remains separate.

| Item | Decision |
|---|---|
| 1 — API mount | REST under `/api/v1` with path roots `imports/`, `exports/`, `reportcards/`, `reports/`, `import-templates/` (not `/api/exchange/` prefix) |
| 2 — permissions | `imports.validate`, `imports.commit`, `reports.read`, `reports.export`, `reportcards.generate` — match manual; **not** an `exchange.*` namespace |
| 3 — event names | `exchange.import_completed`, `exchange.report_ready`, `exchange.report_superseded` |
| 4 — DomainExchangePort | Module-local adapter registry in `backend/modules/exchange/adapters/`; no direct domain ORM |
| 5 — ExchangePort | New `backend/contracts/exchange.py` once this packet is frozen |
| 6 — import datasets | Allowlist: `enrolments`, `opening_balances`, `results`, `library_loans` |
| 7 — export/report datasets | Allowlist: `attendance_summary`, `progress`, `at_risk`, `ptm_summary`, `class_roster`, `subject_summary` |
| 8 — report cards | Bind `publication_id` and `result_revision_ids` immutably on snapshot; supersede links via `superseded_by` |
| 9 — CSV formula injection | Neutralize at parse with leading tab (`\t`) or apostrophe (`'`); not a validation error row |
| 10 — Malayalam PDF | Embedded fonts required; locale `ml` must render without tofu |
| 11 — async infrastructure | `object_storage` + `broker` + `worker` required for validate/commit/export/report jobs |
| 12 — commit integrity | `CommitImportRequest.source_digest` must match stored file digest or **409** `exchange.error.digest_mismatch` |
| 13 — idempotent commit | `Idempotency-Key` header required on commit; replay must not duplicate applies |
| 14 — FeesPort scope | Reports may call `get_balance` only; fakes must raise on `raise`/`credit` if called |
| 15 — real M01 auth | **PENDING** — standalone uses FakeAccess |
| 16 — real domain adapters | **PENDING** — standalone uses deterministic adapter fakes per dataset |

Deferred: production grade-policy text, distributor-style bulk files from real
schools, cross-manufacturer equivalence (N/A), first design-partner report sign-off.

---

## Source identity

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m13/reports-imports-exports` |
| Branched from | `3d0b03bbae4d7509ec5c27ef8e4a029d4eebdf13` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v13` |
| Freeze revision | `school-contracts-v14` |
