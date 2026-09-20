# M05 service ports — PROPOSED, NOT FROZEN

What M05 **provides** and what it **consumes**. Nothing here is frozen until the
manifest says so.

M05 imports no other module. Dependencies are Protocols from
`backend/contracts/ports.py` (plus proposed `FilesPort`), bound to
deterministic fakes in standalone.

---

## 1. Provided: `AssessmentPort`

```python
@runtime_checkable
class AssessmentPort(Protocol):
    """Published assessment facts for other modules. Owned by M05."""

    def get_published_results(
        self,
        context: RequestContext,
        student_id: UUID,
        term_id: UUID,
        cursor: str | None = None,
    ) -> PublishedResultPage:
        """Return published results for one pupil in one term.

        Draft/submitted/approved rows are never returned to student or guardian
        scopes. Staff with results scope may see published rows for assigned
        sections. Raises ObjectInaccessible for unknown/other-school students.
        """

    def get_assignment_summary(
        self,
        context: RequestContext,
        student_id: UUID,
        window: AssignmentWindow,
    ) -> AssignmentSummaryDTO:
        """Return assignment counts for one pupil in a closed time window.

        Only assessments with type=assignment. Draft data never leaks to
        student/guardian scopes: missing means not submitted by due_at.
        """
```

DTO shapes match `schemas/dtos.schema.json`. Until the shared Protocol is
approved (review item 2 family), the concrete service lives at
`modules.assessment.services.port.AssessmentService`.

---

## 2. Consumed

### `AccessPort` — M01 (fake in standalone)

| Action | When |
|---|---|
| `assessment.manage` | Create/update assessment structure |
| `marks.edit` | PATCH result marks (assigned section+subject teacher) |
| `marks.submit` | Submit for review |
| `results.approve` | Approve submitted results |
| `results.publish` | Publish (+ recent 2FA) |
| `results.reopen` | Reopen published (+ recent 2FA + reason) |
| `evidence.view` | View pinned answer-sheet pages (published own-child / assigned staff) |

Scope facts: `{resource_school_id, subject_person_id?, section_id?, subject_id?,
relationship?, effective_date?}`. Module resolves teaching assignment via
Registry before asking Access.

### `RegistryPort` — M02 (fake in standalone)

| Method | Use |
|---|---|
| `get_roster(ctx, section_id, date, subject_id=...)` | Marking grid pupils |
| `get_student` | Existence / school isolation |
| `get_relationships` | Guardian/self published reads |
| `get_teaching_assignments` | Teacher section+subject gate |

### `FilesPort` — M12 (**PROPOSED** shared addition; FakeFiles in standalone)

```python
@runtime_checkable
class FilesPort(Protocol):
    def begin_upload(self, context, purpose, client_name, declared_bytes, mime) -> UploadSession: ...
    def get_status(self, context, file_id) -> FileDTO: ...
    def confirm_quality(self, context, file_id, candidate_version) -> FileDTO: ...
    def pin_evidence(self, context, file_id, canonical_version, binding_id) -> FileEvidenceRef: ...
    def issue_read(self, context, grant: ResourceGrant) -> ReadUrlDTO: ...
    def store_artifact(self, context, purpose, content_ref, mime, sha256) -> ArtifactRef: ...
```

Only `purpose=answer_sheet` supports quality review and evidence pinning.
Unconfirmed files (`review_confirmed=false`) block publication.
Unused methods on a broad fake fail explicitly.

### `PlatformPort` — M14 (test adapter in standalone)

`record_audit` + `append_event` in the writing transaction. `enqueue` for
`assessment.report_snapshot` after successful publication (retryable; does not
block the publish commit).

### `ClockPort`

Every timestamp. No `datetime.now()` in decision logic.

---

## 3. Workflow (module-local)

1. Create assessment (draft) with components + policy_version.
2. Teacher edits marks / marking_outcome; bind evidence pages.
3. Submit → approve → publish (single Idempotency-Key batch).
4. Reopen with reason creates a new result revision; old publication manifest
   retained.
5. Student/guardian reads only after `published`.
