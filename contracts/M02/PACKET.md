# M02 Academic registry — approved contract (revision school-contracts-v4)

**APPROVED AND FROZEN** under revision `school-contracts-v4` on 2026-09-20 by
Abhinav M. The review outcome is recorded in `review-decisions.md`.
Changing any artefact in this directory now moves a frozen hash and will fail
`contract_manifest.py --check`; that is a new reviewed revision, not an edit.
Owner: Developer A. Based on main `1d17113ea333b1c77743b6cfdfe3b3d2314089f1`,
manifest `school-contracts-v3-draft`, M02 `not_started`.

This replaces the placeholder packet with a review proposal for the user's full
M02 request. It does not approve school policy or change the frozen foundation.
Read [review-decisions.md](review-decisions.md) first: foundation verification and
shared-interface conflicts block implementation.

## Artefacts for review

| File | Contents |
|---|---|
| `openapi.json` | OpenAPI 3.1; 81 operations across 53 paths; explicit write fields, nullability, responses, versions, cursor pagination and proposed permission metadata |
| `schemas/dtos.schema.json` | 100 named DTO/request/collection shapes; closed objects; copies of existing public Registry DTO shapes for exact compatibility |
| `schemas/events.schema.json` | Four requested event payload shapes |
| `ports.md` | Exact existing service signatures and proposed exchange/capability signatures |
| `error-codes.json` | 32 status/code/message-key rows using existing shared error codes |
| `fixtures/scenario.json` | Deterministic synthetic two-school, two-year transfer/guardian/elective scenario |
| `fixtures/responses.json` | Eight schema-valid public DTO examples, including elective period rosters |
| `fixtures/expected-results.json` | Twenty proposed acceptance cases; not test execution evidence |
| `review-decisions.md` | Explicit requested decisions and affected providers/consumers |

All artefacts stay outside the manifest until reviewed. Approval must include the
pending shared revision, then freeze and hash the actual approved files. Never
change existing frozen hashes merely to make the drift checker green.

## Boundary and records

Implement only `backend/modules/registry`, `frontend/src/features/registry`,
`dev/modules/M02`, `tests/modules/M02`, `docs/modules/M02`, and the approved
registration entry. The proposed contracts live here. No other business app is
installed or imported in standalone. Access, Platform and Clock are dependencies;
Registry is the real provider. No fake Registry is a substitute for M02 itself.

Owned business records: SchoolConfig, AcademicYear, Term, Standard (1–12), Section,
SubjectOffering, Student, Guardian, GuardianLink, StaffProfile, TeachingAssignment,
Enrolment and LearningOutcome. Additional records explicitly proposed to support
requested behaviour: Subject (school-authored reference, no seeded real curriculum),
SubjectEnrolment (effective-dated), RegistryPolicyRevision, ExternalIdentity,
DuplicateReview, PromotionPreview/Operation, ImportPreview/Operation and
AccessReviewTask and StudentLifecycleRecord. Actor-to-person association needs the separately reviewed
server-only binding in `ports.md`; student identity never requires a login.

Every stored entity has UUID id, trusted school_id and integer version. These
fields are not accepted as identity claims in browser write DTOs. Browser record
reads include version; the existing minimal internal StudentDTO is unchanged.
All cross-record references are resolved within ctx.school_id. Missing and
cross-school resources return indistinguishable 404s, including nested references.
All personal data remains inside the owning deployment/database.

## API conventions and review additions to the seeds

Paths are relative to `/api/v1`. Proposed registration owns students/, guardians/,
guardian-links/, staff/, teaching-assignments/, school-config/, academic-years/,
terms/, standards/, sections/, subjects/, subject-offerings/, subject-enrolments/,
enrolments/, learning-outcomes/, registry-policies/, registry-exchange/ and
registry-access-reviews/. No collision with M01's auth/accounts/roles/sessions roots.
The one school-config row is installed by the initial seed/bootstrap; PUT updates
it under expected_version, not an implicit create.

Creation returns 201, reads and updates 200. Promotion/import previews and commits
are proposed **synchronous 200** operations; no fictitious 202/job id. No worker,
broker or S3 is needed for inline JSON exchange. This is a review decision, not a
silent substitution for Platform.start_job. If asynchronous jobs are required,
revise the Platform contract and declare/test a real broker and worker first.

Every update requires expected_version; promotion also requires preview_version
and Idempotency-Key. Imports carry row expected_version and preview_version.
Collections use items/next_cursor, stable UUID ordering, school/filter-bound
opaque cursors, page_size default 50/cap 100. Invalid cursors are 422. RosterDTO is
one complete snapshot, not a paginated directory. Never truncate its members.

Closed request objects reject unknown fields, including school, role, relationship
and resource grants. Null is allowed only where explicitly declared. Error bodies
reuse the shared envelope. Identity-header rejection remains the existing shared
transport guard, preceding this API. Error-code enum remains unchanged.

The original creation seed is extended with external_ids and a duplicate_review
acknowledgement. Withdrawal adds policy_version so its supplied outcome has a
reviewed meaning. These are proposed API additions requiring approval. Student
creation returns the exact minimal StudentDTO; follow-up GET supplies its version.

## Dates, historical records and per-period rosters

UTC instants; school dates in Asia/Kolkata; ClockPort supplies time. Effective
from_date and to_date are **inclusive**, matching existing TeachingAssignment.
Null to_date is open-ended, bounded by the academic year for enrolments.
Transfer effective D closes the prior range on D-1 and starts the new one on D.
The operation must not create an empty prior interval. Requesting retrospective
changes is proposed to be rejected until a correction policy exists; no editing
of prior attendance/results. Terms and enrolments must fit their academic year;
subject choices fit their enclosing enrolment and offering's year/section.

An identity cannot have overlapping active enrolments, even across two active
academic years. Use PostgreSQL range/exclusion protection or equivalent serialised
student-row locking plus constraints; final database design reviewed before tests.
Concurrent conflicting transfers or enrolments must have exactly one winner.
Two active year records are allowed; they do not justify overlapping attendance.

Every pupil's subject membership is explicit, including required subjects: no
implicit full-section fallback for any subject_id. SubjectOffering identifies a
subject in one section/year and optional group. SubjectEnrolment links it to the
class enrolment over a date range. At most one active choice per non-null optional
group; uniqueness checks include concurrent choices. No school subject names,
stream lists, required combinations or board weights are invented.

For `get_roster(ctx, section, D, subject_id)`, intersect section enrolment, subject
enrolment, offering membership and effective dates; deduplicate pupils. Without
subject_id return the class roster. A known offering with no eligible pupils
returns an empty roster; an unknown/cross-school section or subject is 404.
A subject not offered in that section is 422. Closed/archived records remain
queryable historically with appropriate authorization.

Transfer preserves prior choices and maps future choices only to matching
subject IDs and compatible groups in the target section. Missing/ambiguous
matches return `subject_choice_required`, atomically; never silently enrol a
student into every elective. Initial fixtures give S1 subject X and S2 subject Y
so per-period consumer assertions expose an unfiltered class roster immediately.

Roster version changes transactionally whenever relevant enrolment, subject
choice or displayed-name data changes. Proposed implementation: section revision
row locked/incremented by each affecting mutation; transfer locks both sections
in UUID order. Its version may invalidate an unaffected historical read (safe),
but must never leave a changed snapshot with the same version.

## Duplicates, withdrawal, promotion and exchange

Admission number uniqueness is school-scoped. Proposal: trim outer whitespace,
preserve case and require exact equality; no fuzzy threshold. Exact name plus
non-null birth date yields a review candidate, not an automatic identity merge.
No Aadhaar field is required or collected by these DTOs. Duplicate-review tokens
bind actor, school, canonical input and candidate versions; proposed 15-minute
expiry is a technical review parameter. Exact admission duplicates cannot be
overridden; a different-person reason may acknowledge other candidates. Recheck
under the final transaction; a stale review or concurrent collision is 409.

Withdrawal effective D truncates current class/subject enrolments at D-1, cancels
future enrolment participation without deleting the records, and writes
StudentLeft plus one durable AccessReviewTask in the same transaction. Outcome
codes/status mapping are supplied by a published school policy, not guessed.
No fees, loans, marks, login accounts or other module tables are mutated. Historical
rosters are based on dates, not today's Student.status. Future-dated withdrawal
uses a dated lifecycle record/projection so current status does not change early;
this supporting record is part of the persistence review, not a scheduled job.

Promotion is an explicitly reviewed mapping of each cohort pupil to a destination,
repeat-year section or exclusion reason. No inferred pass marks or progression
rules. Preview binds all source enrolments and versions, source/target year and
section versions, subject choices, relevant student versions and policy revision.
Commit rechecks authorization and every dependency under ordered locks. Exceptions
block commit. New enrolments are created; old classes are not overwritten.
Repeated identical Idempotency-Key returns the same operation/IDs without new audit
or outbox records; changed payload with that key is 409. Keys are scoped by school,
operation kind and actor. Preview expiry proposal: 15 minutes. Persist outcomes
in the same transaction as enrolments, events and audit.

Exchange handles students, staff and opening enrolments by stable `(school,
source, kind, external_id)` mappings, never direct ORM access by a consumer.
Preview validates the whole batch, reports row paths, duplicates and conflicts;
commit is atomic and idempotent, and rechecks row versions/references. Null row
expected_version means create-only, never upsert over an existing row. An existing
mapping requires its exact current version. Imports obey the same duplication,
authorization, enrolment and policy rules as browser writes. Matching an existing
unmapped person requires review outside commit; never fuzzy-merge or guess.
Export is authorization-filtered and cursor-paginated; it never exports contacts,
guardian links or credentials under these minimal row schemas.

## Authorization proposal — no rules enabled by this packet

Owned permission codes: registry.manage, students.read, students.update,
guardians.manage, staff.assign, year.close, students.promote, students.withdraw.
No role rank or implied superuser; the approved fixture grant table must enumerate
each action for each actor. `x-permission` and `x-recent-2fa` in OpenAPI propose
checks, not operational grants. Proposed sensitive writes/export require recent
2FA (300 seconds); confirm at review. Permission denial precedes step-up.

Teacher reads are restricted to assigned sections AND subjects on the effective
date; guardians to effective academic-visible links; students to self through a
trusted account-person association. Directory/list paths filter before pagination
and cannot leak hidden counts or candidate identities. Administrative school-wide
reads require an explicit grant; registry.manage does not silently imply
students.read. Guarded historical access must be reviewed separately from current
roster membership; ending a guardian link must not retain access accidentally.
Adult transitions use unpublished, explicit school policy; no invented birthday
threshold or automatic permission change. Domain fixtures are not production grants.

Relationship resolution never calls Access. The trusted host resolves constrained
facts, checks scope and feeds ScopeFacts to Access. No public relationship endpoint
accepts actor/role facts. See `ports.md` for the required capability review.

## Audit, outbox and failures

All critical mutations, operation records, AccessReviewTasks, audit and events
share one transaction. Audit records describe changed identifiers/field names and
versions; do not copy contact data, birth dates, credentials or free-text reasons
into cross-module events. Reasons may be held in access-controlled registry history.
The event payload schemas use IDs/dates/outcome codes only. Audit/outbox failure
rolls everything back. At-least-once consumers deduplicate event_id.

Enrolment.state is active or cancelled; date ranges determine participation,
so a future active row is not yet on a current roster. Withdrawal marks future
rows cancelled while keeping their original dates/history.

No destructive DELETE API. Archive preserves referenced records, prevents new
links to archived configuration, and never hides authorized history. Closing a
year blocks new lifecycle writes; exact correction/reopening rules remain absent
and therefore denied, not invented. Published policies are immutable: create a
new draft revision; publication requires explicit approval evidence/examples.

## Implementation order after approval

1. Configuration and people: schema/migrations, setup/directory/profile UI, strict
   writes, duplicate review, deterministic fixtures, rollback/isolation checks.
2. Links and assignments: many-to-many dated guardian visibility, staff assignments,
   subject offerings/choices and constrained relationship facts.
3. Enrolment lifecycle: overlaps/concurrency, transfer, withdrawal/access review,
   promotion preview/commit/idempotency, retained history and version invalidation.
4. Exchange and historical roster tests: validated import/export port, stable IDs,
   elective-period consumer fixtures, real browser journeys in English/Malayalam.

After EACH step update progress/handoff/acceptance with actual source and checks.
Standalone verification requires real PostgreSQL, migrations on empty and seeded
databases, all required suites, locales, production build and a second developer's
fresh-checkout verification. Required skipped checks remain blockers.

Integration tests remain PENDING: M03 period consumers, M04 historical attendance,
M10 alumni candidates, M01 account access/revocation and M13 real exchange. No
other module is imported or integrated to make standalone checks pass.
