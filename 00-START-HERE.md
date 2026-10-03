# 00 — START HERE: How to build Black Box with Copilot

This kit is everything needed to build **Black Box** (Bit N Build, AI/ML PS 2) with VS Code Copilot in Agent mode using Claude models. The docs are the source of truth; the prompts are the build sequence. Copilot writes the code, you steer, test, and commit.

## What's in the kit

```
blackbox/
├── README.md                         ← judge-facing README (fill in numbers at the end)
├── .github/
│   ├── copilot-instructions.md       ← rules Copilot follows in EVERY chat (auto-loaded)
│   └── prompts/                      ← run these in order: /p00-bootstrap, /p01-..., etc.
└── docs/
    ├── 00-START-HERE.md              ← this file
    ├── 01-PRD.md                     ← what we're building, USP, PS compliance matrix
    ├── 02-ARCHITECTURE.md            ← components, data flow, key design decisions
    ├── 03-DATA-MODEL.md              ← trace schema, DB tables, step keys
    ├── 04-AGENT-AND-FAULTS.md        ← the agent under test + the 6 fault types
    ├── 05-REPLAY-BISECT-REPAIR.md    ← replay engine, counterfactual labeling, auto-repair
    ├── 06-MODEL-AND-EVAL.md          ← features, ranker, explanations, evaluation protocol
    ├── 07-API.md                     ← FastAPI endpoints
    ├── 08-UI.md                      ← screens, components, visual design
    ├── 09-BUILD-PLAN.md              ← timeline, team split, cut list, risks
    └── 10-PITCH-AND-DEMO.md          ← demo script, slides, judge Q&A bank
```

## Setup (do this before the hackathon clock starts, if rules allow)

1. Create the repo, copy this kit into its root, commit: `chore: add build kit`.
2. VS Code → Copilot Chat → switch to **Agent** mode → choose the strongest Claude model available for backend prompts (P02, P04, P06, P07, P10). A faster model is fine for UI and boilerplate.
3. Make sure prompt files are enabled (Settings → search "prompt files" → enable). Then typing `/` in Copilot Chat lists the prompts in `.github/prompts/`.
   - If your VS Code version expects `agent:` instead of `mode:` in the prompt-file header, change it. If prompt files don't work at all, open the file and paste its body into chat.
4. Get API keys: Gemini (primary), Groq (backup). Put them in `.env` (template comes from P00). Budget a few hundred rupees of paid credit if possible — free-tier rate limits are the #1 risk during data generation.

## The workflow (follow it strictly)

1. **One prompt = one fresh chat.** Start a new Copilot chat for each prompt so context stays clean.
2. Run the prompt. Let Copilot create/edit files and run commands.
3. **Run the acceptance checks** listed at the bottom of each prompt yourself. Don't trust "done" — verify.
4. If something fails, use `/p99-fix` with the error pasted in. Don't let Copilot rewrite unrelated files.
5. **Commit after every prompt** that passes: `feat(p04): plan-execute agent`. Small commits = easy rollback.
6. If Copilot starts inventing fields or changing the schema, stop it and point it back to `docs/03-DATA-MODEL.md`. The schema is frozen after P01.

## Prompt order and owners

| # | Prompt | Owner | Depends on |
|---|---|---|---|
| P00 | Bootstrap repo | A | — |
| P01 | Data model + storage | A | P00 |
| P02 | LLM client, cassette, tracer SDK | A | P01 |
| P03 | Corpus + retrieval | B | P00 |
| P04 | Plan-execute agent + scoring | A | P02, P03 |
| P05 | Fault injection | B | P04 |
| P06 | Replay engine | A | P04 |
| P07 | Bisect + counterfactual labeling | B | P05, P06 |
| P08 | Data generation CLI | B | P07 |
| P09 | Feature extraction | C | P01 (mocks), P08 (real data) |
| P10 | Ranker, baselines, evaluation | C | P09 |
| P11 | Explanations | C | P10 |
| P12 | Auto-repair | A | P06, P10 |
| P13 | API | D | P01 (mocks first) |
| P14 | Frontend shell, runs list, run graph | D | P13 |
| P15 | Replay, repair, compare UI | D | P14, P12 |
| P16 | Evaluation + fleet pages | D | P14, P10 |
| P17 | Live Lab + demo hardening + README | D + A | everything |
| P98 | PS compliance review | anyone | near the end |
| P99 | Fix (template) | anyone | anytime |

**Parallelism:** in the first hour, A runs P00–P01 while everyone reads the docs. After P01 is merged, B starts P03, C starts P09 against fixture data, D starts P13 with mock data. Nobody blocks on anybody after hour 2.

## Golden rules

- The **schema in `docs/03-DATA-MODEL.md` is a contract.** Changing it requires the whole team to agree.
- **No LLM calls in tests.** Tests use `FakeLLM`. Real calls only in CLI commands.
- **Fault metadata never reaches the model's features.** That's label leakage and judges will ask.
- **Determinism first.** Temperature 0 + cassette from the very first LLM call.
- **Demo mode** (`BLACKBOX_DEMO_MODE=1`) serves everything from cassette — the demo must work with Wi-Fi off.
