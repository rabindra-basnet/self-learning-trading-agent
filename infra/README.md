# infra/ — Infrastructure

- `terraform/` — Cloudflare DNS, Workers, R2, WAF rules
- `docker-compose.yml` — VPS stack: engine, workers, postgres, clickhouse, redis, reverse proxy
- `.github/workflows/` — CI/CD pipelines (lint → typecheck → unit → integration → E2E → release)
- `runbooks/` — incident, kill-switch, exchange/LLM outage, restore, drift

See `docs/DEVOPS-PLAN.md` and `docs/SECURITY.md` §6.

Status: S0 — scaffolding only.