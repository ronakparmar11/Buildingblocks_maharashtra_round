# 11 — Frontend Design Specification

**This document supersedes the "Visual identity" section of `08-UI.md`.** Routes, screens, and API shapes in `07-API.md` and `08-UI.md` still apply; where this document is more specific, follow this one.

The frontend is built **before the backend is finished**, against a realistic in-browser mock layer. Switching to the real API later must be a one-line environment change.

---

## 1. Who uses it and what it's for

**Audience:** engineers who build AI agents, and hackathon judges watching on a projector.
**Primary job:** look at a failed agent run and understand, within seconds, which step caused it, why, and whether a fix works.
**Secondary job:** prove the system works at scale (evaluation, fleet patterns).

Every screen answers one question:

| Screen | Question it answers |
|---|---|
| Runs | Which runs failed, and where does the model think each went wrong? |
| Run detail | What caused this failure, and what's the evidence? |
| Compare | What changed between two runs, and how did it change the outcome? |
| Evaluation | Can the model be trusted? |
| Fleet | Where do our agents fail most often? |
| Live lab | Show me the whole loop, live. |

---

## 2. Design concept: "the investigation board"

Flight recorders exist so investigators can reconstruct what happened before a crash. Black Box borrows from that world deliberately:

- **Aeronautical charts** for the execution graph: steps are waypoints on a route drawn over a faint chart grid.
- **Flight data recorder tape** for the timeline: a parameter trace across execution order, like an FDR readout, with a playback scrubber.
- **Cockpit alerting colors** with their real meanings: red is a warning (failed), amber is caution (suspicious or changed), green is normal (passed), cyan is something you can select.
- **International orange**, the real color of flight recorders, is reserved for exactly one thing: the most likely cause.
- **B612**, the typeface Airbus designed for cockpit displays, for step names and numbers.

The theme is **light**, like charts and investigation reports, and because light interfaces stay legible on washed-out hackathon projectors.

**Where the boldness goes:** the run detail graph and its diagnosis playback. Everything else is quiet, disciplined, and dense.

---

## 3. Design tokens

### Color

| Token | Hex | Use |
|---|---|---|
| `paper` | `#EEF1F2` | page background (cool chart paper) |
| `panel` | `#FBFCFC` | panels, tables, inspector |
| `ink` | `#14202B` | primary text, graph edges |
| `graphite` | `#5B6873` | secondary text, icons |
| `rule` | `#C9D2D8` | borders, chart grid, dividers |
| `rule-soft` | `#DFE5E8` | table row dividers, chart grid minor lines |
| `orange` | `#FF4F00` | international orange: most likely cause, primary action button only |
| `orange-tint` | `#FFE4D6` | culprit node fill, highlight backgrounds |
| `warning` | `#C8223A` | failed outcome, errors |
| `caution` | `#D48A00` | suspicious steps (rank 2–3), changed steps in compare |
| `caution-tint` | `#FBEFD5` | caution backgrounds |
| `normal` | `#1E8A4C` | passed outcome |
| `normal-tint` | `#DDF1E5` | pass backgrounds, diff insertions |
| `advisory` | `#0B6E8A` | links, selected state, focus ring, interactive affordances |
| `ghost` | `#AEB8BF` | reused steps (dashed), disabled |

Rules:
- Orange appears **once per screen** at most in its strong form (the #1 cause or the primary button, not both competing). If a screen has both, the button uses `ink` fill instead.
- Red means "failed". Never use red for "suspicious". The culprit is orange, not red.
- No gradients anywhere. No drop shadows except on popovers, drawers, and toasts (`0 8px 24px rgba(20,32,43,0.14)`).

**Blame heat** (node fill and tape trace) — normalized score s in 0..1:
- s < 0.25 → `panel` with `rule` border
- 0.25–0.6 → `caution-tint` with `caution` border
- > 0.6 and not rank 1 → `caution-tint` with 2px `caution` border
- rank 1 → `orange-tint` fill, 2px `orange` border, orange impact marker

### Typography

- **Archivo** (Google Fonts, variable with width axis) for all UI text and headings.
  - Headings: weight 600, width 85 (semi-condensed). The condensed width is the type personality — it reads like instrument and chart labelling.
  - Body/UI: weight 400/500, width 100.
- **B612 Mono** (Google Fonts) for step keys (`q1/retrieve#0`), run IDs, token counts, scores, and any tabular number. Not for general labels.
- Fallback stacks: `Archivo, "Segoe UI", system-ui, sans-serif` and `"B612 Mono", ui-monospace, Consolas, monospace`.

Type scale (1.25 ratio), base 14px for the dense tool UI:

| Token | Size / line-height | Use |
|---|---|---|
| `text-xs` | 12 / 16 | captions, chip text, axis labels |
| `text-sm` | 14 / 20 | default UI, tables |
| `text-md` | 16 / 24 | prose (reasons, explanations), inputs |
| `text-lg` | 20 / 28 | panel titles |
| `text-xl` | 25 / 32 | page titles |
| `text-2xl` | 31 / 38 | KPI numbers |
| `text-3xl` | 39 / 44 | Live lab outcome, run header question on wide screens |

Rules: sentence case everywhere. **No all-caps labels.** No small tracked-out "eyebrow" labels above headings. Prose line length under 75 characters. Numbers use `font-variant-numeric: tabular-nums`.

### Space, shape, elevation

- 4px base unit; use 4, 8, 12, 16, 24, 32, 48.
- Radius by hierarchy, not one radius everywhere: chips and badges 999px (pill), buttons and inputs 6px, panels 10px, graph nodes 8px, the FDR tape 0 (it's an instrument strip).
- Panels are separated by 1px `rule` borders, not shadows.
- Max content width 1440px; Run detail and Compare use full width.

### Iconography

`lucide-react`, 16px in UI, 18px in graph nodes, stroke 1.75. Step icons:
`plan` → `Map` · `retrieve` → `Search` · `extract` → `TextSelect` · `check` → `ShieldCheck` · `reformulate` → `RefreshCw` · `synthesize` → `Merge`.

### Motion

- **One orchestrated moment:** the diagnosis playback on Run detail (section 7.3).
- Motion responding to the user (drawer open, row expand, toast) is fine: 150–200ms, ease-out.
- No entrance animations on page load, no hover lift on cards, no animated backgrounds.
- `prefers-reduced-motion: reduce` → all motion becomes instant.

---

## 4. Voice and copy

Write for an engineer in a hurry. Plain verbs, sentence case, no filler, no exclamation marks. Errors say what happened and what to do; they don't apologize.

**Vocabulary (use these exact words everywhere):**

| Concept | Word in the UI | Not |
|---|---|---|
| culprit step | **likely cause** (rank 1: "most likely cause") | culprit, root cause, bad step |
| diagnose | **Find the cause** | Diagnose, Analyze |
| replay | **Replay from this step** | Re-run, Execute |
| auto-repair | **Try fixes** | Auto-repair, Heal |
| reused step | **reused** | cached, skipped |
| executed step | **re-run** | executed |
| fault run | **injected failure** | fault run |
| organic failure | **natural failure** | organic |
| blast radius | **steps this affects** | blast radius |

Key strings:
- Replay result (pass): **"Fixed. 4 steps re-run, 13 reused, 6,210 tokens saved."**
- Replay result (still failing): **"Still failing. 4 steps re-run, 13 reused. Try another change or try fixes."**
- Try fixes running: **"Trying 3 fixes on q1/retrieve#0…"**
- Try fixes success: **"Fix found: wider search (k=6) on q1/retrieve#0."**
- Try fixes none: **"No fix worked on the top 3 steps. Edit a step manually to keep investigating."**
- Empty runs list: **"No runs match these filters. Clear filters to see all runs."**
- API error: **"Couldn't load this run. The server returned 500. Check that the API is running on port 8000, then reload."**
- Demo-mode cache miss: **"This step isn't in the demo recording. Pick one of the prepared demo questions in Live lab."**

---

## 5. App shell

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ▣ Black Box     Runs   Evaluation   Fleet   Live lab        ● Demo data  v3│
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│                              page content                                  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

- Height 56px, `panel` background, bottom `rule` border.
- Wordmark: a 14px orange square (the recorder) + "Black Box" in Archivo 600, width 85, 18px. Sentence case, not caps.
- Nav links: `text-sm`, `graphite`; active link `ink` with a 2px `ink` underline offset 18px (sits on the header border).
- Right side: status chip from `/health` — "Demo data" (when mocks on), "Demo mode" (cassette only), or "Live" — plus model version in B612 Mono `text-xs`.
- Compare has no nav item; it's reached from runs.
- Keyboard: `g r` runs, `g e` evaluation, `g f` fleet, `g l` live lab. `?` opens a shortcuts sheet.

---

## 6. Runs page `/`

**Question:** which runs failed, and where does the model think each went wrong?

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Runs                                                       1,284 runs      │
│ [ Search questions…        ] [Outcome ▾] [Type ▾] [Split ▾] [Fault ▾]  Clear│
├──────┬────────────────────────────────────────┬──────┬──────────────────────┤
│ ● Failed │ Were Scott Derrickson and Ed Wood… │ 8   │ q1/retrieve#0 ▮▮▮▮▯ .91│
│ ● Passed │ Which magazine was started first… │ 9   │ —                      │
│ ● Failed │ The director of Romeo + Juliet…   │ 12  │ q1/extract#0  ▮▮▮▯▯ .74│
│  …                                                                         │
├────────────────────────────────────────────────────────────────────────────┤
│ Showing 1–50 of 1,284                                   ‹ Prev   Next ›    │
└────────────────────────────────────────────────────────────────────────────┘
```

Columns (left-aligned text, right-aligned numbers):
1. **Outcome** — dot + word: "Failed" (`warning`), "Passed" (`normal`), "Error" (`graphite`). Width 96px.
2. **Question** — truncated to one line with full text in a tooltip; below it in `text-xs graphite`: run type ("Injected failure", "Natural failure", "Clean run", "Replay", "Fix attempt") and, for replays, "of r_8f2c…" linking to the parent.
3. **Steps** — B612 Mono, right-aligned.
4. **Likely cause** — step key chip (B612 Mono, `text-xs`, pill, `orange-tint` background for score > 0.6 else `rule-soft`) + a 5-segment score meter + score to 2 decimals. Empty for passed runs: "—".
5. **When** — relative time ("4 min ago"), absolute in tooltip.

Behavior:
- Filters are pills that open small menus; active filters show their value ("Outcome: Failed") with an × to clear. Filters live in the URL query string so links can be shared and Fleet can link here pre-filtered.
- Search debounced 250ms.
- Whole row is clickable → Run detail; hover row `rule-soft` background; keyboard `j/k` to move, `Enter` to open.
- Server-side pagination, 50 per page.
- Loading: 10 skeleton rows with the exact column widths (no layout shift).
- Empty: the empty string from section 4 with a "Clear filters" button.

---

## 7. Run detail `/runs/:id` — the hero screen

**Question:** what caused this failure, and what's the evidence?

### 7.1 Layout

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ← Runs                                                                      │
│ Were Scott Derrickson and Ed Wood of the same nationality?                  │
│ Expected  yes      Got  no      ● Failed   F1 0.00   Injected failure       │
│                                  [Compare with original] [Try fixes] [Find the cause]│
├──────────────┬───────────────────────────────────────────┬─────────────────┤
│ Run facts    │                                           │ Inspector       │
│              │        execution route (graph)            │                 │
│ 8 steps      │   plan ──► q1/retrieve#0 ──► q1/extract…  │ [Why] I/O  State│
│ 3,412 tokens │       └──► q2/retrieve#0 ──► q2/extract…  │  Replay         │
│ 4.2 s        │                          └──► synthesize  │                 │
│ gemini-flash │                                           │ Most likely     │
│              │                                           │ cause  .91      │
│ Show ground  │                                           │ q1/retrieve#0   │
│ truth  ○     │                                           │ ...reasons...   │
├──────────────┴───────────────────────────────────────────┴─────────────────┤
│ FDR tape  ▁▁▂▁█▆▃▁   ◄ scrubber                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

Grid: left column 220px, inspector 400px, graph fills the rest. Tape is full width, 96px tall. Below 1200px wide, the left column collapses into the header; below 900px, the inspector becomes a bottom sheet.

### 7.2 Header

- Back link "← Runs" (keeps previous filters).
- Question in `text-xl` (or `text-3xl` above 1600px), Archivo 600 width 85, max two lines.
- Answer line: "Expected" label (`graphite`) + gold answer in `ink`; "Got" + final answer — in `warning` color if failed. Outcome chip. F1 in B612 Mono. Run type.
- If this run is a replay or fix attempt: a line "Replay of r_8f2c… · 4 re-run, 13 reused, 6,210 tokens saved" with the parent linked. (Use separate stat chips, not a dot-joined string.)
- Actions, right-aligned: secondary "Compare with original" (only for replays), secondary "Try fixes" (only for failed runs, enabled after diagnosis), primary "Find the cause". Once diagnosis has run, "Find the cause" becomes a quiet text button "Diagnosed in 1.2 ms".

### 7.3 Execution route (the graph) — the signature element

- React Flow + dagre, left to right, `ranksep 90`, `nodesep 28`.
- Canvas background: `paper` with a chart grid — minor lines every 24px in `rule-soft`, major lines every 120px in `rule`, both 1px. This is the one decorative device in the app; it earns its place by making the graph read as a route on a chart.
- Edges: 1.5px `ink` at 55% opacity, smooth-step, small arrowhead. Edges into the most likely cause turn `orange`.
- **Node (waypoint card)**, 220 × 64px, radius 8, `panel` fill, 1px `rule` border:
  - Left: 28px circle "waypoint" with the step icon.
  - Line 1: step key in B612 Mono `text-xs` `ink`.
  - Line 2: output summary in Archivo `text-sm`, one line, ellipsis.
  - Fill/border from blame heat (section 3).
  - Rank 1: `orange-tint` fill, 2px `orange` border, and an **impact marker** — a 10px orange diamond on the waypoint circle — plus a small "Most likely cause" label above the node in `text-xs` `orange`.
  - Rank 2–3: `caution` border with a small rank number "2" / "3" on the waypoint.
  - Reused (replay runs): dashed 1px `ghost` border, 60% opacity text, small "reused" text tag; re-run steps keep full styling.
  - Error step: `warning` border, alert icon replaces the step icon.
  - Selected: 2px `advisory` outline offset 2px.
- Branch labels: faint `graphite` `text-xs` labels "q1 branch", "q2 branch" at the start of each branch lane.
- Controls: zoom in/out/fit in the bottom-left corner as a small vertical control group. Minimap off (it's noise).
- Clicking empty canvas clears selection.

**Diagnosis playback (the one orchestrated moment):** when "Find the cause" is clicked or when a diagnosis loads for the first time on this run:
1. The tape scrubber sweeps left to right over ~1.1s.
2. As it passes each step, that step's tape bar rises to its blame height and its graph node takes its heat color.
3. When the sweep finishes, the rank-1 node receives the orange impact marker, the graph pans to center it, and the inspector opens on the Why tab for that step.
With reduced motion: everything appears instantly, then the inspector opens.

### 7.4 FDR tape (timeline)

- Full-width strip, 96px, `panel` background, top border `rule`.
- Horizontal axis = execution order; each step is a column of equal width.
- Draw the blame score as a **stepped trace line** (1.5px `ink`) with a filled area under it at 10% `ink`; rank-1 column's segment drawn in `orange` with 20% orange fill. This reads as an FDR parameter trace rather than a bar chart.
- Under the trace, a row of tick marks with step keys in B612 Mono `text-xs` (rotated -35° if crowded; show every key on hover).
- Scrubber: a 1px `ink` vertical line with a small handle; hovering a column moves the scrubber and highlights the matching graph node; clicking selects it.
- Before diagnosis: the trace is flat and a centered hint reads "Find the cause to see how suspicious each step is."

### 7.5 Left column: run facts

Simple definition list (label `graphite text-xs`, value `ink` B612 Mono): steps, tokens spent, duration, model, run ID (copy button), created. Then:
- **Show ground truth** toggle (off by default). When on: the node where a failure was injected gets a small black flag icon and a label "Injected here: distractor retrieval"; the proven cause (from labeling) gets a check icon "Proven cause". A one-line note under the toggle: "Hidden by default so you see the model's answer first."

### 7.6 Inspector

Header: step key (B612 Mono `text-lg`), step type with its icon, and if ranked: "Most likely cause" in orange or "Rank 2" in caution, with the score.

Tabs (underline style, not boxed): **Why** · **I/O** · **State** · **Replay**. Default tab: Why for ranked steps, I/O for others.

**Why tab**
- A one-sentence summary: "This step is the most likely cause. Fixing it would change 4 later steps."
- Up to 3 reasons. Each reason is a block:
  - Reason sentence in Archivo `text-md` `ink` (from the API's `text`).
  - Evidence quote: a left-bordered block (3px `rule`), B612 Mono `text-xs` when it's data, Archivo when it's prose. E.g. `“British” not found in 3 retrieved passages`.
  - A thin contribution bar (relative width, `caution` color) — no numbers needed.
- Footer link: "How this score is calculated" → opens a small popover explaining the ranker in two sentences.
- If not ranked in top 3: "This step looks normal. Top suspects: q1/retrieve#0, q1/extract#0." with links.

**I/O tab**
- Two collapsible sections, Input and Output, each with a JSON tree viewer (collapsible keys, strings wrap, long passages clamp to 4 lines with "Show more"). Copy button per section.
- Retrieval steps render passages as small cards (title in Archivo 600, score in B612 Mono, text clamped) instead of raw JSON, with a "Raw JSON" switch.
- Meta row: latency, tokens in/out, model, "From recording" / "Re-run" / "Cached".

**State tab**
- The agent's memory after this step: plan (as a numbered list of sub-questions — it genuinely is a sequence), sub-answers table, attempts, final answer.

**Replay tab** — see section 8.

---

## 8. Replay, steps-this-affects, and Try fixes

### 8.1 Replay tab (inside the inspector)

```
┌ Replay from this step ───────────────────────┐
│ Change the output of q1/retrieve#0, then     │
│ replay. Steps that don't depend on it are    │
│ reused from the recording.                   │
│                                              │
│ ┌──────────────────────────────────────────┐ │
│ │ { "passages": [ { "pid": "p_12", ...     │ │
│ │   ...editable JSON...                    │ │
│ └──────────────────────────────────────────┘ │
│ ✓ Valid JSON                    Reset        │
│                                              │
│ Steps this affects: 4 of 8   [Show on graph] │
│                                              │
│ [Regenerate this step]   [Replay from this step] │
└──────────────────────────────────────────────┘
```

- Editor: textarea with B612 Mono `text-xs`, line numbers, prefilled with the step's output, 14 lines tall, resizable. Validate on change (debounced 200ms): "✓ Valid JSON" in `normal` or "Line 4: expected a comma" in `warning`. Disable the replay button while invalid.
- "Steps this affects: N of M" from `/blast-radius`. **Show on graph** toggles a highlight: affected nodes get a 2px `caution` outline, unaffected nodes fade to 40% opacity with a "will be reused" tooltip. This preview is what makes dependency-aware replay visible *before* it happens.
- Two actions: secondary "Regenerate this step" (re-run the step as-is) and primary "Replay from this step" (uses the edited output).
- While running: button shows a spinner and "Replaying…"; the graph shows affected nodes pulsing gently (opacity 60–100%, 1.2s) — this is a response to the user's action, so it's allowed.

### 8.2 Replay result

A result panel replaces the editor's footer (not a disappearing toast, because the user needs to act on it):
- Pass: `normal-tint` background, check icon, **"Fixed. 4 steps re-run, 13 reused, 6,210 tokens saved."**
- Still failing: `caution-tint`, **"Still failing. 4 steps re-run, 13 reused. Try another change or try fixes."**
- Three stat chips: "4 re-run", "13 reused", "6,210 tokens saved" (B612 Mono numbers).
- Actions: "Open replay" (→ the new run), "Compare with original" (→ Compare page).

### 8.3 Try fixes drawer

Opens from the right, 480px, over the inspector, with a dimmed backdrop.

```
┌ Try fixes ─────────────────────────────── × ┐
│ Trying fixes on the top 3 likely causes,     │
│ in order. Stops at the first fix that works. │
│                                              │
│ 1  q1/retrieve#0                Most likely  │
│    ○ Rewrite the search query     Running…   │
│    ✓ Widen search to 6 results    Passed     │
│      [3 re-run] [5 reused]  [Compare]        │
│    ✕ Search by entity name        Failed     │
│                                              │
│ 2  q1/extract#0                  Not needed  │
│ 3  synthesize                    Not needed  │
│                                              │
│ ┌ Fix found: wider search (k=6) ──────────┐  │
│ │ [Open fixed run]  [Compare with original]│  │
│ └──────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

- The list genuinely is a sequence (rank order), so the 1/2/3 numbering is earned.
- Strategy names in plain words: "Rewrite the search query", "Widen search to 6 results", "Search by entity name", "Ask again (new sample)", "Quote evidence first, then answer", "Use only the sub-answers", "Re-plan with the question type".
- Each attempt row: status icon (spinner / check / cross), strategy name, outcome word, and on completion stat chips. Rows appear as jobs report progress (poll every 700ms).
- Success: a `normal-tint` panel at the bottom with the success string and actions. Failure of all: the "No fix worked…" string with a button "Edit a step manually" that closes the drawer and opens the Replay tab on the #1 step.

---

## 9. Compare `/compare?a=&b=`

**Question:** what changed between two runs, and how did that change the outcome?

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ← Back to run                                                               │
│ Compare runs                                                                │
│ ┌ Original r_8f2c ───────────┐        ┌ Replay r_19ad ─────────────┐        │
│ │ ● Failed   Got "no"        │  ───►  │ ● Passed   Got "yes"       │        │
│ └────────────────────────────┘        └────────────────────────────┘        │
│ First difference at q1/retrieve#0.  4 steps changed, 13 identical.          │
├────────────────────────────────────────────────────────────────────────────┤
│  route of the replay, changed nodes highlighted (180px tall)               │
├────────────────────────────────────────────────────────────────────────────┤
│ [All steps] [Changed only]                                                  │
│ Step             Status      Original                 Replay               │
│ plan             Identical   comparison: q1, q2       comparison: q1, q2    │
│ q1/retrieve#0  ▸ Changed     3 passages: Sc…          3 passages: Scott De… │
│ q1/extract#0   ▸ Changed     British                  American              │
│ …                                                                           │
└────────────────────────────────────────────────────────────────────────────┘
```

- Two outcome cards side by side; the arrow between them is a simple ink line, not decoration.
- Summary sentence under the cards, generated from the data.
- A compact, non-interactive graph of run B (no grid, 180px tall) with changed nodes `caution`, identical nodes `ghost`, first difference with an orange marker.
- Table: columns Step (B612 Mono), Status chip (Identical `rule-soft`, Changed `caution-tint`, Only in original / Only in replay `rule-soft` with italic text), Original summary, Replay summary.
- "Changed only" toggle (default on when more than 8 rows).
- Expanding a changed row shows an inline word diff: deletions with `warning` text and a light red background (`#F9DEE2`) and strikethrough; insertions with `normal` text on `normal-tint`. Below the word diff, a "Show JSON diff" link expands a side-by-side JSON view.
- The first-difference row is expanded by default and has a 3px `orange` left border.

---

## 10. Evaluation `/eval`

**Question:** can the model be trusted?

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Evaluation                                                                  │
│ Tested on 120 questions the model never trained on.                          │
│                                                                            │
│  84%            71%              63%            76%            1.2 ms       │
│  finds the      on failure types on natural     of steps       per          │
│  cause first    it never saw     failures       reused         diagnosis    │
├──────────────────────────────────────┬─────────────────────────────────────┤
│ Model vs. other approaches           │ Failure types it never trained on  │
│ [Seen ▾ Held-out ▾ Natural]          │ (leave-one-out table)              │
│  grouped bars: top-1 / top-3         │                                     │
├──────────────────────────────────────┼─────────────────────────────────────┤
│ Accuracy by failure type             │ Cost of proving the cause          │
│  horizontal bars                     │  bisect replays vs. checking every │
│                                      │  step                               │
├──────────────────────────────────────┴─────────────────────────────────────┤
│ Fixes that worked:  58% using the top suspect, 74% using the top 3          │
├────────────────────────────────────────────────────────────────────────────┤
│ How we tested  (collapsible, plain-language method)                          │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Headline row:** five numbers, not five identical cards. Each is a large B612 Mono number (`text-2xl`) with a plain-language caption under it (`text-sm graphite`, max two lines), separated by 1px vertical `rule` lines. The phrasing makes each number self-explanatory to a judge: "finds the cause first", "on failure types it never saw", "on natural failures", "of steps reused", "per diagnosis".
- **Model vs. other approaches:** grouped horizontal bar chart (Recharts). Rows: Black Box, LLM reading the trace, Heuristic, Last step, Random. Two bars per row: top-1 (solid) and top-3 (40% opacity). Black Box bars `orange`; others `graphite`. A segmented control switches the test set: "Seen failure types" / "Held-out failure types" / "Natural failures". Value labels at bar ends in B612 Mono. Under the chart, one sentence: "The LLM takes 3.1 s and one API call per run; Black Box takes 1.2 ms."
- **Leave-one-out table:** rows = failure type in plain words ("Distractor retrieval"), columns Top-1, Top-3, MRR (B612 Mono, right-aligned). Cells shaded with a light `caution-tint` → `normal-tint` scale only behind the number, so the table scans like a heat map without being a chart.
- **Accuracy by failure type:** horizontal bars, seen types `ink`, held-out types `advisory` with a legend "Never seen in training".
- **Cost of proving the cause:** two bars "Bisect: 3.6 replays" vs "Checking every step: 11.2 replays", plus "Labels verified: 92%".
- **Fixes:** a single sentence row with two numbers, and a link "See fix attempts" → Runs filtered to fix attempts.
- **How we tested:** collapsible, closed by default, four short paragraphs: split by question, held-out failure types, natural failures labeled by resampling, baselines.

---

## 11. Fleet `/fleet`

**Question:** where do our agents fail most often?

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Fleet                                                                       │
│ 41% of failures start in retrieval.                                         │
│ Across 612 failed runs in the test set.                                     │
├──────────────────────────────────────┬─────────────────────────────────────┤
│ Where failures start                 │ Most common reasons                │
│  retrieve      ███████████ 41%       │  Answer not in retrieved text  31% │
│  extract       ██████ 22%            │  Retrieval score far below …   24% │
│  plan          ████ 15%              │  Check flagged unsupported     17% │
│  …                                   │  …                                  │
├──────────────────────────────────────┴─────────────────────────────────────┤
│ By injected failure type   (small table)                                    │
└────────────────────────────────────────────────────────────────────────────┘
```

- The headline sentence is the hero, `text-2xl` Archivo 600 width 85, generated from the largest bucket.
- Bars are horizontal, sorted descending, `ink` with the top bar in `orange`. Labels on the left use the real step names (retrieve, extract, plan…) with their icons, since the audience is engineers.
- Clicking a bar → Runs page with `outcome=fail` and a filter for that likely-cause step name (or reason).
- Each bar row shows the count in B612 Mono on hover.

---

## 12. Live lab `/lab`

**Question:** show me the whole loop, live. This is the demo driver, used on a projector — everything is bigger here.

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Live lab                                                                    │
│ ┌ 1  Pick a question ─────────────┐ ┌ 2  Break something (optional) ───────┐│
│ │ [ Search test questions…   ▾ ]  │ │ [ No failure ▾ ]  at  [ q1/retrieve#0 ▾]││
│ └─────────────────────────────────┘ └───────────────────────────────────────┘│
│                                              [ Run the agent ]              │
├────────────────────────────────────────────────────────────────────────────┤
│ Were Scott Derrickson and Ed Wood of the same nationality?                  │
│ Expected  yes       Got  no       ● Failed                                  │
│                                                                            │
│              execution route (same component as Run detail)                │
│                                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ 3  Most likely cause: q1/retrieve#0   (reasons, compact)   [Try fixes]      │
│ 4  Fix found: wider search. 3 re-run, 5 reused.  [Compare]                  │
└────────────────────────────────────────────────────────────────────────────┘
```

- This is a genuine sequence, so steps are numbered 1–4 and each lights up (`ink` number in a circle → `orange` when active → check when done).
- Question picker: searchable combobox; prepared demo questions pinned at the top under "Prepared for demo".
- Failure picker: "No failure" plus plain-language failure types; target step dropdown filled from `/tasks/{id}/fault-targets`, disabled when "No failure".
- "Run the agent": primary orange button, large (44px tall).
- While running, nodes appear on the route one by one as steps arrive (poll every 500ms) — a response to the user's action.
- On failure: diagnosis runs automatically with the playback from 7.3, then section 3 appears with the top reason only and a "Try fixes" button. Fix results stream into section 4.
- Outcome text in `text-3xl` so it reads from the back of the room.
- "Open full run" link at the bottom → Run detail.

---

## 13. Shared components (build once, use everywhere)

`Button` (primary orange / primary ink / secondary outlined / quiet text; sizes sm/md/lg), `OutcomeChip`, `RunTypeLabel`, `StepKey` (B612 Mono pill with copy-on-click), `ScoreMeter` (5 segments), `StatChip`, `Tabs` (underline), `Drawer`, `Popover`, `Tooltip`, `Toast` (bottom-right, for transient confirmations only), `JsonViewer`, `JsonEditor` (textarea with validation and line numbers), `PassageCard`, `WordDiff`, `Skeleton`, `EmptyState`, `ErrorState`, `FilterPill`, `Combobox`, `SegmentedControl`, `ExecutionRoute` (the graph), `FdrTape`, `KpiRow`.

Every component: visible focus ring (2px `advisory`, offset 2px), keyboard operable, `aria-label`s on icon buttons, color is never the only signal (outcome chips always include the word).

---

## 14. Mock data layer

The frontend must be fully usable with no backend.

- `VITE_USE_MOCKS=true` (default in `.env.development`) routes every API call to `src/mocks/` handlers with a simulated 250–600ms latency. `false` uses the real API through the Vite proxy. The UI code never knows which one it's talking to.
- Mock data shapes must match `docs/07-API.md` exactly via shared TypeScript types in `src/api/types.ts`.
- **Three hand-crafted hero runs** (used for the demo, fully detailed with realistic passages and answers):
  1. Comparison question "Were Scott Derrickson and Ed Wood of the same nationality?" (gold "yes"), injected distractor retrieval at `q1/retrieve#0`, extract says "British", final "no", failed. Diagnosis rank 1 `q1/retrieve#0` (0.91), rank 2 `q1/extract#0` (0.64), rank 3 `synthesize` (0.22). Includes a replay (fixed, 4 re-run, 4 reused) and a fix-attempt sequence where "Widen search to 6 results" passes.
  2. Bridge question about a film director's birthplace, injected wrong extraction at `q1/extract#0`, so `q2` searches the wrong person; failed; rank 1 `q1/extract#0`.
  3. A natural failure where `synthesize` answers "no" despite both sub-answers being "American"; rank 1 `synthesize`, with a "Final answer doesn't match any sub-answer" reason.
- **Generated runs:** a seeded generator produces ~300 additional realistic runs (mixed outcomes, run types, failure types, 6–16 steps, comparison and bridge shapes, retries with `reformulate`) from ~15 question templates, so the Runs page, filters, pagination, Fleet, and Evaluation look real.
- Mock replay and try-fixes jobs progress over time (attempts resolve one by one every ~900ms) so loading and streaming states can be designed and tested.
- Mock evaluation numbers: plausible and internally consistent (top-3 ≥ top-1, held-out below seen, natural below held-out, model above all baselines except where noted).

---

## 15. Quality bar (check before calling any page done)

- Projector test: Chrome at 1366×768 and 125% zoom — no horizontal scroll, every number readable, graph fits with "fit view".
- Wide test: 1920×1080 — no stretched lines of prose over 75 characters.
- Keyboard-only pass through every page.
- No layout shift when data loads (skeletons match final dimensions).
- Every page has loading, empty, and error states using the copy in section 4.
- Lighthouse accessibility score ≥ 95.
- `npm run build` with zero TypeScript errors and zero console errors at runtime.
