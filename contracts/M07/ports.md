# M07 service ports — FROZEN under school-contracts-v8

What M07 **provides** and what it **consumes**.

M07 imports no other module. Dependencies are Protocols from
`backend/contracts/ports.py`, bound to deterministic fakes in standalone.

---

## 1. Provided: `FeesPort`

```python
@runtime_checkable
class FeesPort(Protocol):
    """Single auditable fee ledger. Owned by M07."""

    def raise_charge(
        self,
        context: RequestContext,
        source_key: str,
        student_id: UUID,
        fee_head_id: UUID,
        amount_paise: int,
        due_date: date,
        description_key: str,
    ) -> ChargeDTO:
        """Post a charge keyed by school-unique source_key.

        Identical source_key + payload returns the existing charge. Changed
        payload on the same key raises StateConflict (409).
        """

    def credit_charge(
        self,
        context: RequestContext,
        charge_id: UUID,
        amount_paise: int,
        reason: str,
        source_key: str,
    ) -> CreditDTO:
        """Post an approved concession/credit against one charge."""

    def get_balance(
        self,
        context: RequestContext,
        student_id: UUID,
        as_of: date | None = None,
    ) -> BalanceDTO:
        """Return ledger totals for one student as of a school civil date."""
```

DTO shapes match `schemas/dtos.schema.json`. Until the shared Protocol is
approved, the concrete service lives at `modules.fees.services.port.FeesService`.

---

## 2. Consumed

### `AccessPort` — M01 (fake in standalone)

| Action | When |
|---|---|
| `fees.configure` | Create fee heads / plans |
| `fees.read` | Statements, balances, overdue list, receipt view |
| `fees.record_payment` | Manual payment posting |
| `fees.concede` | Post concession credits (+ 2FA when major) |
| `fees.reverse_payment` | Payment reversal (+ recent 2FA) |
| `fees.refund` | Explicit refund of credit (+ recent 2FA) |

Scope facts: `{resource_school_id, subject_person_id?, relationship?,
effective_date?}`. Finance sees borrower identity only — never academic
evidence. Guardians/students: `fees.read` for self/linked-child only.

### `RegistryPort` — M02 (fake in standalone)

| Method | Use |
|---|---|
| `get_student` | Existence / school isolation / display name on statements |
| `get_relationships` | Guardian/self statement reads |

Unused broad methods fail explicitly on the fake when called.

### `PlatformPort` — M14 (test adapter in standalone)

`record_audit` + `append_event` in the writing transaction for payments,
charges, reversals, refunds and major concessions.

### `ClockPort`

Every timestamp. School civil dates derived via Asia/Kolkata.

---

## 3. Workflow (module-local)

1. Configure fee heads and a versioned fee plan (schedule of head+amount+due).
2. Raise charges (API or `FeesPort.raise_charge`) with unique `source_key`.
3. Record manual payments with allocations; allocate remainder as overpayment credit.
4. Correct via reversal + replacement; refund available credit explicitly.
5. Statement/balance reads derive paid/outstanding/overdue from charges,
   allocations, credits and reversals — never float.
