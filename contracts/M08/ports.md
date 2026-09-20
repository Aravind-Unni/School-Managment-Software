# M08 service ports — proposed under school-contracts-v9

What M08 **provides** and what it **consumes**.

M08 imports no other module. Dependencies are Protocols from
`backend/contracts`, bound to deterministic fakes in standalone.

---

## 1. Provided: `TransportPort`

```python
@runtime_checkable
class TransportPort(Protocol):
    """Bus participation lookup and period charge requests. Owned by M08."""

    def get_participation(
        self,
        context: RequestContext,
        student_id: UUID,
        on_date: date,
    ) -> TransportParticipationView:
        """Return the participation effective on the school civil date.

        Raises ObjectInaccessible when the student is absent or other-school,
        or when no participation covers that date.
        """

    def request_period_charge(
        self,
        context: RequestContext,
        participation_id: UUID,
        period: str,
    ) -> PeriodChargeResult:
        """Request Fees.raise_charge for one participation/period.

        source_key is transport:{participation_id}:{period}:period.
        Idempotent on source_key. Partial periods without proration policy
        return state=blocked rather than inventing an amount.
        """
```

DTO shapes match `schemas/dtos.schema.json`.

---

## 2. Consumed

### `AccessPort` — M01 (fake in standalone)

| Action | When |
|---|---|
| `transport.manage` | Create/patch bus and participation |
| `transport.read` | List participants, read participation/buses |
| `transport.bill` | Billing runs, reconciliation, adjustments, retry |

Scope facts: `{resource_school_id, subject_person_id?, relationship?,
effective_date?}`. Guardians/students read their own participation through
Fees statements in integrated mode; transport.read for self/linked-child only
when exposed here.

### `RegistryPort` — M02 (fake in standalone)

| Method | Use |
|---|---|
| `get_student` | Existence / school isolation / display name |
| `get_relationships` | Guardian/self reads |

Unused broad methods fail explicitly on the fake when called.

### `FeesPort` — M07 (FakeFees in standalone)

| Method | Use |
|---|---|
| `raise_charge` | Period billing with source_key dedupe |
| `credit_charge` | Explicit adjustment credits |
| `get_balance` | Optional preview; unused paths fail if called without seed |

FakeFees: commits then can time out; retry with same source_key returns the
original charge_id; exposes stored charges for reconciliation.

### `PlatformPort` — M14 (test adapter in standalone)

`record_audit` + `append_event` in the writing transaction.
`start_job` for billing runs (real local worker when broker enabled).

### `ClockPort`

Every timestamp. School civil dates derived via Asia/Kolkata.

---

## 3. Workflow (module-local)

1. Optionally create labelled buses (`Bus.active`).
2. Create participation with `fee_plan_id` (approved Fees plan reference).
3. Patch to set `to_date` / `bus_id` with `expected_version` + reason.
4. Billing run for `YYYY-MM` + `policy_version` → preview + queued job.
5. Job calls Fees via `request_period_charge`; records `BillingRequest`.
6. Lost response after Fees commit: retry same `source_key`; link `charge_id`.
7. Reconciliation lists missing charges, orphaned links, blocked, retryables.
8. AdjustmentRequest → Fees.credit_charge; never delete old invoices.
