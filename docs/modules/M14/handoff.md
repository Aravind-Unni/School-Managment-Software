# M14 handoff

## Where things stand

Contract packet **proposed**, not frozen. Implementation has not started
(AGENTS.md human gate).

| Item | Value |
|---|---|
| Branch | `m14/platform-audit-jobs-backup` |
| Started from | `a2f16c24dc6a7c7004e5358a094f0bd0fc5760dd` (`origin/main`) |
| Manifest | `school-contracts-v14`; M14 artefacts hashed with `frozen: false` |
| Proposed freeze | `school-contracts-v15` after review of `contracts/M14/review-decisions.md` |

## Startup (after implementation)

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M14 --profile standalone
python3 scripts/dev.py migrate M14 --profile standalone
python3 scripts/dev.py seed M14 --scenario baseline
python3 scripts/dev.py check M14 --suite contracts
python3 scripts/dev.py check M14 --suite standalone
python3 scripts/dev.py check M14 --suite browser
python3 scripts/dev.py evidence M14
```

URLs come from `up` output; do not assume fixed ports.

## PENDING integration (do not claim standalone)

- Real domain job identities against other modules
- Production monitoring against live multi-module traffic
- Full-scale RPO 15m / RTO 4h validation
- Real M01 authentication / 2FA for ops identities

## Next developer / reviewer action

Approve or amend items 1–16 in `contracts/M14/review-decisions.md`, then freeze
M14 in `contracts/revision.json` and regenerate the manifest. Only then begin
implementation step 1.
