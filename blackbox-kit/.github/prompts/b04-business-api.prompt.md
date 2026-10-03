---
description: "B04 — Business API endpoints: workspaces, overview, incidents, notifications, settings, simulate"
mode: agent
---
Read [Business edition](../../docs/12-BUSINESS-EDITION.md) section 8, and the existing `blackbox/api/`.

## Tasks
1. Add `workspace` query param to all existing endpoints (default `hotpot`), filtering by run/task workspace.
2. Implement every endpoint in section 8 with pydantic response models in `schemas.py`. Incident runs include `customer_message`, `agent_reply`, `correct_answer`.
3. Jobs: verify-fix and simulate run on the existing job registry with progress fields.
4. `PATCH /incidents/{id}` validates status transitions and writes events (and triggers rule evaluation).
5. Notifications status never returns the password; preview returns stored html/text.
6. Start the digest scheduler and the notification worker on app startup; stop them cleanly on shutdown.
7. Tests with TestClient + temp DB + fake SMTP: overview shape, incident list/detail, patch status, notify endpoint logs a notification, recipients CRUD with email validation, rules update, simulate job progresses.

## Rules
Do not modify `frontend/`. Keep existing endpoints backward compatible.

## Acceptance
`make test` passes; `/docs` lists all new endpoints; with Mailpit running, `POST /api/incidents/{id}/notify` delivers an email.
