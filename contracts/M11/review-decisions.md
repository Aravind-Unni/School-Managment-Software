# M11 review decisions

## Review outcome — APPROVED AS PROPOSED

**Reviewed by Abhinav M on 2026-09-21. Items 1–18 approved as proposed.**

Recorded in `contracts/revision.json` under revision `school-contracts-v12`.

| Item | Decision |
|---|---|
| 1 — event names | `communications.notice_published` / `communications.delivery_status_changed` |
| 2 — CommunicationsPort | `enqueue` → `DeliveryDTO` in `backend/contracts/communications.py` |
| 3 — NotificationPort | Docstring revised: fire-and-forget; idempotent path is `CommunicationsPort.enqueue` |
| 4 — SmsProviderPort | Module-local only |
| 5 — API mount | `/api/v1/notices`, `/messages`, `/deliveries/{id}`, `/sms/callback/{provider}` |
| 6 — permissions | `notices.create/publish`, `messages.send/read_status`, `sms.configure` |
| 7 — 2FA | Baseline off for sms.configure; real M01 PENDING |
| 8 — notice states | `draft`, `published`; no auto-publish |
| 9 — audience | `section`, `person_ids` only |
| 10 — locales | `en`, `ml` |
| 11 — delivery states | queued/sending/accepted/delivered/failed/unknown |
| 12 — channels | `in_app`, `sms` |
| 13 — dedupe | same key+payload → same row; mismatch → 409 |
| 14 — content bans | password/TOTP/evidence URLs/detailed grades |
| 15 — callbacks | signature + replay; forged unchanged |
| 16 — templates | key/locale/version; Malayalam preserved |
| 17 — provider config | secret_ref + sender_id; never log secrets |
| 18 — recheck | revoke before SMS |

Deferred: real SMS sandbox, real Registry contacts, real M01 auth/2FA.

---

## Source identity

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m11/notices-third-party-sms` |
| Branched from | `8d84c00da9f3378514b91adc8b98c211dc77dfc9` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v11` |
| Freeze revision | `school-contracts-v12` |
