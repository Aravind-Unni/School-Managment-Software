# M02 review decisions — none approved by authoring this file

## Prerequisites

B00 exists and is merged. Its tracked acceptance record still says peer_reviewed
false and lists unverified criteria. Latest M01 CI proves its own container stack,
not completion of B00's human gate. Local doctor exits 2 without a container engine.
Do not record B00 or M02 as verified. Minimum prerequisite: a reviewer reconciles
B00 acceptance with observed evidence and explicitly closes its verification gate.

M02 currently has no frozen artefacts. Main includes M01's shared changes under
`school-contracts-v3-draft`, with M01 itself still not frozen. A merge instruction
was not contract approval. Freeze the actual approved baseline and M02 proposal
under a reviewed revision before module tests/code.

## Compatibility and proposed resolutions

| Finding in current source | Proposal for review | Affected owners/consumers |
|---|---|---|
| RegistryPort already has StudentDTO, RosterDTO, TeachingAssignment and dated methods | Preserve signatures/shapes; versioned browser StudentRecord is a separate response, not an extension to frozen StudentDTO | M02 provider, FakeRegistry, M01 and future M03/M04/M05 |
| StudentStatus has active/inactive/transferred/graduated, no withdrawn | School-approved withdrawal outcomes map to these statuses; dated withdrawal is retained separately. Do not silently add enum members | Registry provider/fake and all readers |
| RelationshipFacts includes required actor_id and subject_person_id beyond the abbreviated seed | Preserve existing complete shape; always populate school/date/plural scope fields | Registry, resolver, Access, every scoped consumer |
| RequestContext has no service capability, RegistryPort has no constrained trusted-fact handle, account id is not a person id | Add separately reviewed host-issued capability reader and trusted actor-person binding; no browser mutation endpoint | shared identity/ports/resolver, M01 future integration, M02/FakeRegistry |
| ScopeResolver selects one section/subject from plural facts and does not check facts.school_id against context | Review an explicit dated, section/subject-targeted resolver contract plus mismatch rejection; do not widen scopes by taking an arbitrary first item | shared resolver, Access consumers; tenancy gate applies |
| No domain exchange port exists | Proposed RegistryExchangePort in ports.md, with schema-backed preview/commit/export | M02 provider, future M13 consumer; shared port owner |
| PlatformPort takes AuditRecord/EventEnvelope and returns None; no start_job | Call existing DTO-based methods directly and allocate IDs before writing; synchronous promotion/import. No local imitation of missing start_job | Platform/fake, M02; no signature change if accepted |
| Frozen common event-type regex rejects requested StudentEnrolled.v1 etc. | Review a finite compatibility extension accepting the four requested M02 names, keeping existing names valid. No schema edit in this branch | Platform/outbox schema, provider/fake fixtures, downstream consumers |
| EventEnvelope emits envelope_version as well as schema_version | Retain both for this revision; do not silently delete frozen fields | Every event consumer |
| FakeAccess extra_rules exists, but shared factory passes none; PolicyRule has no actor/section/subject restriction and records no calls | Review module-local fixture configuration hook and optional constrained fixture grants/call recording in existing fake. No allow_all and no standalone test-only bypass | shared FakeAccess/binder, M00 regression, M02 standalone |
| Harness/frontend only have implemented M00/M01 entries; Playwright special-cases M01 | Add only approved M02 registration and scoped test discovery; M02 tests remain in its feature/test folders. No harness regeneration | frontend registry/build/browser config; shared change review |
| Frozen error taxonomy has no domain-specific codes | Reuse state_conflict/validation_failed plus proposed message keys; no enum expansion | Error formatter/frontend |

The manifest generator currently hardcodes `school-contracts-v3-draft` and only
freezes M00. It also scans only top-level module schemas, not `schemas/`. A reviewed
revision must address that tooling limitation and explicitly hash all DTO/event
schemas; invoking `--update` alone is not a real freeze. No guard is changed here.

## Plain-language behaviour to approve or revise

1. Promotion uses a staff-reviewed per-student destination, including repeat-year
   exceptions, without calculating pass/fail. No grade rules are supplied.
2. Adult-student guardian policy remains unpublished until the school supplies a
   rule; there is no guessed legal age or automatic access transition.
3. Initial profile is deliberately minimal: optional birth date and language, no
   Aadhaar. Review admission normalization (outer trim, case-sensitive), exact
   name/birth-date duplicate candidates and required review acknowledgement.
4. Date intervals are inclusive; effective transfer/withdrawal D excludes the old
   enrolment on D. Retrospective corrections are refused pending a correction policy.
5. Imports and promotion commits are synchronous/atomic with replay protection.
   Withdrawal creates a durable registry access-review task, not an eager worker
   job or an unimplemented Platform.start_job call.
6. Proposed recent-2FA requirement is 300 seconds on writes/export; grants are
   explicit per actor/scope. Confirm visibility=`academic|none` before activation.
7. School-approved subject/stream, grading reference and withdrawal outcome codes
   must be supplied through draft/publish data, with approved examples. Synthetic
   tests may exercise unpublished templates; they do not approve CBSE rules.
8. Proposed duplicate/import/promotion preview lifetime is 15 minutes. This is
   an implementation parameter for review, not a school policy assertion.

Minimum to unblock implementation: record approval/revisions for this packet and
shared changes, settle B00 verification, then freeze a reviewed manifest revision.
An acceptable partial is this schema/fixture proposal and draft PR. Do not begin
module tests before the packet gate, or enable permissions before their review.
