# backend/modules/exchange -- M13

Not implemented. This directory holds no Python yet.

Note on importability, stated precisely because it is easy to get wrong: because
Python treats a directory without `__init__.py` as a *namespace package*,
`import modules.exchange` does technically succeed and yields an empty module. What
does **not** exist -- and what the guarantee actually rests on -- is
`modules.exchange.registration`. Importing it raises `ModuleNotFoundError`, which is
why `scripts/dev.py up M13` reports "not implemented" instead of booting an empty
Django app that looks like it works. `scripts/arch_check.py` additionally fails if
anything imports a module that has no `registration.py`.

Read [`contracts/M13/PACKET.md`](../../../contracts/M13/PACKET.md) first. The
contract is frozen in `contracts/manifest.json` **before** any code here.

When implementing, this package may import `contracts` and `shared`. It may
**never** import another `modules.*` package -- collaborate through the typed
service ports in `contracts/ports.py`.
