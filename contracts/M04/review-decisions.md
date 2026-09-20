# M04 review decisions

## Review outcome — APPROVED

**Reviewed by Abhinav M on 2026-09-20. All nine items approved as proposed,
with the explicit condition that item 7 must not become a functional stub:**
reconciliation behaviour (preserve submitted history, audit reason, refresh
derived eligibility) is required; only the dedicated `POST .../reconcile`
browser path is deferred.

Recorded in `contracts/revision.json` and frozen under revision
`school-contracts-v5`.

| Item | Decision |
|---|---|
| 1 — event names | Conform: `attendance.submitted` / `attendance.corrected` |
| 2 — shared ports | Add `TimetablePort`, `AttendancePort` and DTOs to `backend/contracts` |
| 3 — baseline cast | Additive `SUBJECT_ENGLISH` + `TEACHER_T3`; M04 FakeRegistry overlay |
| 4 — unmarked | Not writable on save; incomplete roster → 422 on submit |
| 5 — 2FA | Recent 2FA on `attendance.correct` only |
| 6 — percentage | Always null until a future calculation version |
| 7 — reconcile HTTP | Deferred path only; service reconciliation is real |
| 8 — permissions | `attendance.read/mark/submit/correct` |
| 9 — API mount | `/api/v1/attendance/...` |

---

## The proposal, as reviewed

(Unchanged from the proposal text below; the outcome is recorded above.)

Source identity this proposal was produced against:

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m04/teacher-attendance` |
| Branched from | `fd7751dbbeddfbcd3a526ad244a6e8fe0638a892` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v4` |
| Freeze revision | `school-contracts-v5` |

See the remainder of the original nine decision write-ups in git history at
commit `63a222c` if needed; they are not repeated here to avoid drift between
proposal and freeze record.
