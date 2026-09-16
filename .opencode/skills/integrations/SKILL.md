---
name: integrations
description: How to add a third-party provider adapter. Port/adapter pattern, error mapping, vendor boundary rules.
---

# Integrations

Load this skill: when adding a third-party provider, exchange adapter, or external API connection.

Reference: `docs/INTEGRATION-ARCHITECTURE.md` for full port catalogue, boundary anatomy, guarantee matrix.

---

## The Rule

Third-party SDKs must not leak into business logic.

```
Business Logic -> Port -> Adapter -> Third Party
```

## When to Create a Port

Create when:
- Provider may be replaced (exchange, LLM, news source).
- External system is unreliable and you need error mapping.
- Business logic must be testable without the real system.
- SDK types are complex and should not pollute domain.

Do NOT create when:
- Simple utility with no replaceability need.
- SDK already well-contained and port adds no value.
- Creating it "just in case."

## Adapter Structure

Every provider lives in `infrastructure/providers/<vendor>/`:

```
config.py       Pydantic settings (api_key, base_url, timeouts)
client.py       Raw transport (httpx/ccxt). No domain types.
dtos.py         Vendor response shapes exactly as they arrive.
mapping.py      DTO -> domain entity. Only place vendor field names appear.
errors.py       Vendor exceptions -> DomainError subclass.
adapter.py      Implements the port using the five above.
```

## Error Mapping

Every vendor exception maps to exactly one `DomainError` subclass:

```python
from app.core.exceptions.taxonomy import (
    ProviderUnavailableError,
    RateLimitedError,
    ProviderTimeoutError,
)

def map_status(status: int, provider: str, message: str):
    if status == 429:
        return RateLimitedError(message, provider=provider)
    if status in (502, 503):
        return ProviderUnavailableError(message, provider=provider)
    if status == 504:
        return ProviderTimeoutError(message, provider=provider)
    return ProviderUnavailableError(message, provider=provider)
```

SDK exceptions must NEVER cross the adapter boundary.

## Feature-Specific vs Shared

Feature-specific adapter -> inside the owning module:
```
modules/marketdata/infrastructure/providers/binance/
```

Shared technical adapter -> under `app/infrastructure/`:
```
app/infrastructure/capability/database/
app/infrastructure/capability/redis/
```

## Testing Adapters

For every provider, test:
- Happy path: vendor DTO -> domain entity with correct types.
- 429 -> `RateLimitedError`, retryable=True.
- 5xx -> `ProviderUnavailableError`.
- Malformed payload -> `MalformedDataError`.

Use `vcrpy` for recorded vendor traffic. Scrub credentials before recording.
