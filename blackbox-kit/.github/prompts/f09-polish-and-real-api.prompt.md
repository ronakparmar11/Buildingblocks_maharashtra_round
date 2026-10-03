---
description: "F09 — Polish pass, quality bar, and switching to the real API"
mode: agent
---
Read [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) section 15 and [API spec](../../docs/07-API.md).

## Part A — quality pass (do this now)
Go through every page and fix, without redesigning:
1. Every page has loading, empty, and error states using section 4 copy.
2. No layout shift on load.
3. Keyboard-only pass: every action reachable, focus visible, drawers trap focus, Esc closes overlays.
4. Color is never the only signal; icon buttons have `aria-label`s.
5. Projector test (1366×768, 125% zoom) and wide test (1920×1080) on every page; prose lines ≤ 75 characters.
6. Check copy against the vocabulary table in section 4 (likely cause, Find the cause, Replay from this step, Try fixes, reused, re-run). Fix any stray "culprit", "diagnose", "cached", "executed", all-caps labels, or dot-joined meta strings.
7. Remove unused code and console logs; `npm run build` with zero warnings you can fix.
Report a checklist with pass/fail per page.

## Part B — real API readiness (run this only when the backend API exists)
1. Set `VITE_USE_MOCKS=false`, start the backend on :8000, and walk through every page.
2. For each endpoint, compare the real response to `src/api/types.ts`; list every mismatch. Fix mismatches on the **frontend** side only if the API spec agrees with the backend; otherwise report it — do not change backend code.
3. Confirm the status chip shows "Live" or "Demo mode" from `/api/health`.
