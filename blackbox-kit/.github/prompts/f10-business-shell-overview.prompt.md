---
description: "F10 — Business shell: workspace switcher, vocabulary layer, new navigation, Overview page, mocks for new endpoints"
mode: agent
---
Read [Business edition](../../docs/12-BUSINESS-EDITION.md) sections 2, 7.1, 7.2, 8 and [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) sections 3, 4, 13, 14. Reuse existing components; the visual identity is unchanged.

## Tasks
1. **Types and mocks**: add every new response type from section 8 to `src/api/types.ts` (match `blackbox/api/schemas.py` if those models exist), hooks in `hooks.ts`, and mock handlers with a realistic Nimbu Living dataset: ~200 conversations over 7 days, 3–4 incidents (one high: "Refund questions answered wrong — search returned an archived policy", 14 conversations), notifications log, recipients, rules, a simulate job that progresses. Customer messages in natural Indian English, ₹ amounts.
2. **Workspace context**: `WorkspaceProvider` reading `?ws=` then localStorage, default `nimbu`; every API hook passes `workspace`.
3. **Vocabulary layer** `src/lib/vocab.ts`: `t(key)` returns the Nimbu or generic word per section 2 (conversation/run, customer message/question, agent reply/final answer, correct answer per policy/expected, help article/passage). Use it on every page that shows these words, including existing pages.
4. **Header**: workspace switcher (name + chevron, menu with descriptions) left of the nav; nav becomes Overview · Incidents · Conversations · Evaluation · Live lab · Settings. Move Fleet charts into Overview; redirect `/fleet` → `/`. Runs page moves to `/conversations` (redirect `/runs` and `/runs/:id`).
5. **Overview page** at `/` exactly per section 7.2: generated headline sentence, KpiRow with plain captions, wrong-answer-rate line chart with dashed threshold, open incidents compact list, the two Fleet bar charts scoped to the workspace, empty state copy. Currency with `Intl.NumberFormat('en-IN')`.

## Acceptance
- Switching workspace changes all data and the vocabulary across pages, and survives reload.
- Overview reads well at 1366×768 / 125% zoom; numbers are large; the high-severity incident is visible without scrolling.
- `npm run build` passes; everything works on mocks.
