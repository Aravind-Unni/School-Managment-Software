# VPS deploy status

| Item | Status |
|---|---|
| `infra/prod/` compose, nginx, images, RUNBOOK | ready in repo |
| `.env` from `infra/prod/.env.example` | awaiting operator secrets |
| DNS + TLS (Certbot) | awaiting domain + email |
| SSH to VPS | awaiting access |
| `bootstrap_owner` | command exists; run after migrate on VPS |
| School smoke + checklist signatures | not started |
| `RELEASE_ACCEPTED` | **false** — do not flip without signed checklist |

Supply: SSH host, domain, TLS contact email, campus `SCHOOL_ID` UUID, school signatory name.
