#!/usr/bin/env python3
"""Scaffold a new vertical slice in app/modules/<slice>/ following repo house style.

Creates the hexagonal directory tree with stub files, then prints the import-linter
contract block to paste into pyproject.toml plus the composition-root edits the
script deliberately does not make for you (di.py and routers.py are hand-wired so
the ordering and dependencies stay deliberate).

Usage:
    python .agents/scripts/new_slice.py sentiment --repo .
    python .agents/scripts/new_slice.py sentiment --repo . --dry-run
    python .agents/scripts/new_slice.py --about "social media sentiment scoring" --repo .
    python .agents/scripts/new_slice.py --about "order execution via exchange API" --repo . --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LAYERS = ("presentation", "application", "domain", "infrastructure", "contracts")

# Known slice patterns: maps keywords in --about to (slice_name, entities, ports, events)
SLICE_PATTERNS: dict[str, dict[str, str]] = {
    "sentiment": {
        "name": "sentiment",
        "description": "social media and news sentiment analysis",
        "entity": "SentimentScore",
        "port": "SentimentStore",
        "event": "SentimentComputed",
        "service": "SentimentService",
        "route_prefix": "/sentiment",
    },
    "trading": {
        "name": "trading",
        "description": "order execution and position management",
        "entity": "TradeOrder",
        "port": "TradeStore",
        "event": "TradeExecuted",
        "service": "TradingService",
        "route_prefix": "/trading",
    },
    "llm": {
        "name": "llm",
        "description": "LLM-powered analysis and reasoning",
        "entity": "AnalysisResult",
        "port": "LLMReasoner",
        "event": "AnalysisCompleted",
        "service": "LLMService",
        "route_prefix": "/llm",
    },
    "alerts": {
        "name": "alerts",
        "description": "alert rules and notification delivery",
        "entity": "AlertRule",
        "port": "AlertStore",
        "event": "AlertTriggered",
        "service": "AlertService",
        "route_prefix": "/alerts",
    },
    "dashboard": {
        "name": "dashboard",
        "description": "dashboard projections and live views",
        "entity": "DashboardSnapshot",
        "port": "DashboardStore",
        "event": "DashboardUpdated",
        "service": "DashboardService",
        "route_prefix": "/dashboard",
    },
    "history": {
        "name": "history",
        "description": "trade history and PnL analytics",
        "entity": "TradeRecord",
        "port": "HistoryStore",
        "event": "HistoryUpdated",
        "service": "HistoryService",
        "route_prefix": "/history",
    },
    "selfimprovement": {
        "name": "selfimprovement",
        "description": "strategy optimization and model promotion",
        "entity": "OptimizationRound",
        "port": "OptimizationStore",
        "event": "RoundCompleted",
        "service": "SelfImprovementService",
        "route_prefix": "/self-improve",
    },
}


def pascal(slice_name: str) -> str:
    return "".join(part.capitalize() for part in slice_name.split("_"))


def guess_slice_name(about: str) -> str | None:
    """Try to match --about text to a known slice pattern."""
    lower = about.lower()
    for keyword, pattern in SLICE_PATTERNS.items():
        if keyword in lower:
            return pattern["name"]
    # Fallback: extract first meaningful word
    words = re.findall(r"[a-z]+", lower)
    for word in words:
        if len(word) >= 3 and word not in ("for", "the", "and", "via", "with", "using"):
            return word
    return None


def get_pattern(slice_name: str, about: str | None) -> dict[str, str]:
    """Get the template pattern for a slice, either from known patterns or from --about."""
    if slice_name in SLICE_PATTERNS:
        return SLICE_PATTERNS[slice_name]

    cls = pascal(slice_name)
    desc = about or f"{slice_name} processing"
    return {
        "name": slice_name,
        "description": desc,
        "entity": f"{cls}Record",
        "port": f"{cls}Store",
        "event": f"{cls}Updated",
        "service": f"{cls}Service",
        "route_prefix": f"/{slice_name.replace('_', '-')}",
    }


def files_for(slice_name: str, pattern: dict[str, str]) -> dict[str, str]:
    cls = pascal(slice_name)
    mod = f"app.modules.{slice_name}"
    entity = pattern["entity"]
    port = pattern["port"]
    event = pattern["event"]
    service = pattern["service"]
    route_prefix = pattern["route_prefix"]

    return {
        "__init__.py": f'"""{slice_name} slice — {pattern["description"]}."""\n',
        "domain/__init__.py": "",
        "domain/entities.py": f'''"""{slice_name} domain: normalized models (provider-independent)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class {entity}(BaseModel):
    """Normalized entity for {pattern["description"]}."""

    observed_at: datetime
''',
        "domain/ports.py": f'''"""{slice_name} ports — provider-independent capability contracts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from {mod}.domain.entities import {entity}


class {port}(Protocol):
    async def append(self, records: Sequence[{entity}]) -> int: ...

    async def latest(self, n: int = 100) -> list[{entity}]: ...
''',
        "domain/events.py": f'''"""{slice_name} domain events (normalized) — the cross-slice surface."""

from __future__ import annotations

from app.core.messaging.bus import DomainEvent
from {mod}.domain.entities import {entity}


class {event}(DomainEvent):
    records: list[{entity}]
''',
        "application/__init__.py": "",
        "application/services.py": f'''"""{slice_name} application: use-cases. Depend only on ports; normalize at boundaries."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.common.result import Ok, Result
from app.core.exceptions.taxonomy import DomainError
from app.core.logging.setup import get_logger
from app.core.messaging.bus import EventBus
from {mod}.domain.entities import {entity}
from {mod}.domain.events import {event}
from {mod}.domain.ports import {port}

logger = get_logger("{slice_name}.service")


@dataclass(frozen=True, slots=True)
class {cls}Summary:
    stored: int


class {service}:
    def __init__(self, store: {port}, bus: EventBus) -> None:
        self._store = store
        self._bus = bus

    async def process(self, records: list[{entity}]) -> Result[{cls}Summary, DomainError]:
        stored = await self._store.append(records)
        await self._bus.publish({event}(records=records))
        logger.info("{slice_name}_processed", stored=stored)
        return Ok({cls}Summary(stored=stored))
''',
        "infrastructure/__init__.py": "",
        "infrastructure/stores/__init__.py": "",
        "infrastructure/stores/in_memory.py": f'''"""In-memory {port} — the default adapter until a real store lands."""

from __future__ import annotations

from collections.abc import Sequence

from {mod}.domain.entities import {entity}


class InMemory{cls}Store:
    def __init__(self) -> None:
        self._records: list[{entity}] = []

    async def append(self, records: Sequence[{entity}]) -> int:
        self._records.extend(records)
        return len(records)

    async def latest(self, n: int = 100) -> list[{entity}]:
        return self._records[-n:]
''',
        "presentation/__init__.py": "",
        "presentation/schemas.py": f'''"""{slice_name} presentation schemas (transport layer — never provider types)."""

from __future__ import annotations

from pydantic import BaseModel


class {cls}SummaryResponse(BaseModel):
    stored: int
''',
        "presentation/routes.py": f'''"""{slice_name} inbound adapter (FastAPI)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.exceptions.taxonomy import http_status_for
from {mod}.presentation.schemas import {cls}SummaryResponse
from {mod}.application.services import {service}

router = APIRouter(prefix="{route_prefix}", tags=["{slice_name}"])


def _service(request: Request) -> {service}:
    return request.app.state.container.resolve({service})


@router.post("/process", response_model={cls}SummaryResponse, status_code=201)
async def process(request: Request) -> {cls}SummaryResponse:
    result = await _service(request).process([])
    if result.is_err:
        error = result.error_value()
        raise HTTPException(status_code=http_status_for(error), detail=error.message)
    return {cls}SummaryResponse(stored=result.ok_value().stored)
''',
        "contracts/__init__.py": f'''"""{slice_name} public contracts — the only import surface for other slices."""

from {mod}.domain.events import {event}

__all__ = ["{event}"]
''',
    }


def existing_slices(modules_dir: Path) -> list[str]:
    if not modules_dir.is_dir():
        return []
    return sorted(
        p.name
        for p in modules_dir.iterdir()
        if p.is_dir() and not p.name.startswith("_") and (p / "domain").is_dir()
    )


def contract_block(slice_name: str, others: list[str]) -> str:
    forbidden = [f'  "app.modules.{other}",' for other in others]
    forbidden.append('  "app.infrastructure",')
    return f"""[[tool.importlinter.contracts]]
name = "{slice_name} stays internal to its slice"
type = "forbidden"
source_modules = [
  "app.modules.{slice_name}.domain",
  "app.modules.{slice_name}.application",
  "app.modules.{slice_name}.presentation",
]
forbidden_modules = [
{chr(10).join(forbidden)}
]"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slice_name", nargs="?", help="snake_case slice name, e.g. sentiment")
    parser.add_argument("--about", help="describe what to build — script picks slice name and customizes stubs")
    parser.add_argument("--repo", default=".", help="path to the repo root (default: cwd)")
    parser.add_argument("--dry-run", action="store_true", help="print what would be created")
    args = parser.parse_args()

    # Resolve slice name
    if args.about and not args.slice_name:
        slice_name = guess_slice_name(args.about)
        if not slice_name:
            print("error: could not guess a slice name from the description; provide one explicitly", file=sys.stderr)
            return 1
        print(f"detected slice: {slice_name} (from: \"{args.about}\")")
    elif args.slice_name:
        slice_name = args.slice_name
    else:
        parser.error("provide a slice name or --about description")

    if not re.fullmatch(r"[a-z][a-z0-9_]*", slice_name):
        print(f"error: '{slice_name}' must be snake_case (lowercase, digits, underscores)", file=sys.stderr)
        return 1

    repo = Path(args.repo).expanduser().resolve()
    modules = repo / "app" / "modules"
    if not modules.is_dir():
        print(f"error: {modules} not found — is --repo pointing at the repo root?", file=sys.stderr)
        return 1

    target = modules / slice_name
    if target.exists():
        print(f"error: {target} already exists; extend it instead of scaffolding over it", file=sys.stderr)
        return 1

    others = existing_slices(modules)
    pattern = get_pattern(slice_name, args.about)
    files = files_for(slice_name, pattern)

    if args.dry_run:
        for rel in files:
            print(f"would create app/modules/{slice_name}/{rel}")
    else:
        for layer in LAYERS:
            (target / layer).mkdir(parents=True, exist_ok=True)
        for rel, content in files.items():
            path = target / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            print(f"created app/modules/{slice_name}/{rel}")

    cls = pascal(slice_name)
    print(f"""
--- next: paste into [tool.importlinter] in pyproject.toml ---

{contract_block(slice_name, others)}

--- then, in the SAME edit ---

1. Append "app.modules.{slice_name}" to the forbidden_modules of each existing slice contract:
   {", ".join(others) or "(none yet)"}
2. Append these to the "Domain and application layers are provider-free" contract's source_modules:
   "app.modules.{slice_name}.domain",
   "app.modules.{slice_name}.application",

--- wire the composition root (app/di.py) ---

    # --- {slice_name} {"-" * max(0, 56 - len(slice_name))}
    {slice_name}_store = InMemory{cls}Store()
    container.register_instance(InMemory{cls}Store, {slice_name}_store)
    container.register(
        {pattern["service"]},
        lambda: {pattern["service"]}({slice_name}_store, _bus(container)),
    )

--- include the router (app/routers.py) ---

    from app.modules.{slice_name}.presentation.routes import router as {slice_name}_router
    api_router.include_router({slice_name}_router)

--- verify ---

    uv run lint-imports && uv run ruff check app && uv run mypy app && uv run pytest -q
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
