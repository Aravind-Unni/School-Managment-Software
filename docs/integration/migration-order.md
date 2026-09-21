# Migration order — C02 integrated profile

Recorded from Django app installation order on `c02/integration`. Do not rewrite
already-shipped migration files; reconcile dependencies only.

## Host install order (`APPROVED_MODULE_IDS`)

1. `modules.demo` (M00)
2. `modules.platform` (M14)
3. `modules.access` (M01)
4. `modules.registry` (M02)
5. `modules.files` (M12)
6. `modules.timetable` (M03)
7. `modules.attendance` (M04)
8. `modules.assessment` (M05)
9. `modules.fees` (M07)
10. `modules.transport` (M08)
11. `modules.library` (M09)
12. `modules.alumni` (M10)
13. `modules.performance` (M06)
14. `modules.communications` (M11)
15. `modules.exchange` (M13)

Plus shared: `contenttypes`, `staticfiles`, DRF, spectacular, corsheaders,
`shared.harness`.

## Cross-module rules

- Physical FKs stay inside one module.
- Cross-module references are UUIDs (or documented registry/file FKs).
- No cascade deletion of published results, ledgers or evidence.
- M02 added `0002_lifecycle_links_enrolments` (guardian links, assignments,
  enrolments, offerings) without rewriting `0001_initial`.

## Reversibility notes

- Before production writes: restore prior environment from backup.
- After production writes: forward fix / controlled reconciliation only.
- Integrated `migrate all` applies every installed app's migrations in Django
  dependency order on one nonempty database; rehearse on staging first.

## Verification command

```bash
python3 scripts/dev.py up all --profile integrated
python3 scripts/dev.py migrate all --profile integrated
```

Mark applied only after observing success on a nonempty staging database.
