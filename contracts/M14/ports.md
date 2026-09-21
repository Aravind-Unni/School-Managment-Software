# M14 service ports — proposed under school-contracts-v15 (pending freeze)

What M14 **provides** and what it **consumes**. M14 imports no other business
module's ORM. Other modules reach Platform only through frozen `PlatformPort`.

---

## 1. Provided: frozen `PlatformPort` (already in `backend/contracts/ports.py`)

```python
@runtime_checkable
class PlatformPort(Protocol):
    """Audit, outbox and background jobs. Owned by M14 platform.

    Both writes MUST join the caller's open database transaction so that a
    rollback removes them.
    """

    def record_audit(self, record: AuditRecord) -> None: ...
    def append_event(self, event: EventEnvelope) -> None: ...
    def enqueue(self, task_path: str, *, payload: dict[str, object]) -> str: ...
```

M14 binds the **real** implementation (not `TestPlatformAdapter`). Real
`enqueue` creates a `Job` row (idempotent on school + kind + idempotency_key
when supplied in payload) and schedules broker work.

### Ergonomic facade (module-local, matches Development Manual wording)

```python
def record_audit(ctx, action, aggregate_id, redacted_diff) -> UUID: ...
def append_event(ctx, event_type, aggregate_id, aggregate_version, payload) -> UUID: ...
def start_job(ctx, kind, idempotency_key, payload_ref) -> StartJobResultDTO: ...
def register_module(registration: ModuleRegistration) -> None: ...
```

These construct frozen `AuditRecord` / `EventEnvelope` / Job rows and call the
port. They are not a second public Protocol in `backend/contracts` unless a
later revision adds them.

DTO shapes match `schemas/dtos.schema.json`.

---

## 2. Consumed foundation ports

### `AccessPort` — M01 (fake in standalone)

| Action | When |
|---|---|
| `platform.read_health` | Authenticated readiness |
| `jobs.read` | Get job |
| `jobs.retry` | Retry failed/dead job |
| `audit.read` | List audit |
| `backups.manage` | Restore rehearsal (+ recent 2FA) |

Cross-school resource ids return **404**. Company-ops identity required for
restore rehearsals (`platform.error.ops_identity_required`).

### `ClockPort`

Every timestamp. School civil dates via Asia/Kolkata where needed for reports.

### Object storage (M12 port or harness private store)

Pinned object versions for `BackupManifest` and restore hash comparison.
Standalone uses the real local object store from Compose, not unfinished M12 ORM.

---

## 3. Owned aggregates (not exported as ORM)

| Aggregate | Notes |
|---|---|
| AuditRecord | Append-only to application roles; same transaction as write |
| OutboxEvent | Pending → dispatched; at-least-once |
| ConsumerReceipt | Dedupe `(consumer, event_id)` |
| Job | Mutable `version`; sanitized errors on read |
| BackupManifest | db_point + object_versions + verified_at |
| ModuleRegistration | Host wiring only; no private model exposure |

---

## 4. Workflow

1. Domain service opens transaction → `record_audit` + `append_event` → commit.
2. Dispatcher reads committed outbox → delivers at-least-once → consumer writes
   receipt with side effect.
3. Rollback before commit ⇒ no audit row, no dispatched event.
4. Duplicate delivery ⇒ one effect via ConsumerReceipt.
5. Worker crash between attempts ⇒ job resumes; retry API for failed/dead.
6. Restore rehearsal restores to isolated target and compares hashes/counts.

Broker, worker, and object storage are **required** for standalone M14.
