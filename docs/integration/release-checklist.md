# School + operations release acceptance checklist

Complete only after `INTEGRATION_VERIFIED` is true and the VPS install is live.

| Check | Who | Date | Initials |
|---|---|---|---|
| Admin can sign in with 2FA on the live hostname | School | | |
| Teacher can take attendance for a real class | School | | |
| Guardian can view fee statement / child schedule | School | | |
| Backup restore drill recorded (RPO/RTO) | Ops | | |
| TLS certificate valid; healthz/readyz green | Ops | | |
| No demo/persona mode on production | Ops | | |

School contact: __________________  
Ops contact: __________________  

Only after both sign, set `RELEASE_ACCEPTED: true` in `docs/integration/release-manifest.json`.
