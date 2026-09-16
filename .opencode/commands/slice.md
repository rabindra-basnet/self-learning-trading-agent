---
description: Add or modify a feature in a module
---

Load the backend-slice skill first:

skill({ name: "backend-slice" })

Implement the following feature:

$ARGUMENTS

Follow the outside-in order: domain -> ports -> use-case -> adapter -> presentation -> DI.
Use existing patterns from the module. Prefer smallest correct change.
