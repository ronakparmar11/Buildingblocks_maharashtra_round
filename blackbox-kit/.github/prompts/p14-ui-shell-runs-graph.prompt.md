---
description: "P14 — Frontend shell, Runs page, and Run Detail graph (hero screen)"
mode: agent
---
Read [UI spec](../../docs/08-UI.md) sections "Visual identity", "Routes", "Runs", "Run Detail", and [API spec](../../docs/07-API.md). Develop against the API in mock mode (`BLACKBOX_MOCK_API=1 make api`).

## Task
1. `frontend/src/api/types.ts` (mirror API schemas exactly) and `client.ts` (fetch wrapper) + TanStack Query hooks per endpoint.
2. App shell: router, top nav per spec with health status pill, fonts (Inter, JetBrains Mono), brand tokens.
3. Runs page: table with filters, server-side pagination, outcome/origin badges, predicted-culprit chip with score bar.
4. Run Detail:
   - header strip with question, gold vs final, outcome, F1, origin, parent link, action buttons (Diagnose, Auto-repair, Compare with parent — wire Diagnose now, others stubbed).
   - graph with React Flow + dagre (LR): custom node component showing step_key (mono), name icon, output_text (2 lines), blame-heat fill, rank-1 orange outline with pulse and "#1" badge, ghosted dashed style for `reused` steps, error style.
   - timeline strip of blame bars in execution order.
   - inspector with tabs Why / I/O / State (Replay tab comes in P15). Why tab shows score, rank, reasons with evidence in quote blocks.
   - ground-truth toggle (off by default) showing label/fault markers.
5. Loading skeletons and empty/error states everywhere. No layout shift when diagnosis arrives.

## Acceptance
`make web` with the mock API: Runs page lists runs; clicking one shows the graph with heat colors, the #1 culprit highlighted, and readable reasons. `npm run build` passes with no TypeScript errors.
