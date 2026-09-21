# M13 exchange

Status: **implemented**; contracts frozen under `school-contracts-v14`.

- Contract packet: [`contracts/M13/PACKET.md`](../../../contracts/M13/PACKET.md)
- Code: `backend/modules/exchange/`, `frontend/src/features/exchange/`
- Progress: [`progress.md`](progress.md) · Handoff: [`handoff.md`](handoff.md)

Standalone requires broker, worker and object storage. Other business apps stay
out of `INSTALLED_APPS`; dependency ports bind to deterministic fakes.

```bash
python3 scripts/dev.py up M13 --profile standalone
python3 scripts/dev.py migrate M13 --profile standalone
python3 scripts/dev.py seed M13 --scenario baseline
python3 scripts/dev.py check M13 --suite standalone
```
