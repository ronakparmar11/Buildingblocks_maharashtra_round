---
description: "P17 — Live Lab demo driver, cassette prewarm, demo mode hardening, README"
mode: agent
---
Read [UI spec](../../docs/08-UI.md) "Live Lab", [Pitch & Demo](../../docs/10-PITCH-AND-DEMO.md), and [Architecture](../../docs/02-ARCHITECTURE.md) D9.

## Task
1. `/lab` page: task search/picker (test split), fault selector populated from `/tasks/{id}/fault-targets` (or "no fault"), **Run** → live run job → graph fills as steps arrive (poll the run every 500 ms) → auto-diagnose on failure → **Auto-repair** button → winner + Compare link. Big, clear, projector-friendly.
2. `bb prewarm --tasks ID1,ID2,ID3 --faults TYPE@KEY,...`: executes the complete demo path for each (clean, fault run, diagnosis, all repair candidates, compare) so every LLM call is in the cassette.
3. Demo-mode hardening: with `BLACKBOX_DEMO_MODE=1`, a cassette miss returns a clear API error shown as a toast (never a blank screen); `/health` shows `demo mode`. Test the full Live Lab flow with networking disabled.
4. Fill `README.md`: replace placeholders with the numbers from `artifacts/eval.md`, add screenshots (Run Detail, Compare, Eval) in `docs/img/`, and verify the quickstart commands work from a fresh clone.
5. A `make demo` target: starts API (demo mode) + built frontend (vite preview) together.

## Acceptance
With Wi-Fi off: `make demo`, run the 3 prewarmed demo scenarios end to end in Live Lab in under 90 seconds each.
