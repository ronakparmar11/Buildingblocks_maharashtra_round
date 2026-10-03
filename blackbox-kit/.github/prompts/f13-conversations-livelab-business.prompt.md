---
description: "F13 — Conversation detail business labels, archived-article badges, Live lab simulate-traffic mode"
mode: agent
---
Read [Business edition](../../docs/12-BUSINESS-EDITION.md) sections 7.5, 7.7, 10 and the existing Run detail and Live lab code.

## Tasks
1. Conversation detail: vocabulary layer applied (Customer message, Agent reply, Correct answer per policy); passage cards show article title, updated date, and an "Archived" badge (`caution-tint`) for archived articles; "Part of incident: …" link when applicable.
2. Conversations list: customer message column instead of question in the nimbu workspace; filter by category.
3. Live lab in nimbu: segmented control "One conversation" / "Simulate traffic".
   - One conversation: Nimbu prepared questions pinned; plain-language failure presets ("Search returns an archived article", "Reads the wrong number from the article", "Final reply contradicts the facts").
   - Simulate traffic: inputs for message count and wrong-answer share, Start simulation, live counters (sent, answered wrong, incidents opened, emails sent) updating from the job, links "Open Mailpit inbox" and "Open Overview", and a link to each new incident as it appears.
4. Make sure the demo path in section 10 works end to end on mocks, and write it as a checklist in `frontend/DEMO.md`.

## Acceptance
Demo path from section 10 works on mocks without dead ends; `npm run build` passes.
