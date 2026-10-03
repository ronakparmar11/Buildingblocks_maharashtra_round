---
description: "F12 — Settings → Notifications: mail server status, test email, recipients, rules, sent emails log"
mode: agent
---
Read [Business edition](../../docs/12-BUSINESS-EDITION.md) sections 6 and 7.6, and [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) sections 4, 13. Reuse the email preview drawer from F11.

## Tasks
1. Route `/settings/notifications` (and `/settings` redirecting to it), with a simple left sub-nav ready for future settings.
2. Mail server panel: status dot + sentence ("Connected to localhost:1025 (Mailpit)" / "Can't reach the mail server at localhost:1025. Start Mailpit or update SMTP settings in .env."), sender, the note that settings live in `.env`, and "Send test email" with an address field and inline result.
3. Recipients: table with plain-word subscription columns (New incident, High severity, Failure rate, Fix verified, Resolved, Daily summary), inline add with email validation, remove with confirm.
4. Rules: toggles and number inputs (failure-rate threshold %, minimum conversations, digest hour), cost per wrong answer in ₹; save on change with a quiet "Saved" confirmation; "Send summary now".
5. Sent emails log: time, subject, recipients, status chip (Sent/Failed/Throttled/Queued), Preview → drawer.
6. A small "Open Mailpit inbox" link when the host is localhost.

## Acceptance
All interactions work on mocks; keyboard accessible; `npm run build` passes.
