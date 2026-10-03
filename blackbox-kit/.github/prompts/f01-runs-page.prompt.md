---
description: "F01 — Runs page"
mode: agent
---
Read [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) sections 3, 4, 6, 13, 15, and look at the existing components in `frontend/src/components/ui/` and hooks in `frontend/src/api/hooks.ts`. Reuse them — don't create duplicates.

## Goal
Build the Runs page at `/` exactly as section 6 describes.

## Tasks
1. Page title "Runs" (`.heading`, `text-xl`) with the total count on the right in `graphite`.
2. Filter bar: debounced search (250 ms), filter pills for Outcome, Run type, Split, Injected failure type. Active pills show their value with a clear ×; a "Clear" text button when any filter is active. **All filters live in the URL query string** (so links are shareable and Fleet can link here pre-filtered).
3. Table with the five columns from section 6, exact widths, alignment, and content:
   - Outcome chip (dot + word), question (one line + tooltip, run type and parent link underneath), steps (B612 Mono, right-aligned), likely cause (`StepKey` chip + `ScoreMeter` + score, "—" when passed), when (relative, absolute on hover).
4. Row interaction: whole row clickable to `/runs/:id`, hover background `rule-soft`, keyboard `j`/`k` to move focus between rows and `Enter` to open.
5. Pagination: 50 per page, "Showing 1–50 of 1,284", Prev/Next.
6. States: 10 skeleton rows matching final column widths; empty state with the exact copy from section 4 and a "Clear filters" button; error state with the API error copy.

## Acceptance
- Works with mocks: filtering, search, pagination, URL sync (reload keeps filters), keyboard navigation.
- No layout shift between loading and loaded.
- Projector check (1366×768 at 125% zoom): no horizontal scroll, question column truncates gracefully.
- `npm run build` passes.
