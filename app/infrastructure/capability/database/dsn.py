"""Translate libpq-style DSN options into what asyncpg's `connect()` accepts.

Neon (and most managed Postgres) hands out `?sslmode=require&channel_binding=require`.
asyncpg understands those when it parses the DSN itself, but SQLAlchemy's asyncpg
dialect forwards URL query parameters as `connect()` keyword arguments, and
`connect()` has no `sslmode`/`channel_binding` parameter -> `TypeError` at
startup. Map the libpq spelling onto asyncpg's own spelling instead of making
every deployment rewrite its DSN.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import make_url

_CONNECT_KWARGS = {"sslmode": "ssl"}
_IGNORED_OPTIONS = {"channel_binding"}


def normalize_asyncpg_dsn(dsn: str) -> tuple[str, dict[str, Any]]:
    """Return an asyncpg-safe DSN plus the `connect_args` it implies.

    `sslmode` becomes `connect_args["ssl"]`; options asyncpg knows nothing about
    and that only affect libpq negotiation (`channel_binding`) are dropped.
    """
    url = make_url(dsn)
    connect_args: dict[str, Any] = {}
    for option, value in url.query.items():
        translated = _CONNECT_KWARGS.get(option)
        if translated is not None:
            connect_args[translated] = value[-1] if isinstance(value, tuple) else value
    cleaned = url.difference_update_query([*_CONNECT_KWARGS, *_IGNORED_OPTIONS])
    return cleaned.render_as_string(hide_password=False), connect_args
