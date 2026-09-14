"""Structured logging (structlog) with correlation-id propagation."""

from __future__ import annotations

import logging
from contextvars import ContextVar

import structlog

correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def bind_context(*, cid: str | None = None, tid: str | None = None) -> None:
    """Temporary forcing helper (used by middleware & tests)."""
    if cid is not None:
        correlation_id.set(cid)


def _merge_contextvars(
    logger: structlog.typing.WrappedLogger,
    method_name: str,
    event_dict: structlog.typing.EventDict,
) -> structlog.typing.EventDict:
    if cid := correlation_id.get():
        event_dict.setdefault("correlation_id", cid)
    if tid := trace_id.get():
        event_dict.setdefault("trace_id", tid)
    return event_dict


def configure_logging(env: str, level: str = "INFO") -> None:
    """Async rendering keeps structured logs cheap; JSON in prod."""
    renderer: structlog.typing.Processor
    if env == "dev":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)

    shared: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        _merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _redact_secrets,
        renderer,
    ]

    logging.basicConfig(level=level.upper())
    structlog.configure(
        processors=shared,
        wrapper_class=structlog.make_filtering_bound_logger(int(getattr(logging, level.upper(), 20))),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _redact_secrets(
    logger: structlog.typing.WrappedLogger,
    method_name: str,
    event_dict: structlog.typing.EventDict,
) -> structlog.typing.EventDict:
    """Defensive redaction so secrets never reach logs."""
    return {
        k: ("***" if any(secret in k.lower() for secret in ("key", "secret", "token", "password")) else v)
        for k, v in event_dict.items()
    }


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
