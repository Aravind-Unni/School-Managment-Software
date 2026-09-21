# M12 review decisions

## Review outcome — APPROVED AS PROPOSED

**Reviewed by Abhinav M on 2026-09-21. Items 1–11 approved as proposed.**

Recorded in `contracts/revision.json` under revision `school-contracts-v13`.

| Item | Decision |
|---|---|
| 1 — event names | `files.candidate_ready` / `files.accepted` / `files.rejected` / `files.source_purged` |
| 2 — API prefix | `/api/v1/uploads`, `/api/v1/files/...` |
| 3 — ResourceGrant | Keep foundation shape; map file→`resource_id`; version checked at read/pin |
| 4 — FilesPort | Keep existing six methods; complete/reprocess/retention are HTTP/service helpers |
| 5 — permissions | `files.upload`, `files.review_quality`, `files.read`, `files.retention.manage` |
| 6 — retention | Economical fixture: confirm + backup verify + 7-day grace + no hold |
| 7 — image allowlist | JPEG/PNG/WebP; HEIC/PDF-as-image rejected; animation/bomb quarantined |
| 8 — worker | Broker+worker enabled for compress/purge/orphan jobs |
| 9 — 2FA | Retention manage requires recent 2FA; FakeAccess simulates; real M01 PENDING |
| 10 — dedup | Canonical bytes within school only; no hash-lookup API |
| 11 — shared contracts | No `backend/contracts` change; FilesPort already frozen via M05 |

Deferred: Assessment publication gates, independent backup restoration,
production object lifecycle rules, real M01 auth/2FA.

---

## Source identity

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m12/compressed-answer-sheet-files` |
| Branched from | `c3ece552164f4d7b99c8f688903f3892ecfeaeac` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v12` |
| Freeze revision | `school-contracts-v13` |
