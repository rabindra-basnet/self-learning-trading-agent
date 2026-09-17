"""Shared infrastructure toolkit — infra-framework, never imported by domain/application.

These are policies (retry, backoff, circuit breaker, rate limiting) that
integration boundaries COMPOSE via the `Policy` facility.
"""

from app.infrastructure.tooling.http import JsonHttpClient, map_http_error
from app.infrastructure.tooling.policy import CircuitBreaker, Policy, RateLimiter, RetryPolicy

__all__ = [
    "CircuitBreaker",
    "JsonHttpClient",
    "Policy",
    "RateLimiter",
    "RetryPolicy",
    "map_http_error",
]
