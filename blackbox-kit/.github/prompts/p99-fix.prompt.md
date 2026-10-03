---
description: "P99 — Focused bug fix (paste the error below)"
mode: agent
---
A bug needs fixing. Rules:
- First reproduce it: find and run the smallest command or test that shows the failure.
- Identify the root cause and explain it in 2–3 sentences before editing.
- Change the minimum number of lines in the minimum number of files. Do not refactor, rename, or touch the schema in `docs/03-DATA-MODEL.md`.
- Add or update a test that would have caught it (FakeLLM only, no network).
- Run `make test` and the original failing command; report results.

Error / symptom:
${input:error:Paste the error, stack trace, or describe the wrong behaviour}
