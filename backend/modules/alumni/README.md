# backend/modules/alumni -- M10

Not implemented. This directory holds no Python yet.

Note on importability, stated precisely because it is easy to get wrong: because
Python treats a directory without `__init__.py` as a *namespace package*,
`import modules.alumni` does technically succeed and yields an empty module. What
does **not** exist -- and what the guarantee actually rests on -- is
`modules.alumni.registration`. Importing it raises `ModuleNotFoundError`, which is
why `scripts/dev.py up M10` reports "not implemented" instead of booting an empty
Django app that looks like it works. `scripts/arch_check.py` additionally fails if
anything imports a module that has no `registration.py`.

Read [`contracts/M10/PACKET.md`](../../../contracts/M10/PACKET.md) first. The
contract is frozen in `contracts/manifest.json` **before** any code here.

When implementing, this package may import `contracts` and `shared`. It may
**never** import another `modules.*` package -- collaborate through the typed
service ports in `contracts/ports.py`.
