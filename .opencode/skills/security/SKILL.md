---
name: security
description: Security checklist and cybersec flow for this trading agent. Load when handling secrets, auth, API keys, deployment, or security audits.
---

# Security Flow

Trading agent = financial system. Security is not optional.

---

## 1. Secret Management

### Never

- Commit secrets to git
- Log API keys, tokens, passwords
- Put secrets in response bodies
- Store secrets in code
- Record secrets in vcrpy cassettes

### Always

- Use `SecretStr` for all sensitive config
- Read secrets via `.get_secret_value()` at composition root only
- Use `.env` for local, `wrangler secret put` for CF, Vercel env for fallback
- Filter secrets in vcrpy before recording:
  ```python
  vcr = vcr.VCR(
      filter_headers=["X-MBX-APIKEY", "authorization"],
      filter_query_parameters=["signature", "api_key"],
  )
  ```
- Run `gitleaks detect` before every commit

### Config pattern

```python
# app/core/config/settings.py
class BinanceConfig(BaseModel):
    api_key: SecretStr
    api_secret: SecretStr
    base_url: str = "https://api.binance.com"
```

```python
# app/di.py (composition root only)
key = settings.binance.api_key.get_secret_value()
```

## 2. Authentication & Authorization

### JWT

- Short-lived access tokens (15 min default)
- Refresh token rotation
- Edge-safe verification using `jose` (NOT `jsonwebtoken` -- Node.js only)
- Never store tokens in localStorage (use httpOnly cookies or in-memory)
- **Defense in depth**: enforce at proxy + page/route handler (middleware-only auth is bypassable via CVE-2026-64642, CVE-2026-44575)

### Next.js 16: proxy.ts (not middleware.ts)

In Next.js 16, `middleware.ts` was renamed to `proxy.ts` and the exported function from `middleware` to `proxy`. Use `npx @next/codemod@canary middleware-to-proxy` to migrate.

Edge runtime has no Node.js APIs -- use `jose` for JWT verification, never `jsonwebtoken`.

```typescript
// web/proxy.ts
import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

const secret = new TextEncoder().encode(process.env.JWT_SECRET);

const PUBLIC_PATHS = ["/login", "/api/health", "/_next"];

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip public paths
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Rate limit check (edge-compatible: in-memory or Cloudflare rate limiting)
  const ip = request.headers.get("x-forwarded-for") ?? "unknown";
  if (isRateLimited(ip)) {
    return NextResponse.json({ error: "Too many requests" }, { status: 429 });
  }

  // JWT verification
  const token = request.cookies.get("token")?.value;
  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  try {
    const { payload } = await jwtVerify(token, secret);

    // Attach user context for downstream handlers
    const headers = new Headers(request.headers);
    headers.set("x-user-id", payload.sub ?? "");
    headers.set("x-user-role", payload.role ?? "viewer");

    return NextResponse.next({ request: { headers } });
  } catch {
    // Invalid or expired token
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.cookies.delete("token");
    return response;
  }
}

export const config = {
  matcher: [
    // Match all paths except public ones
    "/((?!_next/static|_next/image|favicon.ico|login|api/health).*)",
  ],
};
```

### Defense in depth: page-level auth check

Proxy auth can be bypassed (CVE-2026-64642, CVE-2026-44575). Every protected page/route must also verify the session:

```typescript
// web/app/dashboard/page.tsx
import { auth } from "@/lib/auth";

export default async function DashboardPage() {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }
  return <Dashboard user={session.user} />;
}
```

```typescript
// web/app/api/positions/route.ts
import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

export async function GET() {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  // ... fetch positions
}
```

### API Keys

- Hashed before storage (never plaintext)
- Key prefix stored for identification, full key shown once at creation
- Rate limiting per key
- Key rotation support

### RBAC

| Role | Can Do |
|---|---|
| viewer | Read dashboard, view positions |
| analyst | Read backtests, run analysis |
| admin | Configure strategies, kill switch, manage keys |

Enforce at proxy + page + application layer. Never rely on UI-only restrictions.

## 3. Rate Limiting (3 layers)

### Layer 1: Cloudflare WAF

- Managed rate-limiting rules on `/api/*`
- Bot detection enabled
- Geo-blocking if not needed

### Layer 2: Edge proxy (proxy.ts)

```typescript
// web/lib/rate-limit.ts
const rateLimit = new Map<string, { count: number; reset: number }>();

export function isRateLimited(key: string, limit = 100, windowMs = 60_000): boolean {
  const now = Date.now();
  const entry = rateLimit.get(key);

  if (!entry || now > entry.reset) {
    rateLimit.set(key, { count: 1, reset: now + windowMs });
    return false;
  }

  entry.count++;
  return entry.count > limit;
}
```

### Layer 3: Application (FastAPI)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/api/positions")
@limiter.limit("30/minute")
async def get_positions(request: Request):
    ...
```

## 3. Input Validation

- Pydantic v2 on every inbound schema
- No `Any` types on inputs
- Symbol format validation: `Field(pattern=r"^[A-Z0-9]+/[A-Z0-9]+$")`
- Numeric bounds: `Field(ge=0, le=1000000)`
- String length limits: `Field(min_length=1, max_length=256)`
- No raw SQL interpolation (ORM/parameterized only)

## 4. API Security

- CORS locked to dashboard origin
- Rate limiting at 3 layers: Cloudflare WAF + proxy.ts + FastAPI
- Generic error messages (no stack traces in production)
- OpenAPI schema not exposed in production
- WebSocket auth required, per-connection RBAC scope
- All protected routes must verify auth at proxy AND page/route handler (defense in depth)

## 5. Dependency Security

```bash
# Python
pip-audit

# JavaScript
npm audit

# Before every merge
pip-audit && npm audit && gitleaks detect
```

Pin dependencies in `pyproject.toml` and `package.json`. Review updates before merging.

## 6. Trading Security (safety-critical)

- Risk gate is **fail-closed** (no default allow)
- Kill-switch: clears positions + halts trading, idempotent, full audit
- Paper mode default; production go-live gated by config + manual unlock
- Order dedup/idempotency
- Slippage/execution guardrails before any live order
- **No order is ever sent to live market during CI** -- paper only

## 7. Data Protection

- Encrypt backups at rest
- Per-slice DB credentials
- App user without DDL in prod
- Structured audit log with correlation_id for every decision/order
- Log redaction for sensitive fields

## 8. Infrastructure

- VPS: SSH key-only, fail2ban, minimal packages, automatic updates
- Cloudflare: WAF managed rules, custom rate-limits, TLS everywhere
- Docker: non-root user, minimal base image, no shell in production
- Secrets in env/secret-manager, never in Dockerfile or docker-compose

## 9. Incident Response

| Severity | Response Time | Action |
|---|---|---|
| Critical (secret leak, unauthorized access) | Immediate | Rotate keys, revoke access, audit logs |
| High (service down, data corruption) | 1 hour | Failover, restore from backup, notify |
| Medium (degraded performance) | 4 hours | Investigate, mitigate, monitor |
| Low (non-critical bug) | Next sprint | Fix in normal flow |

## 10. Pre-Commit Checklist

```bash
# Secrets
gitleaks detect

# Dependencies
pip-audit

# No secrets in code
grep -rn "api_key\|secret\|password\|token" app/ --include="*.py" | grep -v "SecretStr\|get_secret_value\|settings\.\|config\.\|__pycache__"

# No SDK leaks in domain
grep -rn "import ccxt\|import redis\|import sqlalchemy" app/modules/*/domain/

# Architecture
uv run lint-imports
```
