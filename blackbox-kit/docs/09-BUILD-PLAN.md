# 09 — Build Plan (24 hours, team of 4)

Adjust hours proportionally if the hackathon is shorter or longer. The **order** and the **checkpoints** matter more than the exact hours.

## Roles

| Person | Role | Prompts |
|---|---|---|
| **A** | Agent & replay lead (strongest backend) | P00, P01, P02, P04, P06, P12 |
| **B** | Data & labels | P03, P05, P07, P08 |
| **C** | Model & evaluation | P09, P10, P11 |
| **D** | API, UI & pitch | P13, P14, P15, P16, P17 (with A) |

## Timeline

| Hour | A | B | C | D |
|---|---|---|---|---|
| 0–1 | P00, P01 | read docs 04–05, test API keys | read doc 06, build fixture step table by hand | read docs 07–08 |
| 1–3 | P02 | P03 (download, embed) | P09 on fixtures | P13 in mock mode |
| 3–6 | P04 | P05 | P09 cont. | P14 |
| 6–8 | P06 | help A test replay | baselines skeleton | P14 cont. |
| **8** | **CHECKPOINT 1: clean run → fault run → replay → rows in DB → visible in UI** | | | |
| 8–10 | support B | P07 | P09 on real runs | P15 (replay UI) |
| 10–14 | P12 | **P08 — start bulk generation, runs in background** | P10 v1 on partial data | P15 cont. |
| **14** | **CHECKPOINT 2: model v1 trained, diagnosis visible in UI** | | | |
| 14–18 | organic labeling run, bug fixes | finish generation, organic labels | P10 full + LOFO + LLM judge, P11 | P16 |
| 18–20 | P17 with D | data QA, seed demo tasks | final eval, write numbers | P17 Live Lab |
| **20** | **FEATURE FREEZE** | | | |
| 20–22 | prewarm cassette for demo tasks, demo-mode test with Wi-Fi off | README numbers | eval.md, results slide | slides, record backup video |
| 22–24 | rehearse ×3, buffer | | | |

## Checkpoint rules

- **Checkpoint 1 missed?** Drop P12 and the fleet page from scope immediately.
- **Checkpoint 2 missed?** Drop LOFO, organic, contrastive feature. Seen + held-out results are enough to win.
- Nobody starts a stretch item before Checkpoint 2.

## Data generation budget

~200 hosts × 6 faults × ~1.6 positions ≈ 1,900 fault runs, ~10 steps each. The prefix of a fault run matches its clean run, so the cassette serves it free; roughly 40–50% of LLM calls are cache hits. Bisect replays are mostly cache hits too. Expect ~12–15k real LLM calls total. On free-tier rate limits that can take many hours — **start P08 by hour 10 at the latest**, use a paid key or several keys if rules allow, and set `MAX_CONCURRENCY` to stay just under the limit.

If you're short on time or quota: 120 hosts is still ~1,100 fault runs and enough for LightGBM.

## Cut list (cut from the top)

1. WebSockets (use polling)
2. Contrastive `neighbor_divergence` feature
3. Fleet page
4. LLM-as-judge baseline beyond 50 runs
5. LOFO (keep the single held-out split)
6. Organic failures (keep as "future work", mention method)
7. Auto-repair beyond the top-1 step

**Never cut:** tracer + replay with reuse stats, bisect labels, trained ranker vs. baselines, held-out fault types, Run Detail graph with reasons, compare view, demo mode.

## Risk register

| Risk | Mitigation |
|---|---|
| Rate limits stall data generation | Start early; resumable generation; multiple providers; reduce hosts |
| Nondeterministic replays | Temperature 0 + cassette everywhere from P02; replay test in P06 must pass |
| Agent too good (few organic failures) | Fine — organic is a stretch; or use a smaller model for organic runs |
| Agent too bad (<40% clean pass) | Simplify prompts, raise k to 4, check JSON parsing errors first |
| Faults don't cause failures | Expected; bisect filters. If <30% of fault runs fail, make faults harsher (e.g. replace all passages, not just gold ones) — never inject two faults in one run, it breaks single-culprit labels |
| Model barely beats heuristic | Check leakage-free features are computed correctly; add grounding features; report honestly — held-out and repair results still carry the story |
| Demo crashes on stage | Demo mode, prewarmed cassette, backup video, local DB copy |
