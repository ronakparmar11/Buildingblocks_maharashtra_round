# Black Box frontend build log

| Phase | Status | Summary |
|---|---|---|
| f00 Foundation | done | Light investigation-board tokens; exact API types and hooks; deterministic mock API; app shell, shortcuts, shared UI, and styleguide. Replaced the legacy dark shell. Browser checks left: styleguide states, keyboard traversal, no mock network requests, projector widths. |
| f01 Runs page | done | URL-synced filters/search, 50-row pagination, exact five-column table, skeleton/empty/error states, row and j/k keyboard navigation. Browser checks left: projector truncation and filter interaction. |
| f02 Run detail graph | done | Responsive detail header/facts shell, dagre React Flow route, waypoint states, synchronized FDR tape, ground truth, and reduced-motion-aware diagnosis playback. Browser checks left: fit/pan, hover sync, responsive projector view. |
| f03 Inspector | done | Reusable inspector with ranked header, Why reasons/evidence/contributions, blast count, passage-aware I/O, State reconstruction, empty state, and responsive bottom sheet. Browser checks left: focus order and long-passage expansion. |
| f04 Replay and fixes | done | Editable/validated replay, blast-radius graph preview, pass/fail result panel, progressive three-attempt fixes job, success/failure states, and focus-trapped drawer. Browser checks left: job timing, focus return, graph pulse/preview feel. |
| f05 Compare | done | Outcome comparison, generated divergence summary, compact status route, data-dependent filter, expandable first word diff and side-by-side JSON, plus missing/loading/error states. Browser checks left: compact framing and narrow table. |
| f06 Evaluation | pending | |
| f07 Fleet | pending | |
| f08 Live lab | pending | |
| f09 Polish and real API | pending | |

## f00 Foundation

- Files changed: package manifests, `index.html`, Tailwind and Vite typings, app entry/shell, API types/client/hooks, mock data/handlers, shared UI, styleguide.
- Decisions: mock mode is the development default; generated data uses a fixed seed; the API client is the only layer aware of mock versus live mode.
- Validation: `npm run build` passed.
- Left for browser verification: visual component states, keyboard-only pass, mock requests staying in-process, and 1366/1920 responsive checks.

## f01 Runs page

- Files changed: `src/pages/RunsPage.tsx`, app route.
- Decisions: native selects retain full keyboard behavior while using pill styling; search writes to the URL after 250 ms.
- Validation: `npm run build` passed.
- Left for browser verification: 1366×768 at 125% zoom, row focus flow, and filter reload persistence.

## f02 Run detail graph

- Files changed: reusable `ExecutionRoute`, `FdrTape`, run detail page, app route, ES2021 library typing.
- Decisions: detail page owns the shared graph/tape selection; playback reveals ranking by execution index with `requestAnimationFrame` and becomes instant for reduced motion.
- Validation: `npm run build` passed (Vite reports a non-failing chunk-size warning).
- Left for browser verification: graph fit and controls, tape hover sync, playback/pan feel, replay node styling, reduced motion, and responsive widths.

## f03 Inspector

- Files changed: reusable `Inspector`, run detail integration; graph files mechanically formatted for maintainability.
- Decisions: the user-selected tab persists across steps; only the initial selection chooses Why for ranked steps and I/O otherwise.
- Validation: `npm run build` passed (existing non-failing chunk-size warning).
- Left for browser verification: tab focus sequence, bottom-sheet ergonomics, passage clamping/expansion, and copy confirmations.

## f04 Replay and fixes

- Files changed: inspector Replay tab, `TryFixes`, shared Drawer focus behavior, detail graph wiring, progressive mock job handler, ES2022 library typing.
- Decisions: editor/mutation result stays local to the inspector; blast-radius highlight and drawer state live in the detail page; mock attempts resolve every 900 ms.
- Validation: `npm run build` passed (existing non-failing chunk-size warning).
- Left for browser verification: replay loading pulse, exact JSON error wording by browser, streamed timing, focus trap/return, and graph preview appearance.

## f05 Compare

- Files changed: Compare page, compact comparison states in `ExecutionRoute`, app route.
- Decisions: reconstruct run B route directly from aligned compare rows; comparisons with eight or fewer rows default to All steps, larger comparisons to Changed only.
- Validation: `npm run build` passed (existing non-failing chunk-size warning).
- Left for browser verification: 180px graph fit, first-difference expansion, JSON columns, and narrow viewport table behavior.