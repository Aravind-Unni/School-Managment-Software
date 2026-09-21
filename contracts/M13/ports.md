# M13 service ports — proposed under school-contracts-v14 (pending freeze)

What M13 **provides** and what it **consumes**. M13 imports no other module's
ORM. Domain modules are reached only through adapter Protocols registered in
`backend/modules/exchange/adapters/`.

---

## 1. Provided: `ExchangePort` (to land in `backend/contracts/exchange.py` once frozen)

```python
@runtime_checkable
class ExchangePort(Protocol):
    """Reports, imports, exports. Owned by M13 exchange.

    Report snapshots bind publication revision ids immutably.
    Implementations must not accept browser-supplied ResourceGrant values.
    """

    def request_report(
        self,
        ctx,
        kind: str,
        source_refs: list[dict],
        locale: str,
        template_version: str,
    ) -> ReportJobStartDTO: ...

    def get_artifact(self, ctx, job_id) -> ArtifactAccessDTO: ...
```

DTO shapes match `schemas/dtos.schema.json`. HTTP routes in `openapi.json` are
the staff-facing surface; other modules (for example M05 publication) call
`request_report` for asynchronous PDF/CSV generation.

---

## 2. Consumed: `DomainExchangePort` (module-local adapter registry)

Each import/export dataset maps to one adapter under
`backend/modules/exchange/adapters/`. Adapters implement:

```python
@runtime_checkable
class DomainExchangePort(Protocol):
    """Validate, apply, and page export rows for one dataset family."""

    def validate_rows(self, ctx, rows) -> dict:
        """Returns {accepted: int, errors: [{row, field, code}]}."""

    def apply_rows(self, ctx, batch_key: str, rows) -> dict:
        """Returns {applied: int, errors: [{row, field, code}]}. Idempotent on batch_key."""

    def export_rows(self, ctx, dataset: str, filters: dict, cursor: str | None) -> dict:
        """Returns {schema_version: str, rows: list[dict], next_cursor?: str}."""
```

Registry resolves `(dataset, direction)` to an adapter instance. Direct ORM
imports from M02/M04/M05/M06/M07/M09 are forbidden.

---

## 3. Consumed foundation and domain ports

### `AccessPort` — M01 (fake in standalone)

| Action | When |
|---|---|
| `imports.validate` | Create import, poll job, list errors, read templates |
| `imports.commit` | Commit validated import (`Idempotency-Key` required) |
| `reports.read` | Read report snapshot metadata and download |
| `reports.export` | Create export, poll, download |
| `reportcards.generate` | Enqueue and poll report card jobs |

Scope facts include `{resource_school_id, subject_person_id?, relationship?,
effective_date?}`. Cross-school reads return **404**. Revoked guardian returns
**403** `exchange.error.artifact_access_revoked` on download.

### `RegistryPort` — M02

Enrolment and roster rows for `enrolments` import and `class_roster` export.

### `AssessmentPort` — M05

Published result revisions for `results` import and report cards; publication id
must match frozen revision ids.

### `AttendancePort` — M04

`attendance_summary` export rows.

### `PerformancePort` — M06

`progress`, `at_risk`, `subject_summary` export rows.

### `FeesPort` — M07

`get_balance` only when rendering fee lines on reports. **`raise` and `credit`
must fail explicitly in fakes** if invoked from exchange code paths.

### `FilesPort` — M12

| Method | When |
|---|---|
| `begin_upload` | Client uploads import CSV/XLSX |
| `get_status` | Confirm import file ready |
| `store_artifact` | Persist generated export/report bytes |
| `issue_read` | Mint short-lived download URL after access check |

### `PlatformPort` — M14

`record_audit` + `append_event` in the writing transaction.
`start_job` for validate, commit, export, and report-card workers.

### `ClockPort`

Every timestamp and signed URL expiry. School civil dates via Asia/Kolkata.

---

## 4. Workflow (module-local)

1. Staff uploads file via FilesPort → `POST /imports` validate job.
2. Worker parses CSV/XLSX, neutralizes formula cells (leading tab or
   apostrophe), calls domain `validate_rows`.
3. Principal commits with matching `source_digest` → domain `apply_rows` with
   idempotent batch key → `exchange.import_completed`.
4. Exports and report cards enqueue via PlatformPort; worker writes artifact via
   FilesPort → `exchange.report_ready` / optional `exchange.report_superseded`.
5. Download endpoints mint `ArtifactAccessDTO` only after Access + relationship
   checks.

Broker, worker, and object storage are **required** in non-standalone profiles.
