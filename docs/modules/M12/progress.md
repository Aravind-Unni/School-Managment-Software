# M12 progress

| | |
|---|---|
| Phase | Implementation complete; awaiting PostgreSQL/browser evidence |
| Status | Contracts **frozen** (`school-contracts-v13`). Module code on branch. **STANDALONE_VERIFIED=false** |
| Branch | `m12/compressed-answer-sheet-files` |
| Started from | `c3ece552164f4d7b99c8f688903f3892ecfeaeac` (`origin/main`) |
| Manifest revision | `school-contracts-v13` |
| PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/13 |
| Head commit | `adc53dd9b2137268b07e91b49e6dad316f4274e3` |
| Last recorded | 2026-09-21 |

## Original request

Build M12 compressed answer-sheet evidence and private files as an independently
runnable standalone module. Contracts first; then implement. May commit/push/
draft PR; no merge/deploy.

## Test numbers (this session)

```
MODULE_ID=M12 pytest tests/modules/M12/     22 passed
dev.py check M12 --suite contracts            green
  (manifest school-contracts-v13, arch 7, shared 105, M12 contract 7)
frontend typecheck + vite build               green
```

## Completed behaviour

- Contracts approved and frozen (`school-contracts-v13`): OpenAPI, DTO/event
  schemas, error rows, FilesPort (existing), fixtures, review-decisions.
- Models: UploadSession, SourceObject, File, Candidate, QualityReview,
  EvidencePin, Derivative, PurgeJob, FilesPolicy.
- API under `/api/v1`: uploads, complete, status, quality-confirmation,
  reprocess, retention-hold; quarantine PUT + grant read helpers.
- FilesPort: begin_upload, get_status, confirm_quality, pin_evidence,
  issue_read, store_artifact.
- Worker tasks: process_file, purge_source, cleanup_orphans; broker+worker on.
- Pillow decode/compress; module-owned memory/S3 store; BackupVerifier fake.
- Frontend review + parent viewer (en+ml); registered in app + i18n.
- Seeds: synthetic pages + candidate/accepted/hold/foreign.
- Foundation canaries retargeted to M13 (isolation + unimplemented-import).

## Incomplete / not-run

- Standalone PostgreSQL suite — not-run.
- Browser suite — not-run.
- PENDING integration: real M01 auth/2FA, Assessment publication gates,
  independent backup restoration, production object lifecycle.

## Exact next step

1. `python3 scripts/dev.py up M12 --profile standalone` then migrate/seed/check.
2. `evidence M12`; STANDALONE_VERIFIED only after peer verify from fresh checkout.
