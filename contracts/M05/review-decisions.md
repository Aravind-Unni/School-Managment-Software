# M05 review decisions

## Review outcome — APPROVED

**Reviewed by Abhinav M on 2026-09-20. All eleven items approved as proposed.**

Recorded in `contracts/revision.json` and frozen under revision
`school-contracts-v6`.

| Item | Decision |
|---|---|
| 1 — event names | Conform: `assessment.results_published` / `result_revised` / `assignment_submission_changed` |
| 2 — FilesPort | Add `FilesPort` + file DTOs to `backend/contracts`; FakeFiles in standalone |
| 3 — API mount | `/api/v1/assessments/...` and `/api/v1/results/...` |
| 4 — permissions | Seven codes as proposed |
| 5 — grade policy | Opaque `policy_version`; `grade` null until school rules |
| 6 — marking_outcome | scored|absent|exempt|oral|practical; absent ≠ 0 |
| 7 — 2FA | publish + reopen only |
| 8 — distinct approver | Off in baseline; policy flag available |
| 9 — Platform jobs | Use existing `enqueue` |
| 10 — assignments | type includes assignment; baseline written_test |
| 11 — evidence identity | M05 bindings use file_id/version/sha256; do not rewrite frozen EvidenceRef |

---

## The proposal, as reviewed

Source identity this proposal was produced against:

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m05/assessments-grades` |
| Branched from | `619e933a331c69d5262945dcc297142672e39e2d` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v5` |
| Proposed freeze revision | `school-contracts-v6` (only after approval) |

---

## Items needing an explicit yes / no

### 1 — Event type names

Manual names `ResultsPublished.v1`, `ResultRevised.v1`,
`AssignmentSubmissionChanged.v1`. Frozen envelope uses dotted snake names
(`attendance.submitted`).

**Propose:** `assessment.results_published`, `assessment.result_revised`,
`assessment.assignment_submission_changed` (schema_version 1 on the envelope).

### 2 — Shared `FilesPort` (additive to `backend/contracts`)

Manual requires Files begin_upload / get_status / confirm_quality / pin_evidence /
issue_read / store_artifact. Foundation today only has thin `ObjectStoragePort`
(put + signed_read_url). M12 is not started.

**Propose:** add `FilesPort` + `FileDTO` / `UploadSession` / file-oriented
`EvidenceRef{file_id,version,sha256}` to `backend/contracts` (owned by M12).
Standalone binds `FakeFiles` validating the same schemas. Keep existing
`ObjectStoragePort` unchanged (M12 may later wrap both). M05 never imports
M12 ORM.

Alternative rejected locally: stretch `ObjectStoragePort` — it cannot express
quality confirmation or versioned pin without a silent contract rewrite.

### 3 — API mount path

Packet template says `/api/assessment/`. Manual and M02–M04 use `/api/v1/...`.

**Propose:** `/api/v1/assessments/...` and `/api/v1/results/...` as in the
manual seeds.

### 4 — Permission codes

Manual: `assessment.manage`; `marks.edit` / `marks.submit`; `results.approve` /
`results.publish` / `results.reopen`; `evidence.view`.

**Propose:** exactly those seven strings. Teachers need assignment-scoped
Access fixtures for section+subject; students/guardians get `evidence.view` /
published-result reads only for self/linked-child after publication.

### 5 — Grade / CBSE policy

Manual forbids inventing CBSE weighting, pass marks, or rounding.

**Propose:** `GradePolicy` is referenced only by opaque `policy_version` string.
Baseline seed uses illustrative `policy_version="illustrative-v0"` with a single
component (max 100, weight 1.0). Letter `grade` on ResultDTO is **nullable** and
stays null until the school supplies approved boundary rules. No pass/fail
computation in M05 until that data exists.

### 6 — Result status vs mark absence

**Propose:** Result `status` enum:
`draft | submitted | approved | published | reopened` for workflow; separate
marking outcome field `marking_outcome`:
`scored | absent | exempt | oral | practical` (default `scored`).
`absent` / `exempt` are **not** score `"0.00"`. Score required only when
`marking_outcome=scored`. Written work with `scored` requires reviewed evidence
before submit/approve/publish.

### 7 — 2FA step-up

**Propose:** `Access.require_recent_2fa` (300s) on `results.publish` and
`results.reopen` only. Marking, evidence bind, submit, approve do not require
step-up in standalone (real M01 integration remains PENDING).

### 8 — Author / approver separation

Manual: policy decision.

**Propose:** default **not** enforced in baseline (same actor may submit and
approve). Optional `GradePolicy.rules.require_distinct_approver` boolean; when
true, approve by the marks author is 422. Baseline seed leaves it false.

### 9 — Platform job API

Manual `Platform.start_job` → `{job_id,state}`. Shared port today is
`PlatformPort.enqueue(...) -> str`.

**Propose:** M05 calls existing `enqueue`; publication response `report_job_id`
is that return value. No shared Protocol change. Report PDF generation is an
owned async job kind `assessment.report_snapshot` with FakePlatform capturing
the enqueue; real worker crash/retry PENDING until broker integration.

### 10 — Assignments surface

Owned records include Assignment(due_at) and Submission.

**Propose:** Assessment `type` enum includes `assignment | written_test |
practical | project`. When `type=assignment`, `due_at` is required on create;
Submission state is tracked and emits
`assessment.assignment_submission_changed`. Baseline seed is `written_test`
(no due_at). Internal service `get_assignment_summary` returns counts for
assignment-type rows only.

### 11 — Evidence file identity vs frozen EvidenceRef

Frozen `EvidenceRef` uses `evidence_id` + `storage_key`. Manual pin uses
`file_id` + `canonical_version` + `sha256`.

**Propose:** M05 stores `EvidenceBinding` with `file_id`, `file_version`,
`sha256`, `page_no`. Public ResultDTO `evidence_refs` use
`{file_id,version,sha256,page_no,binding_id}`. Mapping to M12 storage keys is
FilesPort's concern. Do **not** rewrite frozen `contracts.evidence.EvidenceRef`
in this revision; FilesPort returns its own pin DTO.

---

## Out of scope / PENDING integration (record in handoff, not blockers for freeze)

- Real compression acceptance and quality review (M12)
- Signed file reads against real object storage
- Report PDF snapshot contents
- Guardian relationship revocation mid-publication window
- Real M01 session/TOTP (standalone uses synthetic persona)

---

## Approval checklist for the reviewer

- [ ] Items 1–11 accepted as proposed, or named alternatives recorded here
- [ ] Artefacts under `contracts/M05/` match the accepted decisions
- [ ] Freeze: set module status `frozen`, hash artefacts, bump
  `contracts/revision.json` to `school-contracts-v6`, name reviewer + date
- [ ] Only then may Developer B implement steps 1–4
