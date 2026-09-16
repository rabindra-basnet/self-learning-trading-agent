# Security Plan

Status: DRAFT . Part of SDLC-PLAN.md §2.7 / SYSTEM-DESIGN.md §10

---

## 1. Principles

- **Secrets never in code, logs, or commits.** Env-injected at runtime.
- **Least privilege**: per-slice DB users, RBAC (viewer/analyst/admin).
- **Fail-closed**: risk/execution and auth default deny.
- **Defense in depth:** CF WAF + edge auth + app validation + DB isolation.

## 2. Threat Model (STRIDE sketch; full version in Phase 2)

| Threat | Mitigation |
|---|---|
| Spoofing (unauthorized API) | JWT (short-lived) + refresh; edge middleware verify; RBAC |
| Tampering (message/order injection) | typed Pydantic validation; audit log; order id + dedup keys; HMAC on callbacks |
| Repudiation | structured audit log with correlation_id for every decision/order |
| Info disclosure | keys/analysis server-side only; no secrets in API responses; logs redact |
| DoS | CF WAF rate-limits, bulkheads, timeouts, queue bounds |
| Elevation | RBAC enforced at router guard + application layer |

## 3. Secrets Handling

- `.env.example` non-secret only; `wrangler secret put`; Vercel env; SOPS/age optional.
- LLM keys: reach only `web/api/llm` (server) or engine `llm` slice -- never the browser.
- `git secrets`/`gitleaks` in pre-commit + CI; rotation runbook.

## 4. Application Security Checklist

- [ ] Pydantic v2 validation everywhere (no `Any` on inputs)
- [ ] No SQL string interpolation (ORM/parameterized only)
- [ ] `pip-audit` / `npm audit` gates; pinned deps
- [ ] Bandit + Semgrep (SAST) in CI; ZAP (DAST) at release
- [ ] OWASP ZAP basic + authenticated scans
- [ ] Rate limiting on auth endpoints; generic error messages
- [ ] CORS locked to dashboard origin
- [ ] WS auth required; per-connection RBAC scope

## 5. Trading Security (safety-critical)

- Risk gate **fail-closed** (no default allow).
- Kill-switch: clears positions + halts all trading; idempotent; full audit.
- Paper mode default; production go-live gated by config + manual unlock.
- Order dedup/idempotency; no partial-fill ambiguity (state machine).
- Slippage/execution guardrails before any live order.

## 6. Infrastructure

- VPS hardened (SSH key-only, fail2ban, minimal packages, automatic updates).
- CF WAF managed rules + custom rate-limits; TLS everywhere.
- Backup encrypted at rest; R2 private buckets.
- Per-slice DB credentials; app user without DDL in prod.