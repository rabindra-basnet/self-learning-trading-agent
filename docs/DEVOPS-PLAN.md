# DevOps Plan

Status: DRAFT . Part of SDLC-PLAN.md §5

---

## 1. Version Control

- Git, trunk-based development with short-lived feature branches.
- **Conventional Commits** (`feat:, fix:, test:, chore:, docs:, ci:`).
- Branch naming: `feat/<jira>/<kebab>`, `fix/…`, `test/…`.

## 2. CI (GitHub Actions)

Pipeline (gated, fail-fast):
`lint (ruff/eslint/prettier) -> typecheck (mypy strict / tsc) -> unit (core) -> integration (testcontainers + vcrpy) -> coverage gate >=85% -> SAST (bandit/semgrep) -> build image (multi-stage, python:3.12-slim) -> E2E smoke (Playwright + API E2E on preview) -> contract checks`

- Nightly full workflow: full integration + E2E + backtest regression + load/chaos on staging.
- SCA (`pip-audit`/`npm audit`) + secrets scan (`gitleaks`) on every PR.

## 3. CD

| Artifact | Deploy | Rollback |
|---|---|---|
| Python engine | watchtower on minimal VPS; blue-green restart w/ health check | keep previous image tagged |
| `web/` | `opennextjs-cloudflare build && opennextjs-cloudflare deploy` (primary); Vercel fallback (same package) | deploy previous commit |
| DNS/Workers/R2 | Terraform plan/apply | terraform state |

## 4. IaC & Infrastructure

- `infra/terraform/` -- CF DNS, Workers, R2 buckets, WAF rules.
- `infra/docker-compose.yml` -- VPS stack: engine, workers, postgres, clickhouse, redis, caddy/traefik.
- Roles per env: `dev`, `staging` (paper), `prod` (gated live).

## 5. Configuration & Secrets

- `pydantic-settings` + `.env.example`; committed values only non-secret.
- Secrets: `.env` -> container env (VPS), `wrangler secret put` (CF), Vercel env (fallback). SOPS/age encrypted in repo optional.
- **Never log or commit secrets.** gitleaks enforced.

## 6. Backup / Recovery

- Postgres `pg_dump` -> R2 nightly (+ WAL archiving).
- ClickHouse `BACKUP` -> R2 nightly.
- Tested restore runbook monthly.

## 7. SLOs & Alerts

| SLO | Target |
|---|---|
| Engine uptime | 99.5% |
| API latency p95 | < 300 ms |
| WS latency p95 | < 150 ms |
| Order failures | 0 silent (every submission has ack/fill/reject logged) |

Alert channels: dashboards (Grafana), alert slice (Slack/Telegram/webhook).

## 8. Runbooks (`infra/runbooks/`)

- incident template + severity levels
- kill-switch (manual + API)
- exchange outage (failover adapter)
- LLM outage (fallback chain)
- data drift (re-champion / revert)
- restore / replay / redeploy / scale-up