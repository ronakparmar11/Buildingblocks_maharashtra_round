---
description: "F08 — Live lab (demo driver)"
mode: agent
---
Read [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) sections 7.3 and 12. Reuse `ExecutionRoute` (`revealUpTo`), `FdrTape`, the diagnosis playback, and the Try fixes logic from F04 (extract shared hooks if needed rather than duplicating).

## Goal
A projector-friendly page that runs the whole loop: pick a question → optionally break something → run → watch it fail → find the cause → try fixes → compare.

## Tasks
1. Numbered steps 1–4 with the active/done states from section 12.
2. Question combobox with "Prepared for demo" pinned group (the three hero runs' questions); failure picker with plain-language types + target step dropdown from `useFaultTargets` (disabled for "No failure").
3. "Run the agent" large orange button → live run job; nodes appear on the route one by one as steps arrive.
4. Outcome line in `text-3xl`.
5. On failure: automatic diagnosis with the playback, then step 3 shows the most likely cause and its top reason with a "Try fixes" button; step 4 streams fix attempts and ends with the result and a Compare link.
6. "Run again" resets the page; "Open full run" links to Run detail.
7. Everything is larger here: base text 16px, buttons 44px tall.

## Acceptance
- Full loop with hero question 1 + distractor retrieval at `q1/retrieve#0` completes in under 60 seconds with mocks and ends with a fix found.
- Readable from 4 meters on a 1366×768 projector.
- `npm run build` passes.
