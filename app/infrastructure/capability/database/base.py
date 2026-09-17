"""Declarative base shared by every SQLAlchemy model in this application.

One `Base` means one `Base.metadata`, which is what Alembic autogenerate reads
(`migrations/env.py`), so a new model only has to inherit from this class.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
