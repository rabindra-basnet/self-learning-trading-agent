"""Shared provider registry — mechanism only, no vendor imports."""

from app.infrastructure.providers.registry import (
    ProviderFactory,
    ProviderRegistry,
    UnknownProviderError,
    provider_registry,
)

__all__ = [
    "ProviderFactory",
    "ProviderRegistry",
    "UnknownProviderError",
    "provider_registry",
]
