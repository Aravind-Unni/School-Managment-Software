# M12 service ports — frozen under school-contracts-v13

What M12 **provides** and what it **consumes**.

M12 imports no other module. Dependencies are Protocols from
`backend/contracts`, bound to deterministic fakes in standalone (Access,
Platform). Object bytes use a module-owned S3-compatible client against
Compose MinIO / test memory store — not another business module.

---

## 1. Provided: `FilesPort` (already in `backend/contracts/ports.py`)

```python
@runtime_checkable
class FilesPort(Protocol):
    """Private file lifecycle. Owned by M12 files.

    Only ``purpose=answer_sheet`` supports quality review and evidence pinning.
    Implementations must not accept browser-supplied ResourceGrant values.
    """

    def begin_upload(
        self, context, purpose, client_name, declared_bytes, mime
    ) -> UploadSession: ...

    def get_status(self, context, file_id) -> FileDTO: ...

    def confirm_quality(self, context, file_id, candidate_version) -> FileDTO: ...

    def pin_evidence(
        self, context, file_id, canonical_version, binding_id
    ) -> FileEvidenceRef: ...

    def issue_read(self, context, grant: ResourceGrant) -> ReadUrlDTO: ...

    def store_artifact(
        self, context, purpose, content_ref, mime, sha256
    ) -> ArtifactRef: ...
```

DTO shapes match `schemas/dtos.schema.json` and `backend/contracts/files.py`.

HTTP-only (not on the Protocol): `complete_upload`, `reprocess`,
`set_retention_hold`.

`ResourceGrant` stays the frozen foundation shape
(`grant_id`, `school_id`, `actor_id`, `action`, `resource_id`,
`issued_at`, `expires_at`). `resource_id` is the file id; version is enforced
against pins / canonical at `issue_read`.

---

## 2. Consumed

### `AccessPort` — M01 (fake in standalone)

| Action | When |
|---|---|
| `files.upload` | Begin/complete upload; status for uploader staff |
| `files.review_quality` | Confirm quality; reprocess |
| `files.retention.manage` | Legal hold / retention (+ recent 2FA) |

`files.read` is never a browser REST permission: private reads go through
server-minted `ResourceGrant` after Assessment (or fixture) authorisation.

Scope facts: `{resource_school_id, subject_person_id?, relationship?,
effective_date?}`. Fake Access defaults deny; fixture grants are school-scoped
staff rules. Stale 2FA simulated for retention.

### `PlatformPort` — M14 (test adapter in standalone)

`record_audit` + `append_event` in the writing transaction.
`start_job` for compress / purge / orphan cleanup.

### `ClockPort`

Every timestamp. School civil dates via Asia/Kolkata.

---

## 3. Workflow (module-local)

1. `begin_upload` → quarantine key + short-lived put URL.
2. Client PUTs bytes; `complete` verifies sha256/limits → File `processing`.
3. Worker decodes (answer_sheet only), compresses once, emits
   `files.candidate_ready` or `files.rejected`.
4. Teacher `quality-confirmation` → immutable canonical + `files.accepted`.
5. Assessment calls `pin_evidence`; later `issue_read` with internal grant.
6. Economical purge after confirm + backup verify + 7-day grace + no hold →
   `files.source_purged`. Never purge pinned canonical.
