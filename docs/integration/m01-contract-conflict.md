# M01 contract conflict — C02

**Do not silent-freeze.** Freezing M01 is a separate human review decision.

## Conflict

| Field | Value |
|---|---|
| Provider | M01 Access (`backend/modules/access/`), merged via [PR #2](https://github.com/Aravind-Unni/School-Managment-Software/pull/2) |
| Consumers | Every module declaring `consumers` including `access` |
| Manifest status | `contracts/manifest.json` → `modules.M01.status = not_started` |
| Revision note | `contracts/revision.json` `unfrozen_note` explicitly keeps M01 out of `frozen_modules` |
| Artefacts | Hashed in the manifest (drift detectable) but **not** claimed approved |

## Conflicting fields / semantics

No field-level schema collision was introduced by C02 wiring. The conflict is
**approval status vs code on main**: integrated mode binds `AccessService` for
runtime diagnosis while the contract packet remains unreviewed for freeze.

## Proposed minimum reviewed correction

1. Human reviews `contracts/M01/PACKET.md`, OpenAPI, fixtures and error rows.
2. Add `frozen_modules.M01` to `contracts/revision.json` with reviewer + date.
3. Regenerate `contracts/manifest.json` via `scripts/contract_manifest.py`.
4. Re-run `python3 scripts/dev.py check M01 --suite contracts` and
   `check all --suite contracts`.

## C02 behaviour until freeze

- Wire `AccessService` as the real `access` provider.
- Record `independent_approval: false` and this conflict in
  `release-manifest.json`.
- Do **not** set `INTEGRATION_VERIFIED`.
