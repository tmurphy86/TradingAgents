# tests/ — Test Suite

All tests run in the Docker test container (`api/Dockerfile` stage `test` — installs `.[api,dev]`, sets `PYTHONPATH=/build`). Same container locally and in CI.

```bash
docker compose run --rm test                                  # default: unit + smoke + regression
docker compose run --rm test pytest tests/ -v                 # all non-integration, verbose
docker compose run --rm test pytest tests/ -m integration -v  # needs real API keys
python -m pytest tests/ -m "unit or smoke" -q                 # quick local, no Docker
```

| Marker | Covers | Needs API keys |
|---|---|---|
| `unit` | Isolated logic, no external calls | No |
| `smoke` | Quick sanity checks | No |
| `regression` | FastAPI endpoint shape, SSE streaming, watchlist CRUD — all mocked | No |
| `integration` | Live LLM / data provider calls | Yes |

## Rules

- `conftest.py` injects placeholder API keys so unit/smoke/regression never fail on missing secrets — don't read real keys in those tiers.
- Every new test gets exactly one marker; unmarked tests are a bug.
- Coverage areas: analyst execution planning, LLM providers, env overrides, checkpoint/resume, memory log, model catalog, crypto mode, ticker path-traversal security, API endpoints, SSE, watchlist CRUD.
- Changed API or SSE behavior requires a `regression` test in the same PR.
