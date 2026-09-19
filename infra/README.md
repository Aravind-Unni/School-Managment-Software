# infra

Deployment and container inputs for the foundation.

| File | Purpose |
|---|---|
| `images.json` | Every base image, pinned by tag **and digest**. Each digest was resolved against the live registry, not written from memory. |
| `backend.Dockerfile` | Django/DRF image. Installs with `--require-hashes` from the committed lockfiles. |
| `frontend.Dockerfile` | Vite/React image. Installs with `npm ci` from the committed `package-lock.json`. |

Compose files are **generated**, not committed: `dev/harness/compose.py` renders
one per module into `dev/state/`, containing only the services that module
declared. That is what lets two developers run two modules at once without
colliding.

## Production

Out of scope for B00. M14 owns production deployment, and **Kubernetes is not
required**. These Dockerfiles are shaped so M14 can build on them: dependencies
install from lockfiles, the source is copied (not only bind-mounted), and both
images run as an unprivileged user.

## Upgrading an image

1. Resolve the new tag **and** its digest from the registry.
2. Update both fields in `images.json` in one commit, with the reason.
3. Re-run `python scripts/dev.py check M00 --suite standalone`.
4. Record it in `docs/foundation/progress.md`.
