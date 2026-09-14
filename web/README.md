# web/ — Unified Next.js 16 App

Single package = **dashboard UI + API edge (Route Handlers) + LLM proxy + Edge middleware**. Deploys as one unit to **Cloudflare Workers** (via `@opennextjs/cloudflare`) with the **same package deployable to Vercel** unchanged.

Start locally: `pnpm install && pnpm dev` (engine runs via `docker compose -f infra/docker-compose.yml up`).

See `docs/SYSTEM-DESIGN.md` §8–§12 and `docs/SDLC-PLAN.md` §2.5.

Status: S0 — not scaffolded yet. Planned for Sprint S6/S7.