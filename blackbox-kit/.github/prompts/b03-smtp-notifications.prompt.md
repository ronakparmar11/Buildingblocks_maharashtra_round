---
description: "B03 — SMTP notifications: mailer, HTML/text templates, rules, throttling, log, digest, test email"
mode: agent
---
Read [Business edition](../../docs/12-BUSINESS-EDITION.md) section 6 fully (and 4 for incident fields).

## Tasks
1. Settings: add every `.env` variable from section 6.1 to `blackbox/config.py` and `.env.example` (with Mailpit defaults and commented Gmail example). Add `NOTIFY_DEFAULT_EMAIL`.
2. `blackbox/notify/mailer.py`: stdlib `smtplib` + `email.message.EmailMessage` (multipart text + HTML); STARTTLS/SSL/plain per settings; login only if user set; 10 s timeout; 2 retries with backoff; `check_connection()` for status; never log the password.
3. `blackbox/notify/worker.py`: background thread + queue; writes every attempt to `notification_log` with status queued/sent/failed/throttled and error text. Demo-mode safety exactly as 6.2.
4. `blackbox/notify/templates/`: HTML (table layout, inline CSS, 600px, design per 6.4, bulletproof orange button) and plain-text versions for: incident_opened, incident_escalated, failure_rate, fix_verified, incident_resolved, daily_digest, test. Subjects exactly as section 6.4. Indian number formatting for ₹. Links use `APP_BASE_URL`.
5. `blackbox/notify/rules.py`: replace the B02 stub. `evaluate_rules(event, workspace, incident=None)` checks enabled rules, recipients subscribed, throttling per (incident, kind) using `NOTIFY_THROTTLE_MINUTES`, failure-rate window (last 60 min, threshold, min_runs). Seed default rules and the default recipient on first use.
6. Wire events: incident created → incident_opened; severity → high → incident_escalated; status fix_verified → fix_verified; resolved → incident_resolved; failure-rate check after each finished business run.
7. Digest: background scheduler thread (checks every 60 s, sends once per day at `DIGEST_HOUR_LOCAL`, guarded against double sends), plus `bb notify digest`.
8. CLI: `bb notify test --to you@example.com`, `bb notify status`, `bb notify log`.
9. Tests: use a fake SMTP server (`aiosmtpd` if available as a dev dependency, or monkeypatch `smtplib.SMTP` with a recorder): message is multipart with both parts, subject format, throttling, failed send logged without raising, password never appears in logs or log rows.

## Acceptance
- With Mailpit running (`localhost:1025`, inbox `localhost:8025`): `bb notify test --to support-ai@nimbu.local` arrives and renders correctly in the Mailpit inbox.
- `bb simulate --workspace nimbu --n 20 --failure-rate 0.4` produces an incident email in Mailpit with the example conversation, likely cause, evidence, estimated cost, and a working "Open incident" link.
- With Mailpit stopped, sends are logged as failed and nothing crashes.
- `make test` passes.
