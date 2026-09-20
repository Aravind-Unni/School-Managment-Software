# M06 review decisions

## Review outcome — APPROVED AS PROPOSED

**Reviewed by Abhinav M on 2026-09-20. Items 1–10 approved as proposed.**

Recorded in `contracts/revision.json` under revision `school-contracts-v7`.

| Item | Decision |
|---|---|
| 1 — event names | `performance.warning_opened` / `performance.intervention_reviewed` |
| 2 — PerformancePort | Add to `backend/contracts`; FakeAssessment + FakeAttendance in harness |
| 3 — API mount | `/api/v1/performance/...`, `/warning-rules`, `/warnings/...`, `/interventions`, `/meetings` |
| 4 — permissions | Five codes exactly as manual |
| 5 — mean metric | Baseline formula `simple_mean_v1` only; no CBSE grade scale invented |
| 6 — attendance % | Fake may return configured percentage + `policy_version`; incomplete ≠ low |
| 7 — topic analysis | `insufficient_data` when item tags absent; never infer gaps |
| 8 — warning lifecycle | open → acknowledged\|dismissed → closed; reopen via history; dedupe by rule+student+window |
| 9 — broker/worker | Real local broker+worker for projection rebuild/reconcile jobs |
| 10 — observations | Sensitive notes require `observations.read_sensitive`; absent from guardian export |

---

## Source identity

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m06/analytics-warnings-interventions` |
| Branched from | `abe35b7c4621df8b6ebf111293401e80b4b255a1` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v6` |
| Freeze revision | `school-contracts-v7` |

---

## Items needing an explicit yes / no

### 1 — Event type names

Manual: `WarningOpened.v1`, `InterventionReviewed.v1`. Frozen envelope uses
dotted snake names.

**Propose:** `performance.warning_opened`, `performance.intervention_reviewed`
(schema_version 1 on the envelope).

### 2 — Shared `PerformancePort` + harness fakes for Assessment/Attendance

M06 consumes Assessment and Attendance ports already frozen for M04/M05 owners.
Standalone must not import those ORM apps.

**Propose:** add `PerformancePort` + dashboard/intervention DTOs to
`backend/contracts`. Add `FakeAssessment` and `FakeAttendance` to
`FAKEABLE_PORTS` / `build_fake_registry`, validating the same request/response
shapes. Consumers declare `"assessment"` and `"attendance"`.

### 3 — API mount path

Packet template said `/api/performance/`. Manual and M02–M05 use `/api/v1/...`.

**Propose:** paths relative to `/api/v1` exactly as the manual seeds.

### 4 — Permission codes

**Propose:** `performance.read`, `warnings.manage`, `interventions.manage`,
`meetings.record`, `observations.read_sensitive`.

### 5 — Baseline metric formula

Manual seed: S1 scores 60/100 and 70/100 → 65 percent via simple mean. Do not
invent CBSE grade boundaries.

**Propose:** metric definition code `overall_mean` with
`formula=simple_mean_v1`, `denominator=100`. Incompatible policy versions are
never compared; dashboard labels the definition version.

### 6 — Attendance percentage vs incomplete

Manual: distinguish incomplete attendance from low attendance; require sample
minimums. Fake Attendance for baseline: S1 eligible=10, present=8 → 80% with
`policy_version=period_present_over_eligible_v1`. S2 missing inputs → no
percentage / incomplete warning path, not low-attendance.

### 7 — Topic / skill analysis

**Propose:** when tagged item-level data is absent, metrics carry
`status=insufficient_data` and no advice text. Never infer learning gaps from
totals.

### 8 — Warning lifecycle and dedupe

**Propose:** states `open|acknowledged|dismissed|closed`. Acknowledge/dismiss
require `reason` + `expected_version`. Same rule+student+window+source fingerprint
does not open a duplicate while one is open/acknowledged. History retained on
dismiss.

### 9 — Projection worker

**Propose:** `module.json` enables broker+worker. Job kind
`performance.rebuild_projections`. Daily reconcile + full rebuild supported.
Eager-only mode must not claim crash/retry coverage.

### 10 — Observations and guardian export

**Propose:** `Observation.visibility` / `kind` gate sensitive notes. Guardian
and student dashboard/export omit restricted observations even when
`performance.read` is granted for own-child academic summaries.

---

## Explicitly not decided here

- Real CBSE grading scales or report-card layout (use opaque definition versions).
- Real M01 2FA integration (FakeAccess step-up stays pending).
- Rebuild against live M04/M05 providers (PENDING integration).
