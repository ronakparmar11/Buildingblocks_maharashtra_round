---
description: "B02 — Incidents engine, verify-fix on similar conversations, traffic simulator, production hook"
mode: agent
---
Read [Business edition](../../docs/12-BUSINESS-EDITION.md) section 4 fully, and the existing diagnose, explain, repair, and replay code.

## Tasks
1. `blackbox/incidents/engine.py`:
   - `group_key(run, diagnosis)` = (workspace, category, rank-1 step name, rank-1 top reason feature).
   - `assign_incident(run_id)`: join the open incident with the same key within 7 days or open a new one; update n_runs, last_seen, est_cost_inr (n × `COST_PER_WRONG_ANSWER_INR`, overridable per workspace via a settings row), severity, representative run (highest score); write `incident_event`s.
   - Title generation in plain words per section 4.2, including detecting "search returned an archived policy" when the top retrieved passage of the likely-cause retrieve step has `status=archived`.
   - `explain_incident(incident)`: one plain paragraph built from the representative conversation (customer message, wrong reply, correct answer, archived vs current article when applicable).
   - Status transitions with events: open → investigating → fix_verified → resolved, and reopen.
2. `verify_fix(incident_id, repair_run_id)`: read the winning strategy override from the repair run's `replay_spec`, apply the same override (same step name, mapped to each run's matching step key) to every affected run via `replay(origin="repair")`, concurrently (max 4); store `verify_result {n_total, n_passed, run_ids, tokens_saved}`; set `fix_verified` if ≥ 80% pass; events throughout.
3. `on_run_finished(run)` hook for origins `live` and `simulated` in business workspaces: failed → diagnose → assign_incident → call `notify.evaluate_rules(...)` (create a stub module `blackbox/notify/rules.py` with `evaluate_rules` as a no-op if B03 isn't done yet).
4. Simulator `blackbox/incidents/simulate.py` + `bb simulate --workspace nimbu --n 30 --failure-rate 0.35 --seed 7`: picks random Nimbu tasks; injects faults for the chosen share (weights: DISTRACTOR_RETRIEVAL 0.5, WRONG_EXTRACTION 0.2, PLAN_CORRUPT 0.1, HALLUCINATED_SYNTHESIS 0.1, BAD_QUERY 0.1 where applicable); origin `simulated`; runs `on_run_finished`; reports progress counters (sent, wrong, incidents opened, emails queued). Expose a job runner function for the API.
5. CLI: `bb incidents list --workspace nimbu`, `bb incidents show ID`, `bb incidents verify ID --repair-run RUN`.
6. Tests (FakeLLM, temp DB): two runs with the same pattern join one incident; severity thresholds; archived-policy title detection; verify_fix applies the override to all runs and sets fix_verified; hook ignores bisect/replay/repair/datagen origins.

## Acceptance
`make test` passes. `bb simulate --workspace nimbu --n 20 --failure-rate 0.4` creates at least one incident; `bb incidents show` prints a sensible title, paragraph, and timeline.
