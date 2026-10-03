---
description: "F11 — Incidents list and incident detail (business hero screen) with fix → verify → resolve flow"
mode: agent
---
Read [Business edition](../../docs/12-BUSINESS-EDITION.md) sections 4, 7.3, 7.4 and [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) sections 4, 8.3. Reuse the reason block from the Why tab and the Try fixes drawer — do not duplicate them.

## Tasks
1. **Incidents list** `/incidents`: columns, filters (default "Open and investigating"), empty state, URL-synced filters, row → detail.
2. **Incident detail** `/incidents/:id`:
   - Header: title, severity (dot + word), conversations, estimated cost (with the tooltip from section 4.2), open since, owner; actions Notify team (confirm dialog → toast "Emailed 2 people about this incident."), Assign (popover), Status menu with valid transitions.
   - "What's going wrong" paragraph + likely cause in plain words ("Searching the help center" for retrieve, etc.) with the top 2 reasons and evidence.
   - **Fix panel**: numbered 3-step sequence. Step 1 opens the Try fixes drawer on the representative conversation; when a fix passes, step 2 enables "Verify on all N conversations" → progress → result sentence + stat chips; step 3 Resolve with a confirm dialog and optional note. Steps show done/active/locked states.
   - Timeline (newest at bottom), notification events link to the email preview drawer (build the preview drawer here as a shared component: sandboxed iframe `sandbox=""` with `srcdoc`, plus a Plain text tab).
   - Affected conversations table (customer message, agent reply in warning color, correct answer, likely cause chip) → conversation detail.
3. Loading, empty, error states with the spec's copy style.

## Acceptance
On mocks: open the high-severity incident → try fixes → "Search current articles only" passes → verify on all 14 → "Fix verified on 12 of 14 conversations…" → resolve; the timeline updates at each step. `npm run build` passes.
