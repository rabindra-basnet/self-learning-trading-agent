---
description: Add a third-party provider adapter
---

Load the integrations skill first:

skill({ name: "integrations" })

Add the following provider integration:

$ARGUMENTS

Follow the port/adapter pattern:
1. Check if an existing port already fits
2. Create adapter in infrastructure/providers/<vendor>/
3. Map vendor errors to DomainError subclasses
4. Wire in di.py
5. Test the adapter separately
