# M12 files

Status: **implemented** (contracts frozen under `school-contracts-v13`).

- Contract packet: [`contracts/M12/PACKET.md`](../../../contracts/M12/PACKET.md)
- Backend: `backend/modules/files/`
- Frontend: `frontend/src/features/files/` (review + parent viewer)
- Standalone: `python3 scripts/dev.py up M12 --profile standalone`

## Behaviour

Private upload quarantine, answer-sheet decode/compress (WebP q85, long-edge
2400), teacher quality confirmation, evidence pin, grant-based private reads,
economical source purge (confirm + backup verify + 7-day grace + no hold).
Imports/reports preserve bytes without the quality pipeline.

## PENDING

Real M01 auth/2FA, Assessment publication gates, independent backup restoration,
production object lifecycle rules.
