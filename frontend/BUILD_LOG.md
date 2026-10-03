# Black Box frontend build log

| Phase | Status | Summary |
|---|---|---|
| f00 Foundation | done | Light investigation-board tokens; exact API types and hooks; deterministic mock API; app shell, shortcuts, shared UI, and styleguide. Replaced the legacy dark shell. Browser checks left: styleguide states, keyboard traversal, no mock network requests, projector widths. |
| f01 Runs page | pending | |
| f02 Run detail graph | pending | |
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