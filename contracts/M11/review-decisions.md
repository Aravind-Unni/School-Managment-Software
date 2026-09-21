# M11 review decisions — PROPOSED (awaiting approval)

**Status: awaiting human review.** Do not freeze or implement until items below
are approved or revised.

Proposed freeze revision: `school-contracts-v12` (only after approval).

---

## Items for review

| # | Topic | Proposal | Alternatives |
|---|---|---|---|
| 1 | Event names | Dotted snake: `communications.notice_published`, `communications.delivery_status_changed` (maps manual NoticePublished.v1 / DeliveryStatusChanged.v1; envelope `schema_version`=1). No phone numbers in payloads. | Keep CamelCase `.v1` strings in `event_type` (breaks M02–M10 convention). |
| 2 | Provided port | New `CommunicationsPort.enqueue(ctx, template_key, recipient_ref, channel, locale, variables, dedupe_key) -> DeliveryDTO` in `backend/contracts/communications.py` after freeze. | Keep only REST; no in-process port. |
| 3 | Shared `NotificationPort` | **Revise** foundation stub: `send(...)` becomes a thin multi-recipient helper that calls `enqueue` once per recipient with a caller-supplied or derived dedupe key; document that producers needing idempotency must call `CommunicationsPort.enqueue` directly. Binding key stays `notifications` for existing harness wiring; add `communications` binding to the real M11 adapter in standalone. | Leave `NotificationPort` unchanged forever (diverges from manual); or delete it (breaks FakeNotifications consumers). |
| 4 | Provider adapter | Module-local `SmsProviderPort`: `send(message, idempotency_key)`, `lookup(provider_ref)`, `verify_callback(headers, raw_body)`. Not a cross-module shared port. Fake SMS HTTP server in standalone. | Put provider Protocol in `backend/contracts`. |
| 5 | API mount | `/api/v1/notices`, `/api/v1/messages`, `/api/v1/deliveries/{id}`, `/api/v1/sms/callback/{provider}` (manual). Packet’s `/api/communications/` prefix is superseded. | Nest under `/api/v1/communications/...`. |
| 6 | Permissions | Exact manual codes: `notices.create`, `notices.publish`, `messages.send`, `messages.read_status`, `sms.configure`. | Prefix all with `communications.` (e.g. `communications.notices_create`). |
| 7 | 2FA | Baseline: **not** required for notice/message APIs (M11 is not login 2FA). `sms.configure` may call `Access.require_recent_2fa` when a fixture says so; default fixture off. Real M01 step-up PENDING. | Always require step-up for publish/send. |
| 8 | Notice states | `draft`, `published`. `scheduled_at` optional on create; if set and in the future, publish still requires explicit publish call (no invented auto-publish policy). | Add `scheduled` state with worker auto-publish. |
| 9 | Audience selector | Closed kinds only: `section` `{section_id}`, `person_ids` `{person_ids: uuid[]}`. Resolved to `AudienceSnapshot.recipient_ids` on publish via Fake Registry contacts. No invented whole-school broadcast policy. | Add `school_all` / role-based audiences. |
| 10 | Locales | `en`, `ml` only. |
| 11 | Delivery states | `queued`, `sending`, `accepted`, `delivered`, `failed`, `unknown`. Timeout after provider accept → reconcile via `lookup` before resend. |
| 12 | Channels | `in_app`, `sms` for launch. Email out of scope for M11 send path. |
| 13 | Dedupe | Identical `(school_id, dedupe_key)` + identical payload_hash → same Delivery. Same key + different payload → **409** `state_conflict`. |
| 14 | Content bans | Reject variables/body containing password/TOTP secrets, answer-sheet / private evidence URLs, or detailed grade payloads (`communications.error.forbidden_content`). |
| 15 | Callbacks | `POST /sms/callback/{provider}`; signature + replay protection required. Forged → 401/403; delivery unchanged. |
| 16 | Templates | `MessageTemplate(key, locale, version, provider_template_id?)`. Unicode Malayalam preserved. Segmentation estimate is UI-only once provider rules known (fixture stub). |
| 17 | Provider config | `ProviderConfig(secret_ref, sender_id, enabled)`; one live provider at launch; secrets never logged. |
| 18 | Recheck before send | Snapshot audience at publish; worker rechecks verified contact + preference/revocation before SMS; guardian unlink blocks pending delivery. |

Deferred / PENDING integration (not freeze blockers): real SMS provider sandbox
(credentials, Unicode delivery, charges), real Registry contact verification,
real M01 auth/2FA, production sender/template registration.

---

## Source identity (recorded at proposal)

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m11/notices-third-party-sms` |
| Branched from | `8d84c00da9f3378514b91adc8b98c211dc77dfc9` (`origin/main`) |
| Manifest revision at proposal | `school-contracts-v11` |
| Proposed freeze revision | `school-contracts-v12` |
