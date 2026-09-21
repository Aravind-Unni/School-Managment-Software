# M11 service ports — proposed under school-contracts-v12

What M11 **provides** and what it **consumes**.

M11 imports no other module. Dependencies are Protocols from
`backend/contracts`, bound to deterministic fakes in standalone.

---

## 1. Provided: `CommunicationsPort`

```python
@runtime_checkable
class CommunicationsPort(Protocol):
    """In-app notices and replaceable outbound messaging. Owned by M11."""

    def enqueue(
        self,
        context: RequestContext,
        template_key: str,
        recipient_ref: UUID,
        channel: str,
        locale: str,
        variables: dict[str, object],
        dedupe_key: str,
    ) -> DeliveryDTO:
        """Queue one templated delivery; identical keys return the same row.

        recipient_ref is a verified school person/contact id from Registry,
        not arbitrary client text. Same dedupe_key with a different
        payload_hash raises StateConflict (409). Does not send passwords,
        TOTP secrets, evidence URLs or detailed grades.
        """
```

DTO shapes match `schemas/dtos.schema.json` (`DeliveryDTO`).

### Module-local: `SmsProviderPort` (not shared)

```python
class SmsProviderPort(Protocol):
    def send(self, message: SmsMessage, idempotency_key: str) -> ProviderSendResult: ...
    def lookup(self, provider_ref: str) -> str: ...  # delivery state
    def verify_callback(
        self, headers: Mapping[str, str], raw_body: bytes
    ) -> VerifiedCallbackEvent: ...
```

Fake adapter in standalone; real adapter only in integrated/production with
secrets. Production refuses fake adapters.

---

## 2. Consumed

### `AccessPort` — M01 (fake in standalone)

| Action | When |
|---|---|
| `notices.create` | Create draft notice |
| `notices.publish` | Publish + snapshot audience |
| `messages.send` | POST /messages and CommunicationsPort.enqueue |
| `messages.read_status` | GET /deliveries/{id} |
| `sms.configure` | ProviderConfig writes |

Scope facts: `{resource_school_id, subject_person_id?, section_id?,
relationship?, effective_date?}`. Recipient audience must fall within sender
scope. Fake Access defaults deny. Stale 2FA simulated only when a fixture
requires it for `sms.configure` (baseline: off).

### `RegistryPort` — M02 (fake in standalone)

| Method | Use |
|---|---|
| `get_student` | School isolation / display when audience includes pupils |
| `get_roster` | Resolve `section` audience to student ids on publish date |
| `get_relationships` | Scope checks; guardian unlink detection before SMS |

Fake Registry also supplies **verified contact references** for
`recipient_ref` (fixture table). Unused broad methods fail explicitly.

### `PlatformPort` — M14 (test adapter in standalone)

`record_audit` + `append_event` in the writing transaction.
`start_job` for delivery/reconcile workers (`communications.deliver`,
`communications.reconcile`). Real broker/worker in standalone (M11 owns jobs).

### `ClockPort`

Every timestamp. School civil dates via Asia/Kolkata when needed. Standalone
freezes the clock.

---

## 3. Workflow (module-local)

1. Create notice (draft) → optional `scheduled_at`.
2. Publish with `expected_version` → `AudienceSnapshot` + `communications.notice_published`.
3. In-app notice remains readable even if SMS provider is down.
4. `enqueue` / POST /messages → Delivery `queued`; worker → `sending` → provider
   `send` with idempotency_key → `accepted`/`failed`/`unknown`.
5. Timeout after accept → `lookup` before any resend; duplicate dedupe yields one
   provider request.
6. Callback: verify signature + replay; update state; emit
   `communications.delivery_status_changed`. Forged callback: no state change.
7. Before SMS send: recheck verified contact and preference/revocation.
