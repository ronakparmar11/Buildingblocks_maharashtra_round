# Business edition build log

| Phase | Status | Files changed | Decisions and remaining work |
| --- | --- | --- | --- |
| Phase 0 — kit unpack | done | `blackbox-kit/docs/12-BUSINESS-EDITION.md`, `blackbox-kit/.github/prompts/{b00-b04,f10-f14}*.prompt.md` | Extracted `business-kit.zip`, copied the supplied files, verified b00-b04, f10-f14, and matching document checksums, then removed `_bk`. This is the final permitted write inside `blackbox-kit/`. |
| b00 — schema, workspaces, seed | done | `blackbox/store/{models,db}.py`, `blackbox/corpus/{paths,nimbu,hotpot,embed,retriever}.py`, `blackbox/workspaces/`, `blackbox/cli.py`, `tests/test_{migration,nimbu_seed,corpus}.py` | Added exact schema v2 models and backup-first idempotent migration; the real DB backup is `data/blackbox.backup-20261003T174542900373Z.db`. Kept legacy Hotpot files and copy them once into `data/hotpot/`. Added 40 Nimbu articles (32 current, 8 archived), 40 grounded questions (15 lookup, 15 bridge, 10 comparison), 70/30 tasks, per-workspace indexes, and archived filtering. `make test`: 54 passed. Ruff passed. Real migration succeeded twice (second run no-op). Nimbu build produced 40 passages/tasks; return search returned archived and current policies in the top six. |
| b01 — Nimbu agent data and eval | pending | — | — |
| b02 — incidents and simulator | pending | — | — |
| b03 — SMTP notifications | pending | — | — |
| b04 — business API | pending | — | — |
| f10 — business shell and overview | pending | — | — |
| f11 — incidents | pending | — | — |
| f12 — settings and notifications | pending | — | — |
| f13 — conversations and Live Lab | pending | — | — |
| f14 — business real API | pending | — | Reserved for the user; do not run in this build. |