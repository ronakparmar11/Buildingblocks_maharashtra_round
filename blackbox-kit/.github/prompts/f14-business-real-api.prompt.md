---
description: "F14 — Connect business screens to the real API and verify the full demo with Mailpit"
mode: agent
---
Read [Business edition](../../docs/12-BUSINESS-EDITION.md) sections 8 and 10, `blackbox/api/schemas.py`, and `frontend/src/api/types.ts`.

The backend is running on port 8000 and Mailpit on 1025/8025.

## Tasks
1. Set `VITE_USE_MOCKS=false`. Walk through Overview, Incidents, Incident detail, Conversations, Settings, and Live lab against the real API.
2. List every mismatch between real responses and types.ts. Fix on the frontend if the backend matches section 8; otherwise report the backend issue without changing backend code.
3. Run the section 10 demo path for real: simulate traffic → incident → email in Mailpit → open incident link → try fixes → verify → resolve → fix-verified email.
4. Report: mismatches fixed, issues found, and the demo checklist with pass/fail per step.

Never run bb generate/label/faults. Never touch data/.
