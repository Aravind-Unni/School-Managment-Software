# C02 journey matrix (integration gate)

Execute on a live **integrated** stack (`python3 scripts/dev.py up all --profile integrated`
then migrate + seed). Record pass/fail with evidence paths. Do **not** mark
`INTEGRATION_VERIFIED` until every row is observed pass **and**
`independent_approvals_count == 14` and M01 is frozen.

| ID | Journey | Persona | How to run | Result | Evidence |
|---|---|---|---|---|---|
| J1 | Login + CSRF session | admin | Browser: `/login` → home | | |
| J2 | Registry students list | admin | `/registry/students` | | |
| J3 | Teacher attendance mark | teacher | `/attendance/today` | | |
| J4 | Timetable class week | teacher | `/timetable/class/...` | | |
| J5 | Assessment marking | teacher | `/assessment/...` | | |
| J6 | Fee statement | guardian | `/fees/statement/...` | | |
| J7 | Transport roster | admin | `/transport/...` | | |
| J8 | Library issue | librarian | `/library/desk` | | |
| J9 | Notice send | admin | `/comms/...` | | |
| J10 | Files review | admin | `/files/review` | | |
| J11 | Exchange export | admin | `/exchange/export` | | |
| J12 | Platform audit read | owner | `/platform/audit` | | |
| J13 | Denial: unrelated class | teacher | Playwright M03 denial | | |
| J14 | Guardian revoke path | guardian | M05 pending case | | |

Automation entry: `python3 scripts/dev.py check all --suite browser` covers the
Playwright subset that modules already ship. Rows without automated coverage
require a signed manual smoke on integrated (or prod compose).

## Observed this session

| Suite / row | Result |
|---|---|
| load | **passed** — `dev/evidence/.../load.json` |
| restore | **passed** — `dev/evidence/.../restore.json` |
| browser ALL | **passed** — 5 integrated-smoke journeys |
| J1 Login + CSRF | **passed** (integrated-smoke) |
| J2–J4, J6 partial | guardian home + fees nav link observed |
| J5, J7–J14 | not signed — need peer standalone + manual matrix |
| `INTEGRATION_VERIFIED` | **false** — see release-manifest.json |
