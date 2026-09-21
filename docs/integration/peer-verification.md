# Peer verification protocol (STANDALONE_VERIFIED)

Each of M01–M14 requires a **second person** (not the implementer) to re-run
evidence from a **fresh checkout** before `STANDALONE_VERIFIED` may be set.

## Verifier steps (per module ID)

```bash
git clone <repo> school-verify && cd school-verify
git checkout <branch>
python3 scripts/dev.py doctor
python3 scripts/dev.py up <ID> --profile standalone
python3 scripts/dev.py migrate <ID> --profile standalone
python3 scripts/dev.py seed <ID> --scenario baseline
python3 scripts/dev.py check <ID> --suite contracts
python3 scripts/dev.py check <ID> --suite standalone
python3 scripts/dev.py check <ID> --suite browser
python3 scripts/dev.py evidence <ID>
```

Record observed counts in `docs/modules/<ID>/acceptance.json`, then set
`standalone_verified` / `independent_approval` in
`docs/integration/release-manifest.json` only if all three suites passed.

## M01 freeze (separate)

Do **not** silent-freeze. Review `contracts/M01/`, then add
`frozen_modules.M01` to `contracts/revision.json` and run
`python3 scripts/contract_manifest.py --update`.

## Status

Until named verifiers complete the table below, `independent_approvals_count`
stays 0 and `INTEGRATION_VERIFIED` stays false.

| Module | Verifier name | Date | Evidence path |
|---|---|---|---|
| M01 | | | |
| M02 | | | |
| M03 | | | |
| M04 | | | |
| M05 | | | |
| M06 | | | |
| M07 | | | |
| M08 | | | |
| M09 | | | |
| M10 | | | |
| M11 | | | |
| M12 | | | |
| M13 | | | |
| M14 | | | |
