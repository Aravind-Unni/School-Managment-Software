# M14 review decisions

## Review outcome — APPROVED AS PROPOSED

**Reviewed against Development Manual v3.1 (M14 packet) supplied in the module
task.** Items 1–16 approved as proposed for freeze under `school-contracts-v15`.
Reviewer of record for this freeze: Abhinav M (task owner / collaborator pattern
matching M02–M13). Peer review of the implementation PR remains separate.

| Item | Decision |
|---|---|
| 1 — API mount | REST under `/api/v1` with path roots `health/`, `jobs/`, `audit/`, `operations/`; foundation `/healthz` + `/readyz` kept |
| 2 — permissions | `platform.read_health`, `jobs.read`, `jobs.retry`, `audit.read`, `backups.manage` |
| 3 — PlatformPort shape | Keep frozen `record_audit` / `append_event` / `enqueue`; ergonomic facades module-local |
| 4 — start_job | Job aggregate + idempotency; `enqueue` creates Job on real M14 |
| 5 — AuditRecord wire | Common schema unchanged; public DTO maps `aggregate_id` / `redacted_diff` |
| 6 — health auth | `health/live` public; `health/ready` needs `platform.read_health` |
| 7 — job retry | Failed/dead only; **202**; cross-school **404** |
| 8 — audit list | Cursor pagination; redaction; privileged raw deferred to ops fixture |
| 9 — restore rehearsal | Ops identity + isolated target only; never production overwrite |
| 10 — outbox / receipts | At-least-once; dedupe `(consumer, event_id)`; no receipt event storms |
| 11 — infrastructure events | `platform.job_state_changed`, `platform.restore_rehearsal_verified` only |
| 12 — ModuleRegistration | Host wiring; no private ORM exposure |
| 13 — standalone deps | Fake Access; **no FakePlatform**; broker+worker+object storage required |
| 14 — object storage | `module.json` `object_storage: true` |
| 15 — real M01 auth | **PENDING** |
| 16 — full-scale RPO/RTO | **PENDING** |

---

## Source identity

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m14/platform-audit-jobs-backup` |
| Branched from | `a2f16c24dc6a7c7004e5358a094f0bd0fc5760dd` (`origin/main`) |
| Freeze revision | `school-contracts-v15` |
| Freeze commit | (recorded after freeze commit) |
