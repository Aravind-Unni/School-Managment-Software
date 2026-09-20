# M09 review decisions

## Review outcome — APPROVED AS PROPOSED

**Reviewed by Abhinav M on 2026-09-21. Items 1–18 approved as proposed.**

Recorded in `contracts/revision.json` under revision `school-contracts-v10`.

| Item | Decision |
|---|---|
| 1 — event names | `library.loan_issued` / `library.loan_returned` / `library.overdue_detected` |
| 2 — LibraryPort | `get_open_loans`, `get_availability` in `backend/contracts/library.py` |
| 3 — API mount | `/api/v1/library/...` |
| 4 — permissions | `library.catalogue.manage`, `library.issue`, `library.return`, `library.renew`, `library.read_overdues`, `library.read_own` |
| 5 — 2FA | Not required in baseline; real M01 step-up PENDING |
| 6 — copy states | `available`, `on_loan`, `lost`, `damaged`, `withdrawn` |
| 7 — borrower types | `student`, `staff` |
| 8 — active loan uniqueness | Partial unique index + transaction lock |
| 9 — accession uniqueness | Unique `(school_id, accession_no)` |
| 10 — ISBN | Optional; not unique; import review only |
| 11 — return idempotency | Second return returns closed LoanDTO; no second event |
| 12 — renewal | Preserve old_due; reject overdue / non-increasing due |
| 13 — borrower limits | Fixture data: max 3 active loans, max 2 renewals |
| 14 — overdue | School civil date; detect on GET overdues |
| 15 — withdrawal | Adjust to withdrawn; history retained |
| 16 — fines | Out of scope |
| 17 — import | Duplicate accession/ISBN review items |
| 18 — own loans | Foreign borrower → 404 |

Deferred: real M01 auth/2FA, real Registry borrower contacts, fines via Fees.

---

## Source identity

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m09/library-catalogue-lending` |
| Branched from | `b046ad6e567e3a1e6d165d17ffd101c3821300be` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v9` |
| Freeze revision | `school-contracts-v10` |
