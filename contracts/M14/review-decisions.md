# M14 review decisions — PROPOSED (awaiting freeze)

**Status:** contract artefacts are proposed under this packet. **Do not implement
until a named reviewer freezes them in `contracts/manifest.json`.**

Branched from `a2f16c24dc6a7c7004e5358a094f0bd0fc5760dd` (`origin/main`).
Manifest revision at proposal: `school-contracts-v14`.
Proposed freeze revision: `school-contracts-v15`.

| Item | Decision (proposed) | Alternatives rejected |
|---|---|---|
| 1 — API mount | REST under `/api/v1` with path roots `health/`, `jobs/`, `audit/`, `operations/` (matches manual “paths relative to /api/v1”). Keep foundation `/healthz` + `/readyz` for container probes; they are not replaced. | PACKET’s `/api/platform/` rejected — manual and M02–M13 use shared `/api/v1`. |
| 2 — permissions | Exact manual codes: `platform.read_health`, `jobs.read`, `jobs.retry`, `audit.read`, `backups.manage`. Owned prefixes: `platform.`, `jobs.`, `audit.`, `backups.`. | PACKET’s “all `platform.<verb>_<noun>`” would rename manual codes. |
| 3 — PlatformPort shape | **Keep frozen** `backend/contracts` `PlatformPort`: `record_audit(AuditRecord)`, `append_event(EventEnvelope)`, `enqueue(task_path, payload) -> job_id`. Real M14 binds these; no silent signature change. | Manual’s `record_audit(ctx,…)->audit_id` / `start_job(…)` stay as **ergonomic facades** inside M14 (and existing M01 `PlatformFacade`), mapping onto the frozen port + Job row. |
| 4 — start_job | HTTP/job aggregate uses `Job(kind, school_id, actor_id, payload_ref, state, progress, error_code, idempotency_key)`. `enqueue` on real M14 creates/upserts that Job. Idempotent on `(school_id, kind, idempotency_key)`. | Adding `start_job` to frozen PlatformPort deferred — shared contract revision if later needed. |
| 5 — AuditRecord wire | Common frozen schema stays: `resource_id`, `before`, `after`. Public `GET /audit` DTO exposes `aggregate_id` (= `resource_id`) and `redacted_diff` (= server-redacted `{before, after}`). Secrets/tokens/image blobs never leave redaction. | Renaming common AuditRecord fields rejected (would break every consumer). |
| 6 — health auth | `GET /api/v1/health/live` is **public** (liveness only). `GET /api/v1/health/ready` requires `platform.read_health` and returns database / queue / file-processor readiness without credentials or connection strings. | Unauthenticated detailed readiness rejected. |
| 7 — job retry | `POST /jobs/{id}/retry {reason}` requires `jobs.retry`. Replays preserving business idempotency key; only `failed` (and optionally `dead`) jobs. Returns **202** with JobDTO. Cross-school job id → **404**. | Allowing retry of `succeeded` jobs rejected. |
| 8 — audit list | `GET /audit` requires `audit.read`. Cursor pagination; filters: `action`, `actor_id`, `aggregate_id`, `occurred_from`, `occurred_to`. Privileged raw `before`/`after` only when actor also has company-ops emergency access fixture (standalone: explicit persona); school admins see redacted only. | Offset pagination rejected. |
| 9 — restore rehearsal | `POST /operations/restore-rehearsals` requires `backups.manage` + company-ops identity (not a school-created role). Always targets an **isolated** restore database/bucket; never overwrites production. Returns **202** then report with verified hashes/counts. | Implicit production overwrite rejected. |
| 10 — outbox / receipts | `OutboxEvent` + `ConsumerReceipt(consumer, event_id)` owned by M14. At-least-once dispatch; dedupe key `(consumer, event_id)` committed with side effect where possible. Receipts **must not** emit recursive unlimited platform events. | Global ordering promise rejected. |
| 11 — infrastructure events | Allowlisted only: `platform.job_state_changed`, `platform.restore_rehearsal_verified`. No event storms from delivery receipts. | Emitting an event per receipt rejected. |
| 12 — ModuleRegistration | Host already loads `ModuleRegistration`; M14’s `register_module` wires routes, nav, permission catalogue, consumers, migrations, health — **does not** expose private ORM models. | Self-install by import side-effect rejected. |
| 13 — standalone deps | Fake Access (deny-by-default) for operational endpoints. **No FakePlatform** — M14 binds real implementation. Sample producer/consumer exercises real audit/outbox/jobs. Broker + worker + object storage **required** (`module.json`). | Eager-only worker crash claims rejected. |
| 14 — object storage | `dev/modules/M14/module.json` resources: `object_storage: true` (backup object versions + restore rehearsal). | Leaving false would block acceptance. |
| 15 — real M01 auth / ops SSO | **PENDING** until Section C. Standalone uses synthetic personas + FakeAccess fixtures. | |
| 16 — production RPO/RTO / full-scale load | **PENDING** — document hypotheses only; not claimed as verified in standalone. | |

Deferred outside this freeze: Kubernetes, inventing school policy, real domain job kind catalogue beyond sample producer, production monitoring dashboards against live multi-module traffic.

---

## Source identity

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m14/platform-audit-jobs-backup` |
| Branched from | `a2f16c24dc6a7c7004e5358a094f0bd0fc5760dd` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v14` |
| Proposed freeze revision | `school-contracts-v15` |
