# M10 review decisions

## Review outcome — APPROVED AS PROPOSED

**Reviewed by Abhinav M on 2026-09-21. Items 1–14 approved as proposed.**

Recorded in `contracts/revision.json` under revision `school-contracts-v11`.

| Item | Decision |
|---|---|
| 1 — event names | `alumni.profile_approved` / `alumni.contact_preference_changed` (dotted snake; maps manual AlumniProfileApproved.v1 / AlumniContactPreferenceChanged.v1; envelope `schema_version`=1) |
| 2 — AlumniPort | `get_profile`, `create_candidate` in `backend/contracts/alumni.py` |
| 3 — API mount | `/api/v1/alumni/...` |
| 4 — permissions | `alumni.review`, `alumni.manage`, `alumni.read`, `alumni.export`, `alumni.contact_self` |
| 5 — 2FA | Not required in baseline; real M01 step-up PENDING |
| 6 — outcomes | `graduate`, `transfer` only |
| 7 — candidate states | `pending`, `approved`, `excluded` |
| 8 — transfer policy | Fixture `transfer_include_as_alumni=null` → transfer stays pending; do not invent production policy |
| 9 — uniqueness | Unique `(school_id, student_id, leaving_event_id)` |
| 10 — snapshot | last_standard, leaving_year, outcome, display/admission only; no grades/transcripts |
| 11 — contact fields | Optional `email`, `phone`, `postal_address` only |
| 12 — purposes/channels | purposes `alumni_notice`/`directory`; channels `email`/`sms`/`postal`/`phone` |
| 13 — alumni login | Fixture `alumni_login_enabled=false`; `contact_self` denied until policy on |
| 14 — export | Granted fields from fixture; reject others with `alumni.error.export_field_not_granted`; job via `Platform.start_job` |

Deferred / PENDING integration: real StudentLeft from Registry, account lifecycle
(Access), exchange-scoped export delivery (M13), real M01 auth/2FA.

---

## Source identity

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m10/alumni-records-contact-permissions` |
| Branched from | `3ae3f8cbc25e09d04cb9a409411072cd6fd9a1bc` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v10` |
| Freeze revision | `school-contracts-v11` |
