# app/ -- Python Trading Engine

VSA modular monolith (FastAPI). Vertical slices in `app/modules/<slice>/` with `{presentation, application, domain, infrastructure, contracts}/`; shared kernel in `app/core/`; composition root in `app/di.py` and `app/workers/`.

See `docs/SYSTEM-DESIGN.md` §3-§6 and `docs/SDLC-PLAN.md` §2.1-§2.4.

Status: S0 -- scaffolding only. No business code until the SDLC gate clears (see `docs/SDLC-PLAN.md` §3).