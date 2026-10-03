# Black Box frontend build log

| Phase | Status | Summary |
|---|---|---|
| f00 Foundation | done | Light investigation-board tokens; exact API types and hooks; deterministic mock API; app shell, shortcuts, shared UI, and styleguide. Replaced the legacy dark shell. Browser checks left: styleguide states, keyboard traversal, no mock network requests, projector widths. |
| f01 Runs page | done | URL-synced filters/search, 50-row pagination, exact five-column table, skeleton/empty/error states, row and j/k keyboard navigation. Browser checks left: projector truncation and filter interaction. |
| f02 Run detail graph | done | Responsive detail header/facts shell, dagre React Flow route, waypoint states, synchronized FDR tape, ground truth, and reduced-motion-aware diagnosis playback. Browser checks left: fit/pan, hover sync, responsive projector view. |
| f03 Inspector | pending | |
| f04 Replay and fixes | pending | |
| f05 Compare | pending | |
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