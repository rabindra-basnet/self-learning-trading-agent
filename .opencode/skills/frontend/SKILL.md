---
name: frontend
description: Next.js 16 App Router patterns for this trading agent dashboard. Load when building or modifying web/ directory components, pages, API routes, proxy.ts, or server actions.
---

# Frontend Skill -- Next.js 16

Trading agent dashboard. Server-first architecture.

---

## 1. Project Structure (vertical slices)

```
web/
  app/
    (auth)/                    # auth route group
      login/page.tsx
    (dashboard)/               # protected route group
      layout.tsx               # dashboard shell
      positions/page.tsx
      signals/page.tsx
      backtest/page.tsx
      settings/page.tsx
    api/
      health/route.ts          # health check
      positions/route.ts       # proxy to backend
      signals/route.ts
      llm/                     # LLM proxy
        chat/route.ts
        stream/route.ts
  components/                  # shared UI components
    ui/                        # primitives (Button, Card, Table)
    dashboard/                 # domain components (PositionTable, PnLChart)
    charts/                    # Recharts / D3 wrappers
  lib/                         # shared utilities
    auth.ts                    # auth() helper
    api.ts                     # backend client
    rate-limit.ts              # edge rate limiting
    utils.ts                   # cn(), formatCurrency(), etc.
  hooks/                       # shared React hooks
    useWebSocket.ts
    usePositions.ts
  types/                       # shared TypeScript types
    index.ts
  proxy.ts                     # edge auth + rate limiting (NOT middleware.ts)
  next.config.ts
  tailwind.config.ts
  tsconfig.json
  package.json
```

## 2. proxy.ts (NOT middleware.ts)

Next.js 16 renames `middleware.ts` to `proxy.ts` and `middleware` to `proxy`.

```typescript
// web/proxy.ts
import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

const secret = new TextEncoder().encode(process.env.JWT_SECRET);

const PUBLIC_PATHS = ["/login", "/api/health", "/_next"];

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const token = request.cookies.get("token")?.value;
  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  try {
    const { payload } = await jwtVerify(token, secret);
    const headers = new Headers(request.headers);
    headers.set("x-user-id", payload.sub ?? "");
    headers.set("x-user-role", (payload.role as string) ?? "viewer");
    return NextResponse.next({ request: { headers } });
  } catch {
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.cookies.delete("token");
    return response;
  }
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|login|api/health).*)"],
};
```

## 3. Server Components (default)

All components are Server Components by default. Only add `"use client"` when you need:
- `useState`, `useReducer`, `useEffect`
- Event handlers (`onClick`, `onSubmit`)
- Browser APIs (`window`, `localStorage`)
- Custom hooks that use state/effects

```typescript
// web/app/(dashboard)/positions/page.tsx -- Server Component
import { auth } from "@/lib/auth";
import { PositionTable } from "@/components/dashboard/PositionTable";
import { redirect } from "next/navigation";

export default async function PositionsPage() {
  const session = await auth();
  if (!session) redirect("/login");

  const positions = await fetch(`${process.env.BACKEND_URL}/api/positions`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
    next: { revalidate: 30 },  // ISR: refresh every 30s
  }).then((r) => r.json());

  return (
    <div>
      <h1>Positions</h1>
      <PositionTable positions={positions} />
    </div>
  );
}
```

```typescript
// web/components/dashboard/PositionTable.tsx -- Client Component
"use client";

import { useState } from "react";

interface Position {
  symbol: string;
  side: "long" | "short";
  entryPrice: number;
  quantity: number;
  unrealizedPnl: number;
}

export function PositionTable({ positions }: { positions: Position[] }) {
  const [sort, setSort] = useState<keyof Position>("symbol");

  return (
    <table>
      <thead>
        <tr>
          {Object.keys(positions[0] ?? {}).map((key) => (
            <th key={key} onClick={() => setSort(key as keyof Position)}>
              {key}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {positions
          .sort((a, b) => String(a[sort]).localeCompare(String(b[sort])))
          .map((p, i) => (
            <tr key={i}>
              <td>{p.symbol}</td>
              <td>{p.side}</td>
              <td>{p.entryPrice}</td>
              <td>{p.quantity}</td>
              <td className={p.unrealizedPnl >= 0 ? "text-green-500" : "text-red-500"}>
                {p.unrealizedPnl.toFixed(2)}
              </td>
            </tr>
          ))}
      </tbody>
    </table>
  );
}
```

## 4. Server Actions (mutations)

Use Server Actions for form submissions and mutations. Never call backend directly from client components.

```typescript
// web/app/(dashboard)/settings/actions.ts
"use server";

import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";

export async function updateRiskConfig(formData: FormData) {
  const session = await auth();
  if (!session) redirect("/login");

  const maxDrawdown = Number(formData.get("maxDrawdown"));
  const maxPositionSize = Number(formData.get("maxPositionSize"));

  const res = await fetch(`${process.env.BACKEND_URL}/api/risk/config`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ maxDrawdown, maxPositionSize }),
  });

  if (!res.ok) {
    return { error: "Failed to update risk config" };
  }

  revalidatePath("/settings");
  return { success: true };
}
```

```typescript
// web/app/(dashboard)/settings/page.tsx
import { updateRiskConfig } from "./actions";

export default function SettingsPage() {
  return (
    <form action={updateRiskConfig}>
      <input name="maxDrawdown" type="number" placeholder="Max Drawdown %" />
      <input name="maxPositionSize" type="number" placeholder="Max Position Size" />
      <button type="submit">Save</button>
    </form>
  );
}
```

## 5. Route Handlers (API routes)

```typescript
// web/app/api/positions/route.ts
import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

export async function GET() {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const res = await fetch(`${process.env.BACKEND_URL}/api/positions`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
  });

  const data = await res.json();
  return NextResponse.json(data);
}
```

## 6. LLM Streaming (SSE proxy)

```typescript
// web/app/api/llm/stream/route.ts
import { auth } from "@/lib/auth";
import { NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session) {
    return new Response("Unauthorized", { status: 401 });
  }

  const { messages } = await request.json();

  const response = await fetch(`${process.env.BACKEND_URL}/api/llm/chat`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ messages, stream: true }),
  });

  // Forward SSE stream to client
  return new Response(response.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
```

## 7. WebSocket (real-time updates)

```typescript
// web/hooks/useWebSocket.ts
"use client";

import { useEffect, useRef, useState } from "react";

export function useWebSocket(url: string) {
  const [data, setData] = useState<unknown>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket(url);

    ws.current.onmessage = (event) => {
      setData(JSON.parse(event.data));
    };

    ws.current.onerror = () => {
      console.error("WebSocket error");
    };

    return () => {
      ws.current?.close();
    };
  }, [url]);

  return data;
}
```

## 8. Styling

- Tailwind CSS v4 (utility-first)
- `cn()` for conditional classes: `import { cn } from "@/lib/utils"`
- Dark mode via `class` strategy
- Responsive: mobile-first, breakpoints `sm:`, `md:`, `lg:`

## 9. Environment Variables

```bash
# web/.env.local
JWT_SECRET=...
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

- `NEXT_PUBLIC_` = exposed to client (only for non-sensitive values like WS URL)
- Everything else = server only

## 10. Testing

```bash
# Unit
pnpm --dir web test

# E2E
pnpm --dir web exec playwright test

# Type check
pnpm --dir web exec tsc --noEmit

# Lint
pnpm --dir web lint
```

- Vitest for unit tests
- Playwright for E2E
- Test Server Components with `renderToString` from `react-dom/server`
- Mock `fetch` calls in Server Component tests

## 11. Key Rules

- Never use `pages/` router -- App Router only
- Never use `getServerSideProps` -- use Server Components
- Never store secrets in `NEXT_PUBLIC_` vars
- Never call backend from client components -- use Server Actions or Route Handlers
- Never use `jsonwebtoken` in proxy.ts -- use `jose`
- Always verify auth at proxy AND page/route handler (defense in depth)
- Every mutation goes through Server Actions
- Data fetching in Server Components with `fetch()` + `next: { revalidate }` for ISR
