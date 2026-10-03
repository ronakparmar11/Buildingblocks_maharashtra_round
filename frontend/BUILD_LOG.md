# Black Box frontend build log

| Phase | Status | Summary |
|---|---|---|
| f00 Foundation | done | Light investigation-board tokens; exact API types and hooks; deterministic mock API; app shell, shortcuts, shared UI, and styleguide. Replaced the legacy dark shell. Browser checks left: styleguide states, keyboard traversal, no mock network requests, projector widths. |
| f01 Runs page | done | URL-synced filters/search, 50-row pagination, exact five-column table, skeleton/empty/error states, row and j/k keyboard navigation. Browser checks left: projector truncation and filter interaction. |
| f02 Run detail graph | done | Responsive detail header/facts shell, dagre React Flow route, waypoint states, synchronized FDR tape, ground truth, and reduced-motion-aware diagnosis playback. Browser checks left: fit/pan, hover sync, responsive projector view. |
| f03 Inspector | done | Reusable inspector with ranked header, Why reasons/evidence/contributions, blast count, passage-aware I/O, State reconstruction, empty state, and responsive bottom sheet. Browser checks left: focus order and long-passage expansion. |
| f04 Replay and fixes | done | Editable/validated replay, blast-radius graph preview, pass/fail result panel, progressive three-attempt fixes job, success/failure states, and focus-trapped drawer. Browser checks left: job timing, focus return, graph pulse/preview feel. |
| f05 Compare | done | Outcome comparison, generated divergence summary, compact status route, data-dependent filter, expandable first word diff and side-by-side JSON, plus missing/loading/error states. Browser checks left: compact framing and narrow table. |
| f06 Evaluation | done | Judge-readable KPI row, interactive baseline bars, leave-one-out heat table, failure accuracy, proof cost, fix rates, method details, and screen-reader data fallbacks. Browser checks left: projector labels and chart animation. |
| f07 Fleet | done | Generated fleet headline, sorted step/reason bars with hover counts, injected-failure table, Runs drill-down URLs, real mock cause filtering, and all data states. Browser checks left: hover and mobile layout. |
| f08 Live lab | done | Four-stage projector flow with prepared questions, optional fault/target, live run, 500 ms route reveal, automatic diagnosis, streamed fixes, reset, full-run, and compare actions. Browser checks left: timing and distance readability. |
| f09 Polish and real API | done | Part A complete: state/accessibility/copy audit, static styleguide tokens, visible Fleet filters, warning-free chunk split, lint/build, projector and wide route audit, hero and Live lab interaction checks. Part B intentionally skipped. |

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

## f06 Evaluation

- Files changed: Evaluation page, expanded internally consistent mock evaluation payload, app route.
- Decisions: Recharts only for axis-based comparisons; dense leave-one-out evidence stays an HTML table; every chart has an accessible title and hidden data table.
- Validation: `npm run build` passed (non-failing bundle-size warning increased after Recharts).
- Left for browser verification: 1366×768 at 125% zoom, bar label overlap, 150 ms click animation, and single-column breakpoint.

## f07 Fleet

- Files changed: Fleet page, mock Runs likely-cause filtering, app route.
- Decisions: bars are semantic links so keyboard and pointer users get identical drill-downs; counts use native hover titles while percentages stay visible.
- Validation: `npm run build` passed (existing non-failing bundle-size warning).
- Left for browser verification: hover count discoverability, bar-label truncation, and the 900px single-column breakpoint.

## f08 Live lab

- Files changed: Live lab page and app route.
- Decisions: reuse the existing live-run, run, diagnosis, repair-job, route, and tape contracts; keep presentation timing local to the lab; prepared mock run reveals one step every 500 ms.
- Validation: `npm run build` passed (existing non-failing bundle-size warning).
- Left for browser verification: complete loop under 60 seconds, projector readability at four meters, control spacing, and streamed node/fix timing.

## f09 Polish and real API

- Files changed: page empty/loading states, Runs drill-down filter display, static styleguide token classes, semantic `StepKey`, drawer/inspector cleanup, graph attribution, Vite chunk splitting.
- Decisions: Part A only; mocks remain the development default and Part B was intentionally skipped. React Flow attribution remains visible to avoid a license warning.
- Validation: `npm run lint` passed; `npm run build` passed without warnings; automated browser audit at 1366×768 with 125% zoom and 1920×1080 found no horizontal overflow or console errors and no `/api/` requests.
- Runs: pass — 304 mock runs, 50-row page, loading geometry, keyboard controls, filters, and projector table checked.
- Run detail: pass — diagnosis playback completed, selected `q1/retrieve#0`, responsive graph/tape/inspector screenshot checked.
- Compare: pass — outcomes, compact route, first diff, and console-clean semantics checked.
- Evaluation: pass — KPI/chart/table layout and labels checked at projector and wide sizes.
- Fleet: pass — responsive layout and cause drill-down behavior checked.
- Live lab: pass — prepared failure loop reached “Fix found” well under 60 seconds.
- Styleguide: pass — all static color/type tokens and shared component states render.
- Hero mock audit: pass — all three prepared failures have distinct detailed traces and three-reason diagnoses; generated rows now open matching run/task details instead of falling back to the Scott trace.
- Remaining manual checks: subjective readability from four meters, reduced-motion emulation, and screen-reader announcement quality.