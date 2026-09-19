# backend/modules/assessment -- M05

Not implemented. This directory holds no Python yet.

Note on importability, stated precisely because it is easy to get wrong: because
Python treats a directory without `__init__.py` as a *namespace package*,
`import modules.assessment` does technically succeed and yields an empty module. What
does **not** exist -- and what the guarantee actually rests on -- is
`modules.assessment.registration`. Importing it raises `ModuleNotFoundError`, which is
why `scripts/dev.py up M05` reports "not implemented" instead of booting an empty
Django app that looks like it works. `scripts/arch_check.py` additionally fails if
anything imports a module that has no `registration.py`.

Read [`contracts/M05/PACKET.md`](../../../contracts/M05/PACKET.md) first. The
contract is frozen in `contracts/manifest.json` **before** any code here.

When implementing, this package may import `contracts` and `shared`. It may
**never** import another `modules.*` package -- collaborate through the typed
service ports in `contracts/ports.py`.
