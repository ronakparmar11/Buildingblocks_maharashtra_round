---
description: "F02 — Run detail: header, execution route graph, FDR tape, run facts, diagnosis playback"
mode: agent
---
Read [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) sections 2, 3, 7.1–7.5, 13, 15 carefully. This is the hero screen and the most important page in the app. Reuse existing components and hooks.

## Goal
Build `/runs/:id` layout, header, the execution route graph, the FDR tape, the run facts column, and the diagnosis playback. (The inspector is built in F03 — leave a right-column placeholder with the correct width.)

## Tasks
1. **Layout** (7.1): CSS grid — left 220px, graph flexible, inspector 400px, FDR tape full width 96px at the bottom. Responsive collapse rules at 1200px and 900px.
2. **Header** (7.2): back link that preserves Runs filters, question, expected/got line, outcome chip, F1, run type, replay info chips for replay runs, and the three actions with the exact show/hide/enabled rules. After diagnosis, "Find the cause" becomes the quiet "Diagnosed in 1.2 ms" text.
3. **ExecutionRoute component** (7.3) using `@xyflow/react` + `dagre` (LR, ranksep 90, nodesep 28):
   - Chart-grid canvas background (minor 24px `rule-soft`, major 120px `rule`).
   - Custom waypoint node (220×64): waypoint circle with step icon, step key in B612 Mono, one-line output summary; blame-heat styling exactly per section 3; rank-1 impact marker (orange diamond) and "Most likely cause" label; rank 2–3 numbers; reused (dashed, faded, "reused" tag); error; selected outline.
   - Edges 1.5px ink at 55% opacity, smooth-step, arrowheads; edges into rank 1 turn orange.
   - Faint branch lane labels ("q1 branch").
   - Zoom controls bottom-left; no minimap; click empty canvas clears selection.
   - Make the component reusable with props: `steps`, `edges`, `ranking?`, `selectedKey?`, `onSelect?`, `highlight?` (for "steps this affects"), `compact?` (for Compare/Lab), `revealUpTo?` (for Live lab streaming).
4. **FdrTape component** (7.4): stepped trace line with area fill, rank-1 segment in orange, step-key ticks (rotated when crowded), hover scrubber synced with graph highlight, click selects. Pre-diagnosis hint text.
5. **Diagnosis playback** (7.3, the one orchestrated moment): on "Find the cause" (or first load of an existing diagnosis), sweep the scrubber across the tape over ~1.1 s, raising each step's trace and coloring its node as it passes, then mark rank 1, pan the graph to center it, and select it. Instant under `prefers-reduced-motion`. Implement with `requestAnimationFrame`, not CSS keyframes on every node.
6. **Run facts column** (7.5): definition list, copyable run ID, and the "Show ground truth" toggle with the injected-here flag and proven-cause check markers on nodes, plus the explanatory note.
7. States: skeleton layout while loading (graph area shows the empty chart grid), and the run-not-found / API error states.

## Acceptance
- Open hero run 1 from the mocks: graph shows two branches merging at synthesize; clicking "Find the cause" plays the sweep and lands on `q1/retrieve#0` with the orange impact marker.
- Hover on tape ↔ highlight on graph works both ways; clicking either selects the step.
- Open a replay run: reused steps render dashed and faded.
- Reduced motion (DevTools → Rendering → emulate) makes the playback instant.
- Projector check passes; `npm run build` passes.
