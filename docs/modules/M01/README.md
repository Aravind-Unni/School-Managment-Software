# M01 access

Status: **implemented, verification and contract review incomplete**. The module
is not STANDALONE_VERIFIED and its contract artefacts are not frozen.

- Current state and next action: [progress.md](progress.md)
- Verification limits and open review questions: [handoff.md](handoff.md)
- Proposed contract: [PACKET.md](../../../contracts/M01/PACKET.md)
- Implementation: `backend/modules/access/`, `frontend/src/features/access/`

M01 uses real login, sessions, TOTP and recovery, with a deterministic fake
Registry. It does not bind fake Access, because it owns Access.

After starting, migrating and seeding the M01 standalone stack, select its browser
suite explicitly:

```bash
MODULE_ID=M01 python3 scripts/dev.py check M01 --suite browser
```

New endpoint or policy work must wait for review and freezing of the proposed
contracts. See the handoff for shared interfaces already changed on this branch.
