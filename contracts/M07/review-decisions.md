# M07 review decisions — PROPOSED, NOT FROZEN

Awaiting human review. Do not treat artefacts as frozen until
`contracts/revision.json` lists M07 and `manifest.json` status is `frozen`.

---

## Source identity

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m07/fees-payments-balances-receipts` |
| Branched from | `da0570c2efdd3e17ef852164d0a62a9265416fbf` (`origin/main`, M06 merged) |
| Manifest revision at proposal | `school-contracts-v7` |
| Proposed freeze revision | `school-contracts-v8` (only after approval) |

---

## Items needing an explicit yes / no

### 1 — Event type names

Manual: `PaymentPosted.v1`, `PaymentReversed.v1`, `ChargePosted.v1`. Frozen
envelope uses dotted snake names (`attendance.submitted`).

**Propose:** `fees.payment_posted`, `fees.payment_reversed`, `fees.charge_posted`
(schema_version 1 on the envelope).

### 2 — Shared `FeesPort`

Manual requires `raise_charge`, `credit_charge`, `get_balance` for other modules
(bus/library). No `FeesPort` exists in `backend/contracts` today.

**Propose:** add `FeesPort` + fee DTOs to `backend/contracts` (owned by M07).
Standalone consumers bind the real fees service; other modules' standalone
profiles do not pull fees ORM. M08/M09 later consume the port.

### 3 — API mount path

Packet template said `/api/fees/`. Manual and M02–M06 use `/api/v1/...`.

**Propose:** paths relative to `/api/v1` exactly as the manual seeds:
`/fee-plans`, `/charges`, `/payments`, `/payments/{id}/reversals`,
`/students/{id}/fee-statement`, plus supporting reads for overdue list,
concessions, and receipt by id.

### 4 — Permission codes

Manual: `fees.configure`; `fees.read`; `fees.record_payment`; `fees.concede`;
`fees.reverse_payment`; `fees.refund`.

**Propose:** exactly those six strings. Students/guardians get `fees.read` only
for self/linked-child via relationship fixtures (never client-asserted).

### 5 — 2FA step-up surface

Manual: reversal/refund and major concessions require recent 2FA
(`Access.require_recent_2fa`, max_age_seconds=300).

**Propose:** step-up on `POST /payments/{id}/reversals`, `POST /refunds`, and
`POST /concessions` when concession amount ≥ 50% of charge balance or
`major=true`. Fake Access simulates stale 2FA; real M01 integration stays
PENDING.

### 6 — Fee plan shape (no invented policy)

Manual owns FeeHead, FeePlan(version, applicability, schedule). Late charges,
concession authority matrices and bus proration need signed school examples.

**Propose baseline:** fee heads are opaque codes (`tuition`, `bus`, `misc`);
plans carry `version`, `applicability` (`{standards?, section_ids?, student_ids?}`),
and `schedule` (`[{fee_head_id, amount_paise, due_date}]`). No auto late fee,
no bus proration formula, no concession matrix in code — those remain PENDING
until signed policy examples exist. Concessions are explicit posted credits with
reason + `fees.concede`.

### 7 — Payment methods and references

Manual: cash/bank/UPI recorded by staff; reference text does not verify bank
settlement; no gateway.

**Propose:** `method` enum `cash|bank|upi` only. `reference` optional string.
No settlement verification.

### 8 — Idempotency and source_key

**Propose:** `Idempotency-Key` required on `POST /payments`. Same key + same
payload returns existing receipt (200). Same key + different payload → 409
`fees.error.idempotency_payload_conflict`. Charge `source_key` unique per school;
reuse with same payload returns existing charge; changed payload → 409
`fees.error.source_key_conflict`.

### 9 — Receipt / payment numbers

**Propose:** server-allocated monotonic receipt `number` string per school
(`RCP-YYYYMMDD-#####` civil date Asia/Kolkata). Unique `(school_id, number)`.
Never client-supplied.

### 10 — Overpayment and credits

**Propose:** allocation cannot exceed payment remainder or charge balance.
Unallocated payment remainder becomes student `Credit` (`kind=overpayment`)
usable on later charges. Explicit `RefundRecord` decreases available credit;
requires `fees.refund` + 2FA. Posted rows never edited/deleted — reverse +
replace.

### 11 — Opening balances / daily reconciliation

Manual: reconcile daily collections and opening balances.

**Propose:** baseline seed posts an `opening_balance` charge head via
`source_key=opening:{student_id}` so import totals are ledger rows, not a
second store. Daily collection summary is a read of payments by `posted_at`
date (Asia/Kolkata); no separate accounting subsystem.

### 12 — Broker/worker

Manual standalone: PostgreSQL + real transactions; no payment gateway. No
module-owned async jobs listed.

**Propose:** `module.json` keeps `broker: false`, `worker: false`. No Celery
jobs in M07 baseline.

---

## Explicitly deferred (not review blockers)

| Topic | Why deferred |
|---|---|
| Late fee automation | Needs signed school policy example |
| Bus proration | Needs signed policy; M08 posts charges via `Fees.raise_charge` |
| Concession authority matrix | Needs signed policy; baseline is permission + 2FA only |
| Real M01 auth/2FA | PENDING integration |
| Real M08 transport charge requests | PENDING integration |
| Online gateway / bank initiation | Out of product scope |

---

## Approval checklist (reviewer fills)

- [ ] Item 1 event names
- [ ] Item 2 FeesPort shared addition
- [ ] Item 3 API mount `/api/v1/...`
- [ ] Item 4 six permission codes
- [ ] Item 5 2FA surfaces
- [ ] Item 6 fee plan baseline (no invented late/bus/concession policy)
- [ ] Item 7 payment methods
- [ ] Item 8 idempotency / source_key
- [ ] Item 9 receipt numbers
- [ ] Item 10 overpayment credits + refunds
- [ ] Item 11 opening balance as ledger charges
- [ ] Item 12 no broker/worker

**Reviewer:** _______________ **Date:** _______________
