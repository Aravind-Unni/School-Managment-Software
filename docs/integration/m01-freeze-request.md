# M01 freeze review request

M01 implementation is on main; `contracts/manifest.json` still lists M01 as
`not_started`. **Do not silent-freeze.**

## Reviewer checklist

1. Read `contracts/M01/PACKET.md` and OpenAPI / schemas / error enums / fixtures.
2. Confirm they match the merged M01 behaviour (no silent widening).
3. Add `frozen_modules.M01` in `contracts/revision.json`.
4. Run `python3 scripts/contract_manifest.py --update`.
5. Run `python3 scripts/dev.py check M01 --suite contracts`.
6. Record reviewer name and date below.

| Field | Value |
|---|---|
| Reviewer | |
| Date | |
| Decision | pending |
| Notes | |

Until this is signed, C02 keeps `M01_contracts_unfrozen` as a hard blocker and
`INTEGRATION_VERIFIED` stays false.
