# M04 review decisions — AWAITING REVIEW

Writing a proposal is not approving it. Every row below needs a named reviewer and
a date before `contracts/M04` is added to `contracts/revision.json` and hashed into
the manifest. **Do not implement the module until that freeze happens.**

Source identity this proposal was produced against:

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m04/teacher-attendance` |
| Branched from | `fd7751dbbeddfbcd3a526ad244a6e8fe0638a892` (`origin/main`, M03 merged) |
| Manifest revision | `school-contracts-v4`, status `reviewed`, 27 frozen entries |
| M04 manifest status | `not_started` before this proposal |
| Foundation check | `dev.py check M00 --suite contracts` passed |
| `dev.py doctor` | ok on this machine (modules listed; stack not started) |

---

## Decisions requested

### 1. Event names vs frozen envelope

Packet: `AttendanceSubmitted.v1`, `AttendanceCorrected.v1`. Frozen
`event-envelope.schema.json` requires `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`.

**Proposed:** emit `attendance.submitted` and `attendance.corrected` (same
conform decision as M03). Mapping recorded in `schemas/events.schema.json`.

**Alternative:** revise the shared envelope — out of scope for M04 alone.

### 2. Add `TimetablePort` + DTOs and `AttendancePort` to `backend/contracts`

M03 deferred `TimetablePort` until a consumer existed. M04 is that consumer and
cannot import `modules.timetable`.

**Proposed (additive shared revision when freezing M04):**

- Add `TimetablePort` and move/copy `PeriodSessionDTO`, `CalendarDayDTO`,
  `TeachingAuthorityDTO` into `backend/contracts` (owned shapes, no ORM).
- Add `AttendancePort` + `AttendanceSummaryDTO`.
- Add `FakeTimetable` under `backend/shared/fakes/`.

**Alternative:** keep a duplicate Protocol only inside M04 — rejected; two
consumers would diverge.

### 3. Baseline cast: English subject + T3 vs frozen shared fixtures

Packet wants P1 Mathematics / P2 English, T3 substitute, S1+S2 on both, plus an
elective outsider. Shared fixtures have maths+malayalam, T1+T2 only, and S2
**not** enrolled in maths (M03 relies on that asymmetry).

**Proposed:**

- Additive labels `SUBJECT_ENGLISH` and `TEACHER_T3` in shared fixtures (or
  M04 seed uuid5s with the same labels).
- M04 standalone FakeRegistry **overlay**: S1+S2 enrolled in maths+english; S3
  maths-only (elective outsider for P2). Do **not** change the default
  `SUBJECT_ENROLMENTS` table M03 tests use.
- P2 uses English (not Malayalam) so M03's S2/malayalam asymmetry stays intact.

### 4. Writable status on save vs `unmarked`

Packet lists statuses including `unmarked`. Untouched entries must not become
present.

**Proposed:** `unmarked` is the default row state and a summary bucket only.
Save/submit bodies accept only `present|absent|late|excused`. Submitting with
any roster pupil still `unmarked` is `422 attendance.error.incomplete_roster`.

### 5. Recent 2FA on corrections

Packet: scoped correction privileges are separate and audited; marking/submit
need assignment + Access. It does not explicitly require step-up for corrections.

**Proposed:** `attendance.correct` requires `require_recent_2fa` (300s), matching
other sensitive audited writes. Mark/submit do **not** require step-up in
standalone (real auth pending M01 integration).

**Alternative:** no step-up on correct until school policy says so.

### 6. Percentage calculation version

Packet: configured summary calculation is separate; return counts even when
percentage unavailable; do not invent late/excused weights.

**Proposed:** `percentage` and `policy_version` always `null` in this module
until a future reviewed config exists. No default formula ships with M04.

### 7. Reconciliation API surface

Packet requires 409 with reconciliation when snapshots go stale, and audited
reconciliation that updates eligibility without deleting history.

**Proposed for this freeze:** stale create/save/submit returns
`409 attendance.error.roster_stale` (or `assignment_stale` /
`period_not_eligible`). A dedicated `POST .../reconcile` endpoint is **deferred**
to a follow-up contract revision; standalone tests assert preservation of
submitted rows when the fake reports cancellation after submit, via service-level
reconciliation helpers covered in step 3. Browser API for reconcile is not in
the six packet paths.

**Ask:** approve deferral, or require an explicit reconcile path in this freeze.

### 8. Permission codes

Packet: `attendance.mark/submit/correct/read`.

**Proposed:** exactly those four strings as Access actions. No finer verbs in
v1.

### 9. `api_prefix` in PACKET vs `/api/v1`

ModuleRegistration table in PACKET.md says `/api/attendance/`; public API says
paths relative to `/api/v1`.

**Proposed:** browser paths under `/api/v1/attendance/...` as in OpenAPI;
registration `api_prefix` = `/api/v1/attendance/` for the router mount.

---

## Artefacts in this proposal

| Path | Contents |
|---|---|
| `openapi.json` | 6 operations |
| `schemas/dtos.schema.json` | Closed DTOs |
| `schemas/events.schema.json` | Both event payloads |
| `error-codes.json` | HTTP × code × message_key rows |
| `ports.md` | Provided + consumed signatures |
| `fixtures/scenario.json` | Baseline synthetic cast |
| `fixtures/expected-results.json` | A1–A17 + P1–P4 PENDING |
| `fixtures/responses.json` | Consumer response examples |

---

## Reply needed

Approve as proposed, or list item numbers to change. After approval, the next
commit freezes via `contracts/revision.json` + `contract_manifest.py --update`,
then implementation step 1 starts.
