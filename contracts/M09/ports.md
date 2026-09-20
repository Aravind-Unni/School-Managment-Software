# M09 service ports — proposed under school-contracts-v10

What M09 **provides** and what it **consumes**.

M09 imports no other module. Dependencies are Protocols from
`backend/contracts`, bound to deterministic fakes in standalone.

---

## 1. Provided: `LibraryPort`

```python
@runtime_checkable
class LibraryPort(Protocol):
    """Open-loan and availability lookup. Owned by M09."""

    def get_open_loans(
        self,
        context: RequestContext,
        person_id: UUID,
    ) -> list[OpenLoanView]:
        """Return open loans for person_id in the actor school.

        Each item: loan_id, copy_id, due_date, overdue (school civil date).
        Raises ObjectInaccessible when person is other-school or denied.
        """

    def get_availability(
        self,
        context: RequestContext,
        title_id: UUID,
    ) -> AvailabilityView:
        """Return {available, total} copy counts for a title.

        available = copies in state available. total excludes withdrawn.
        Raises ObjectInaccessible when title absent or other-school.
        """
```

DTO shapes match `schemas/dtos.schema.json`.

---

## 2. Consumed

### `AccessPort` — M01 (fake in standalone)

| Action | When |
|---|---|
| `library.catalogue.manage` | Create/update titles, copies, imports, copy adjustments |
| `library.issue` | Issue loan |
| `library.return` | Return loan |
| `library.renew` | Renew loan |
| `library.read_overdues` | Overdue queue |
| `library.read_own` | Student/guardian own loans + permitted availability |

Scope facts: `{resource_school_id, subject_person_id?, relationship?,
effective_date?}`. Fake Access defaults deny; fixture grants separate librarian
vs student. Stale 2FA simulated when a rule requires it (baseline: not required).

### `RegistryPort` — M02 (fake in standalone)

| Method | Use |
|---|---|
| `get_student` | Borrower identity / school isolation / display name |
| `get_relationships` | Guardian/self loan reads |

Unused broad methods fail explicitly on the fake when called.

### `PlatformPort` — M14 (test adapter in standalone)

`record_audit` + `append_event` in the writing transaction.

### `ClockPort`

Every timestamp. School civil dates via Asia/Kolkata. Standalone freezes the
clock for overdue boundary tests.

---

## 3. Workflow (module-local)

1. Create Title; create Copy with unique accession_no (state=available).
2. Issue: lock copy; require available + no open loan; create Loan; set on_loan;
   audit + `library.loan_issued`.
3. Return: idempotent close; restore available or lost/damaged; audit +
   `library.loan_returned`.
4. Renew: append Renewal; bump due_date + version; enforce fixture renewal limit.
5. Overdues: paginated open loans with due_date < as_of; emit overdue_detected
   when first observed overdue.
6. Adjust copy (lost/damaged/withdrawn) with reason + actor.
7. Catalogue import: review duplicates; no silent merge.
