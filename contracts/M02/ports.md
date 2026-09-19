# M02 service ports — proposed binding contract

No Python in this document is installed or imported. Existing signatures below
are read from `backend/contracts/ports.py`. Additional interfaces need a reviewed
shared revision; never hide them in another module's implementation namespace.

## Existing RegistryPort (preserve exactly)

```python
get_student(self, context: RequestContext, student_id: UUID) -> StudentDTO
get_roster(self, context: RequestContext, section_id: UUID,
           effective_date: date, subject_id: UUID | None = None) -> RosterDTO
get_relationships(self, context: RequestContext, actor_id: UUID,
                  student_id: UUID, effective_date: date) -> RelationshipFacts
get_teaching_assignments(self, context: RequestContext, staff_id: UUID,
                         effective_date: date) -> tuple[TeachingAssignment, ...]
relationship_facts(self, context: RequestContext,
                   subject_person_id: UUID) -> RelationshipFacts
```

StudentDTO/RosterDTO/TeachingAssignment wire schemas match the shared file.
No get_roster call may treat subject_id as decoration: the dated subject choices
are mandatory inputs to its filtering, including transfers on period dates.
Student reads and rosters require Access decisions on server-resolved scope.
Relationship methods must not call Access, to avoid resolver recursion. Existing
arbitrary actor lookups cannot become a public unguarded API. Legacy ctx-based
relationship_facts is self-actor only, with the host clock's school date; other
actor/date lookups require the reviewed trusted reader below.

## Proposed RegistryFactReaderPort and capability (shared revision required)

```python
@dataclass(frozen=True, slots=True)
class RegistryReadCapability:
    capability_id: UUID
    school_id: UUID
    caller_module_id: str
    actor_ids: frozenset[UUID]
    student_ids: frozenset[UUID]
    staff_ids: frozenset[UUID]
    from_date: date
    to_date: date
    expires_at: datetime
    operations: frozenset[Literal["relationships", "teaching_assignments"]]


class RegistryFactReaderPort(Protocol):
    def get_relationships(
        self,
        capability: RegistryReadCapability,
        *,
        actor_id: UUID,
        student_id: UUID,
        effective_date: date,
    ) -> RelationshipFacts: ...

    def get_teaching_assignments(
        self,
        capability: RegistryReadCapability,
        *,
        staff_id: UUID,
        effective_date: date,
    ) -> tuple[TeachingAssignment, ...]: ...
```

A plain constructed dataclass is NOT authority. The trusted host issues and binds
capability_id to exact immutable fields in a request-scoped issuance registry.
Registry verifies issuance plus every field, expiry, date interval, method and
resource scope using ClockPort before reading; reconstructed/unissued IDs fail.
No browser schema accepts this type, no general-purpose mint endpoint exists,
and no downstream module may grant itself broader scope. Production and fake
providers must validate the same constraints. This design requires security
review, not just type checking. No durable/storable capability token is proposed.

ActorPersonBinding is school-scoped, effective-dated, and keyed to a server-verified
actor id. Only an approved identity administration service may write it; no browser
input asserting actor ownership. Synthetic standalone bindings connect fixed
server personas to fixture people. Many people may have no binding/account.
M01 integration remains pending. The binding's issuance/write contract must be
approved with M01/host owners before implementing relationship authorization.

## Proposed RegistryExchangePort (shared revision required)

All capitalized DTOs below are immutable types whose wire shapes are defined in
`schemas/dtos.schema.json`. Errors use `error-codes.json`; they are not booleans
or partial success. Import rows are strictly schema validated, including unknown
fields. Exports carry only the selected row kind per page.

```python
class RegistryExchangePort(Protocol):
    def preview_import(
        self,
        context: RequestContext,
        request: ImportPreviewRequest,
    ) -> ImportPreview: ...

    def commit_import(
        self,
        context: RequestContext,
        request: ImportCommit,
        *,
        idempotency_key: str,
    ) -> ImportResult: ...

    def export_page(
        self,
        context: RequestContext,
        *,
        kind: Literal["students", "staff", "opening_enrolments"],
        cursor: str | None = None,
        page_size: int = 50,
    ) -> ExportPage: ...
```

Methods call the same authorized services as REST. A future M13 consumer uses
this port only, not Registry ORM models. No network to unfinished modules, and
no worker is promised. A schema-compatible fake must exercise success, denial,
missing reference, stale preview/row versions, duplicate IDs/retries and injected
failure before the future consumer can claim contract compatibility.

## Dependencies to preserve

```python
AccessPort.authorize(context, action, scope_facts) -> Decision
AccessPort.require_recent_2fa(context, max_age_seconds=300) -> None
PlatformPort.record_audit(record: AuditRecord) -> None
PlatformPort.append_event(event: EventEnvelope) -> None
ClockPort.now() -> datetime
```

Build audit_id/event_id in M02 before sending the existing immutable DTOs; do not
change Platform's return type or fake it with a new facade. Platform writes join
the caller transaction. No call to absent start_job. Unused enqueue must continue
to refuse worker assertions. Proposed audit actions use the explicit permission
or operation name; four emitted event types are exactly StudentEnrolled.v1,
StudentSectionChanged.v1, StudentLeft.v1 and GuardianLinkChanged.v1, subject to
review of the frozen envelope's conflicting event_type regex.

Module tests may wrap the real deterministic adapters to record calls, but may
not weaken their denies, tenant checks, failure injection or transaction semantics.
Host binding of scoped fixture grants requires the review in review-decisions.md.
