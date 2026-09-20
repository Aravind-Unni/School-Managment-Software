# M08 review decisions

## Review outcome — APPROVED AS PROPOSED

**Reviewed by Abhinav M on 2026-09-21. Items 1–12 approved as proposed.**

Recorded in `contracts/revision.json` under revision `school-contracts-v9`.

| Item | Decision |
|---|---|
| 1 — event names | `transport.participation_changed` / `transport.billing_requested` (envelope-safe dotted form). Manual `BusParticipationChanged.v1` / `BusBillingRequested.v1` are aliases for the payload shapes only. |
| 2 — TransportPort | Add to `backend/contracts/transport.py`; owned by M08. Methods: `get_participation`, `request_period_charge`. |
| 3 — API mount | `/api/v1/...` as manual seeds (not `/api/transport/`). |
| 4 — permissions | Exactly `transport.manage`, `transport.read`, `transport.bill`. |
| 5 — 2FA | Not required for transport writes in baseline. Monetary posting is owned by Fees; Finance policy approval stays outside this module. |
| 6 — fee amount | Full-period amount comes from an approved fee-plan reference (`fee_plan_id` + schedule). Missing proration policy for partial periods → `BillingRequest.state=blocked` with `transport.error.proration_policy_missing`. Never invent proration. |
| 7 — source_key | `transport:{participation_id}:{billing_period}:{charge_kind}`. Period is `YYYY-MM`. charge_kind defaults to `period`. |
| 8 — bus assignment | Optional. Yes/no participation is enough when `bus_id` is null. |
| 9 — overlap | Reject create/patch that would leave two active participations overlapping for the same student (422 `transport.error.overlapping_participation`). |
| 10 — cancellation | Set `to_date`; historical BillingRequests and Fees charges remain. Partial-period correction is an AdjustmentRequest that calls `Fees.credit_charge` with a unique source_key. |
| 11 — FakeFees | Shared harness fake: source_key dedupe, commit-then-timeout, expose stored charges. Real M07 ledger integration stays PENDING. |
| 12 — broker/worker | Required for billing-run jobs and retries (`dev/modules/M08/module.json`). |

Deferred (not freeze blockers): GPS/routes, real M01 2FA, real Fees ledger wiring,
school-specific proration formulas.

---

## Source identity

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m08/bus-participation-fee-coordination` |
| Branched from | `6b6aef011b5f428b3d45ed0cd6761cfa88df8707` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v8` |
| Proposed freeze revision | `school-contracts-v9` |
