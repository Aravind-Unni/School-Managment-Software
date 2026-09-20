# M07 review decisions

## Review outcome — APPROVED AS PROPOSED

**Reviewed by Abhinav M on 2026-09-20. Items 1–12 approved as proposed.**

Recorded in `contracts/revision.json` under revision `school-contracts-v8`.

| Item | Decision |
|---|---|
| 1 — event names | `fees.payment_posted` / `fees.payment_reversed` / `fees.charge_posted` |
| 2 — FeesPort | Add to `backend/contracts`; owned by M07 |
| 3 — API mount | `/api/v1/...` as manual seeds |
| 4 — permissions | Six codes exactly as manual |
| 5 — 2FA | Reversal, refund, major concessions (max_age 300s) |
| 6 — fee plan | Opaque heads/schedule; no invented late/bus/concession policy |
| 7 — methods | `cash\|bank\|upi` only |
| 8 — idempotency | Key + source_key conflict → 409 |
| 9 — receipt numbers | Server `RCP-YYYYMMDD-#####` |
| 10 — overpayment | Credit + explicit refund |
| 11 — opening balance | Ledger charges `opening:{student_id}` |
| 12 — broker/worker | None in baseline |

---

## Source identity

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m07/fees-payments-balances-receipts` |
| Branched from | `da0570c2efdd3e17ef852164d0a62a9265416fbf` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v7` |
| Freeze revision | `school-contracts-v8` |

Deferred (not freeze blockers): late fees, bus proration, concession authority
matrix, real M01/M08 integration.
