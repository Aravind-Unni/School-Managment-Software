# M09 review decisions — PROPOSED (awaiting human gate)

**Status: NOT APPROVED.** Do not freeze in `contracts/revision.json` until
items below are decided. Implementation must not start before freeze.

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m09/library-catalogue-lending` |
| Branched from | `b046ad6e567e3a1e6d165d17ffd101c3821300be` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v9` |
| Proposed freeze revision | `school-contracts-v10` |

---

## Decisions proposed from the development manual

| # | Topic | Proposal | Alternatives |
|---|---|---|---|
| 1 | Event names | Dotted envelope-safe: `library.loan_issued`, `library.loan_returned`, `library.overdue_detected`. Manual `LibraryLoanIssued.v1` etc. are payload aliases only. | Keep CamelCase Type.v1 as envelope event_type (rejected elsewhere). |
| 2 | LibraryPort | Add `backend/contracts/library.py`: `get_open_loans(ctx, person_id)`, `get_availability(ctx, title_id)`. | Wider port with issue/return (keep those HTTP-only). |
| 3 | API mount | Paths under `/api/v1/` (`/library/titles`, `/library/copies`, …) matching manual seeds. | `/api/library/` from PACKET template (out of date vs M02–M08). |
| 4 | Permissions | Exact codes from manual: `library.catalogue.manage`, `library.issue`, `library.return`, `library.renew`, `library.read_overdues`. Plus `library.read_own` for student/guardian own loans/availability. | Collapse issue/return/renew into one `library.circulate` (manual lists them separately). |
| 5 | 2FA | Not required for baseline library writes in standalone. Real M01 step-up stays PENDING. | Require `Access.require_recent_2fa` on catalogue.manage / circulate. |
| 6 | Copy states | Enum: `available`, `on_loan`, `lost`, `damaged`, `withdrawn`. Issue requires `available`; return restores `available` unless condition is lost/damaged. | Separate “reserved”. |
| 7 | Borrower types | Enum: `student`, `staff`. Fake Registry supplies student S1/S2; staff borrower uses fixture person when seeded. | Only `student` at launch. |
| 8 | Active loan uniqueness | DB unique partial index: one open loan per copy (`returned_at IS NULL`). Concurrent issue → one 201 + one 409 `state_conflict`. | Application-only lock. |
| 9 | Accession uniqueness | Unique `(school_id, accession_no)`. Duplicate → 422 `library.error.duplicate_accession`. | Global unique without school. |
| 10 | ISBN | Optional on Title; **not** unique. Catalogue import flags duplicate ISBN for review, does not reject. | Unique ISBN. |
| 11 | Return idempotency | Second return with same/closed loan returns 200 closed LoanDTO; does not append second return or second event. | 409 on second return. |
| 12 | Renewal | Requires open loan; body `{new_due_date, expected_version, reason?}`. Appends Renewal row preserving `old_due`. Rejects if `new_due_date` ≤ current due or overdue at school date. | Allow overdue renewals. |
| 13 | Borrower limits | **Data, not code:** seed fixture `max_active_loans_per_borrower=3`, `max_renewals_per_loan=2`. Exceed → 422. Not claimed as approved CBSE/school policy. | Leave unlimited until school supplies numbers. |
| 14 | Overdue | School civil date Asia/Kolkata: `due_date < as_of` ⇒ overdue. Event `library.overdue_detected` emitted when overdue queue is read/scanned for a newly overdue open loan (at-least-once; consumer dedupes). | Nightly job only. |
| 15 | Withdrawal | Copy → `withdrawn` via CopyAdjustment with reason; flags outstanding loan (loan stays open, copy not issuable). History retained. No auto-delete of borrower with active loan. | Force-close loan on withdraw. |
| 16 | Fines | Out of scope. No money fields in Library. Future charges go to Fees. | Embed fine_paise (rejected). |
| 17 | Import | `POST /library/catalogue-imports` accepts rows; returns review items for duplicate ISBN/accession. Does not auto-merge. | Silent overwrite. |
| 18 | Own loans visibility | Student/guardian: `library.read_own` + relationship scope. Other students get 404 on foreign loans (not 403). Librarians use circulate/read_overdues. | 403 for foreign. |

---

## Open questions for the reviewer (blockers if rejected)

1. Confirm permission split (`library.issue` / `library.return` / `library.renew` vs one circulate code).
2. Confirm seed borrower limits (3 active / 2 renewals) are acceptable as **fixture data** until school policy exists.
3. Confirm overdue detection on GET overdues (no worker in M09 `module.json`) vs requiring a broker.

Deferred (not freeze blockers): real M01 auth/2FA, real Registry borrower contact fields beyond FakeRegistry, fines via Fees, barcode hardware.
