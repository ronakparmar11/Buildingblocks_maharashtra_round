---
description: "F00 — Frontend foundation: design tokens, fonts, app shell, shared components, mock data layer"
mode: agent
---
Read these fully before writing code:
- [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) — the source of truth for every visual and copy decision. Sections 3, 4, 5, 13, 14, 15 matter most for this task.
- [API spec](../../docs/07-API.md) — every response shape the UI consumes.
- [Data model](../../docs/03-DATA-MODEL.md) — step keys and fields.

## Goal
Build the foundation every page will use, so later prompts only build pages. The app must run completely without the backend.

## Tasks

### 1. Tokens and fonts
- Install `lucide-react` (and any missing deps from the architecture doc: `@xyflow/react`, `dagre`, `@types/dagre`, `recharts`, `diff`, `@tanstack/react-query`, `react-router-dom`).
- Load **Archivo** (variable, include the width axis `wdth 75..100`, weights 400–700) and **B612 Mono** (400, 700) from Google Fonts in `index.html` with `display=swap`.
- Tailwind config: add every color token from section 3 by its exact name (`paper`, `panel`, `ink`, `graphite`, `rule`, `rule-soft`, `orange`, `orange-tint`, `warning`, `caution`, `caution-tint`, `normal`, `normal-tint`, `advisory`, `ghost`), the type scale from section 3 as `text-xs` … `text-3xl` with the given line heights, font families `sans` (Archivo stack) and `mono` (B612 Mono stack), radii `chip`, `control` (6px), `panel` (10px), `node` (8px), and the popover shadow.
- `src/styles/globals.css`: body `paper` background, `ink` text, `text-sm`, tabular numbers utility, a `.heading` class (Archivo 600, `font-variation-settings: "wdth" 85`), focus-visible ring (2px `advisory`, offset 2px), and a global `prefers-reduced-motion` rule that disables transitions and animations.
- Remove any previous dark theme or old colors.

### 2. API layer with mocks
- `src/api/types.ts`: TypeScript types mirroring every request and response in the API spec exactly.
- `src/api/client.ts`: `apiGet`/`apiPost` that call `/api/...` normally, or route to `src/mocks/handlers.ts` when `import.meta.env.VITE_USE_MOCKS === "true"` (simulate 250–600 ms latency). Add `.env.development` with `VITE_USE_MOCKS=true`.
- `src/api/hooks.ts`: one TanStack Query hook per endpoint (`useRuns`, `useRun`, `useDiagnosis`, `useReplay` mutation, `useBlastRadius`, `useRepairJob`, `useCompare`, `useEval`, `useFleet`, `useTasks`, `useFaultTargets`, `useLiveRun`, `useHealth`).
- Errors become a typed `ApiError` with status and message so pages can show the error copy from section 4.

### 3. Mock data (section 14 of the design spec)
- `src/mocks/hero-runs.ts`: the **three hand-crafted hero runs**, fully detailed: realistic passages (title, text, score), extract answers with evidence sentences, check results, plan JSON, state snapshots, deps, diagnosis rankings with 3 reasons each (reason text + evidence). Include for hero run 1: a replay run (fixed: 4 re-run, 4 reused, tokens saved) and a fix-attempt sequence where "Widen search to 6 results" passes.
- `src/mocks/generator.ts`: a seeded generator (deterministic, e.g. mulberry32) producing ~300 realistic runs from ~15 question templates (mix of comparison and bridge; run types clean / injected failure / natural failure / replay / fix attempt; outcomes; 6–16 steps; some with `reformulate` retries), each with a diagnosis for failed runs.
- `src/mocks/eval.ts` and `src/mocks/fleet.ts`: plausible, internally consistent numbers per section 14.
- `src/mocks/handlers.ts`: implements every endpoint over this data, including filters, search, pagination, blast radius (computed from deps), compare (computed by aligning step keys and diffing `output_text`), replay (returns a new run that re-runs affected steps and reuses the rest), and jobs for try-fixes and live runs that progress over time (one attempt resolves every ~900 ms; live run steps appear one by one).

### 4. App shell
Router with routes `/`, `/runs/:id`, `/compare`, `/eval`, `/fleet`, `/lab`, `/styleguide` (placeholder pages for now). Header exactly as section 5: orange-square wordmark "Black Box" (sentence case), nav links with active underline, status chip ("Demo data" when mocks are on) and model version from `useHealth`. Keyboard shortcuts `g r`, `g e`, `g f`, `g l`, and `?` for a shortcuts sheet.

### 5. Shared components (section 13)
Build every component listed in section 13 in `src/components/ui/` (and `ExecutionRoute`, `FdrTape`, `KpiRow` as stubs with the right props — they're built properly in later prompts). Use `lucide-react` icons and the step icon mapping from section 3.

### 6. Styleguide page `/styleguide`
Show every color token, the type scale, and every shared component in all states (default, hover, focus, disabled, loading, error). This page is how we review the design system — make it tidy.

## Rules
- Follow the design spec's copy and vocabulary exactly (section 4). Sentence case, no all-caps labels, no gradients, no card shadows.
- Don't call the backend. Don't touch anything outside `frontend/`.

## Acceptance
- `npm run build` passes with zero TypeScript errors.
- `npm run dev` → header renders, nav works, `/styleguide` shows all tokens and components, status chip says "Demo data".
- In the browser console, `useRuns` data loads from mocks (no network calls to `/api`).
- Report: files created, components built, anything you couldn't finish.
