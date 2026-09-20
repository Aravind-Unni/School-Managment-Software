# M10 service ports — proposed under school-contracts-v11

What M10 **provides** and what it **consumes**.

M10 imports no other module. Dependencies are Protocols from
`backend/contracts`, bound to deterministic fakes in standalone.

---

## 1. Provided: `AlumniPort`

```python
@runtime_checkable
class AlumniPort(Protocol):
    """Alumni profile lookup and candidate creation. Owned by M10."""

    def get_profile(
        self,
        context: RequestContext,
        student_id: UUID,
    ) -> AlumniProfileView:
        """Return approved profile contact view for student_id in actor school.

        Raises ObjectInaccessible when absent, other-school, or denied.
        Does not return editable grade or transcript fields.
        """

    def create_candidate(
        self,
        context: RequestContext,
        student_id: UUID,
        leaving_event_id: UUID,
        outcome: str,
    ) -> CreateCandidateResult:
        """Idempotent candidate for (student_id, leaving_event_id).

        Duplicate leaving_event_id returns the existing candidate id/state.
        Does not auto-create a public directory profile.
        """
```

DTO shapes match `schemas/dtos.schema.json` (`AlumniProfileView`,
`CreateCandidateResult`).

---

## 2. Consumed

### `AccessPort` — M01 (fake in standalone)

| Action | When |
|---|---|
| `alumni.review` | List candidates; approve/exclude |
| `alumni.manage` | Patch contact fields/preferences (staff) |
| `alumni.read` | Directory search |
| `alumni.export` | Create export job |
| `alumni.contact_self` | Own-profile contact edit when alumni login policy on |

Scope facts: `{resource_school_id, subject_person_id?, relationship?,
effective_date?}`. Fake Access defaults deny. Former parent/teacher grants do
not expand into alumni directory access. Stale 2FA simulated when a rule
requires it (baseline: not required for these actions).

### `RegistryPort` — M02 (fake in standalone)

| Method | Use |
|---|---|
| `get_student` | Departing pupil snapshot / school isolation / display |

Unused broad methods fail explicitly on the fake when called.

### `PlatformPort` — M14 (test adapter in standalone)

`record_audit` + `append_event` in the writing transaction.
`start_job` for alumni export (kind `alumni.export`). Fake Platform can
redeliver synthetic `StudentLeft` payloads for candidate ingestion tests.
Real exchange-backed export delivery is PENDING (M13).

### `ClockPort`

Every timestamp. School civil year via Asia/Kolkata when deriving leaving_year
from an event instant. Standalone freezes the clock.

---

## 3. Workflow (module-local)

1. Consume `StudentLeft` once per `leaving_event_id` → `AlumniCandidate`
   (state=pending). Duplicate delivery is a no-op returning the same candidate.
2. Reviewer approve `include=true` → `AlumniProfile` + leaving snapshot fields
   only + `alumni.profile_approved`. `include=false` → candidate excluded.
3. Transfer with `transfer_include_as_alumni=null` stays pending (no invented
   school policy).
4. Contact patch with `expected_version`; preference withdrawal audited +
   `alumni.contact_preference_changed`; blocks campaign selection.
5. Export: reject ungranted fields; `Platform.start_job`; audit; expire/log via
   job payload (exchange PENDING).
