# 12 — Business Edition: Black Box for E-commerce Customer Support

This document extends the project. Everything in docs 01–11 still applies unless this document says otherwise. Where it changes the schema, the change is listed explicitly in section 5 ("Schema v2") and is approved.

---

## 1. The business story

**Customer:** an Indian D2C home and kitchen brand, **Nimbu Living** (fictional), selling cookware, appliances, bedsheets, lamps, and decor online. Payments by card, UPI, EMI, and cash on delivery (COD).

**Their AI:** a customer-support agent on the website and WhatsApp that answers questions from the help center: returns, refunds, shipping, COD, cancellations, warranty, loyalty points.

**Their problem:** the agent sometimes answers wrong. The most common cause: the help center contains old (archived) policies next to current ones, and the agent quotes the old one. A customer is told "you have 30 days to return" when the policy is 7 days. That turns into a refund dispute, a human escalation, a chargeback, or a 1-star review. Engineers spend hours reading conversation logs to find out why.

**What Black Box gives them:**
1. **Detects** wrong answers and groups them into **incidents** ("Refund questions answered with an archived policy — 14 conversations").
2. **Finds the likely cause** of each failure, with evidence.
3. **Emails the support-AI team** the moment an incident opens, with the diagnosis inside the email.
4. **Tries fixes**, then **verifies the fix on every affected conversation** before anyone ships it.
5. **Tracks** the incident to resolution, with a timeline and the estimated money at stake.

**Positioning line:** *"Sentry for AI support agents — find why your bot answered wrong, fix it, and prove the fix, before customers notice."*

### Why this matters for judges
- The business damage is instantly understandable ("told a customer 30 days, policy says 7").
- The technical engine is unchanged: the support agent has the same plan → retrieve → extract → check → synthesize shape.
- It adds a **cross-domain result**: the diagnosis model is trained on the public HotpotQA benchmark and evaluated, without retraining, on the store's support conversations.

---

## 2. Workspaces

The app now has **workspaces**, each an agent + its knowledge base:

| Workspace id | Display name | Purpose |
|---|---|---|
| `nimbu` | Nimbu Living support | The business product and the demo story (default in the UI) |
| `hotpot` | Benchmark (HotpotQA) | Training data and the credible public-benchmark evaluation |

A workspace switcher in the header changes which workspace every page shows. All existing data belongs to `hotpot`.

**Vocabulary changes in the `nimbu` workspace** (the UI uses these words; the `hotpot` workspace keeps the original words):

| Generic | Nimbu workspace |
|---|---|
| run | conversation |
| question | customer message |
| final answer | agent reply |
| gold answer | correct answer (per policy) |
| passage | help article |
| task | support question |

---

## 3. The Nimbu Living help center (seed data)

Seed files are **hand-authored and committed to git** (not in `data/`):
`blackbox/workspaces/nimbu/articles.json` and `blackbox/workspaces/nimbu/questions.json`.

### 3.1 Articles (~40)

Each article: `{ "aid": "a_returns_current", "title": "...", "category": "...", "status": "current" | "archived", "updated": "2026-01-10", "text": "3–8 sentences" }`.

**Current policy facts (the ground truth — every current article must agree with these exactly):**

| Topic | Current policy |
|---|---|
| Return window | 7 days from delivery |
| Festive sale returns | Orders placed during the Diwali sale (20 Oct – 5 Nov) get a 15-day return window |
| Final-sale items | Not returnable; damaged or defective items can be exchanged within 48 hours |
| Return pickup fee | ₹99 deducted from the refund, waived if the item is damaged or wrong |
| Prepaid refunds | To the original payment method in 5–7 business days |
| COD refunds | Instant Nimbu store credit, or bank transfer (NEFT) in 7–10 business days after the customer shares bank details |
| Free shipping | On orders above ₹999; otherwise shipping costs ₹79 |
| Delivery time | Metro cities 2–4 business days; rest of India 4–7; North-East and J&K 7–10 |
| COD | Available for orders up to ₹10,000; COD fee ₹49 |
| Cancellation | Free before dispatch; after dispatch the customer can refuse delivery, and prepaid orders are refunded minus ₹79 shipping |
| Address change | Allowed until the order is packed, usually within 12 hours of ordering |
| Warranty | Cookware 2 years; appliances 1 year (brand warranty); textiles have no warranty |
| Damaged on arrival | Report within 48 hours with unboxing photos or video; replacement ships in 3–5 business days |
| Size/colour exchange | Within 7 days, once per order, free |
| Nimbu Points | Earn 1 point per ₹100; 1 point = ₹1; points expire after 12 months; points can pay up to 20% of an order |
| Gift cards | Valid 12 months; non-refundable; cannot be bought with Nimbu Points |
| No-cost EMI | On orders above ₹3,000 with select credit cards, for 3 or 6 months |
| International shipping | Not available; India only |
| GST invoice | Downloadable from My Orders; a business GSTIN must be added before placing the order |
| Order tracking | Tracking link by SMS and email after dispatch |

**Archived articles (~8) — realistic old versions that contradict current policy.** These are the natural distractors that make the business failure story real:
- "Return policy (2024)": 30-day return window
- "Shipping charges (2024)": free shipping above ₹499, otherwise ₹49
- "Cash on delivery (2024)": COD up to ₹5,000, fee ₹30
- "International orders (2023)": shipping to the UAE available
- "Nimbu Points (2024)": points never expire
- "Refunds for COD orders (2024)": refunds only by cheque
- "Warranty (2023)": all products 1 year
- "Exchange policy (2024)": exchanges within 15 days

Also add 3–4 **near-duplicate current articles** on related topics (e.g. "Returns for final-sale items", "Returns during the Diwali sale") so retrieval has to discriminate.

### 3.2 Support questions (~40)

Each: `{ "qid": "nq_001", "question": "customer message in natural, slightly informal Indian English", "answer": "short gold span", "category": "returns|refunds|shipping|payments|orders|warranty|loyalty|giftcards", "qtype": "lookup|bridge|comparison", "gold_aids": [...], "distractor_aids": [...] }`

- Gold answers are **short spans** so scoring works: "7 days", "₹79", "No", "Yes", "2 years", "15 days", "5–7 business days".
- Mix: ~15 lookup (one fact), ~15 bridge (need two facts in sequence), ~10 comparison.
- `distractor_aids` lists the archived or near-duplicate articles that could mislead.

Examples:
- "my order total is ₹850, do i have to pay for delivery and how much?" → "₹79" (bridge: threshold, then fee)
- "Can I use my Nimbu Points to buy a gift card?" → "No"
- "I bought a bedsheet on 25 October in the Diwali sale. How many days do I have to return it?" → "15 days" (bridge: sale dates, then sale return window)
- "Is COD available for a ₹12,000 order?" → "No"
- "Do cookware and appliances have the same warranty period?" → "No" (comparison)
- "How long does it take to get my money back for a prepaid order?" → "5–7 business days"

### 3.3 Retrieval

- Passage id for articles: `p_` + aid. Passage meta includes `status`, `updated`, `category`.
- Separate index per workspace: `data/{workspace}/passages.jsonl`, `data/{workspace}/embeddings.npy`.
- `Retriever.for_workspace(ws)`; existing HotpotQA code becomes workspace `hotpot` (move files into `data/hotpot/` with a one-time migration that leaves old paths working until migrated).
- Retrieval returns archived articles too (that's the realistic failure). Current articles are not boosted by default.

### 3.4 Agent framing for Nimbu

Same plan-execute agent and step keys. Prompts get a workspace-specific system preamble: "You are the customer support assistant for Nimbu Living, an Indian home and kitchen store. Answer only from the help articles provided. Keep answers short." Prompt text stays part of the step input (hashed).

### 3.5 New repair strategy (business-specific)

For `retrieve` steps: **"Search current articles only"** — re-run retrieval filtering out `status = archived`. This is the fix that the demo lands on, and it's exactly what a real support team would ship.

---

## 4. Incidents

### 4.1 What an incident is

An incident groups failed conversations that share the same failure pattern, so the team handles one problem instead of 14 conversations.

**Grouping key:** `(workspace, category, likely-cause step name, top reason feature)` within a rolling 7-day window. Example: (`nimbu`, `returns`, `retrieve`, `query_title_overlap`).

A failed run joins the open incident with the same key, or opens a new one.

### 4.2 Incident fields

- **Title**, generated in plain words: "{Category} questions answered wrong — {pattern}". Pattern phrases by reason feature, e.g. "search returned an archived policy" (when the retrieved top article is archived), "answer not found in the help article", "final reply doesn't match the facts found", "plan missed part of the question".
- **Severity**: `low` (1–2 conversations), `medium` (3–9), `high` (10+ or estimated cost ≥ ₹5,000).
- **Estimated cost**: affected conversations × `COST_PER_WRONG_ANSWER_INR` (default 450, configurable; always labelled "estimated" in UI and email, with the tooltip "Average cost of a refund dispute or human escalation. Change it in Settings.").
- **Status**: `open` → `investigating` → `fix_verified` → `resolved` (and `reopened`).
- **Owner** (free text name), **first seen**, **last seen**, **affected run ids**.
- **Representative conversation**: the affected run with the highest diagnosis score.
- **Timeline events**: opened, conversation added, notified, status changed, fix tried, fix verified, resolved, reopened — each with timestamp and a one-line description.

### 4.3 Verify fix on similar conversations

After a fix works on the representative conversation, **"Verify on all N conversations"** applies the same strategy (same step name, same override params) to every affected conversation via replay. Result: "Fix verified on 12 of 14 conversations." If ≥ 80% pass, status becomes `fix_verified` automatically. Each verification replay reuses unaffected steps, and the total tokens saved are shown.

### 4.4 Traffic simulator

`bb simulate --workspace nimbu --n 30 --failure-rate 0.35 [--seed 7]` runs random Nimbu support questions; for a share of them it injects a realistic fault (weighted toward `DISTRACTOR_RETRIEVAL` with archived articles), so incidents form naturally. Each simulated run: diagnose → attach to incident → evaluate notification rules. This is how the demo populates the Overview and triggers emails live. Also available via `POST /api/simulate` as a job.

### 4.5 Production hook

`on_run_finished(run)` is called after any run with origin `live` or `simulated` in a business workspace: if failed → diagnose → assign incident → evaluate rules → queue notifications. Never triggered for datagen, bisect, replay, or repair runs.

---

## 5. Schema v2 (approved changes)

Additions only; nothing removed or renamed.

- `task`: add `workspace` (str, indexed, default `hotpot`), `category` (str, nullable).
- `run`: add `workspace` (str, indexed, default `hotpot`), `incident_id` (str, nullable, indexed). New origin value `simulated`.
- New table `incident`: `incident_id`, `workspace`, `group_key`, `title`, `category`, `cause_step_name`, `cause_feature`, `severity`, `status`, `owner`, `est_cost_inr`, `n_runs`, `representative_run_id`, `first_seen`, `last_seen`, `resolved_at`, `verified_strategy` (JSON, nullable), `verify_result` (JSON, nullable).
- New table `incident_event`: `event_id`, `incident_id`, `kind`, `text`, `created_at`, `meta` (JSON).
- New table `recipient`: `recipient_id`, `name`, `email`, `workspace`, `active`, `rules` (JSON list of rule kinds subscribed).
- New table `notification_rule`: `rule_id`, `workspace`, `kind`, `enabled`, `params` (JSON).
- New table `notification_log`: `notification_id`, `workspace`, `rule_kind`, `incident_id` (nullable), `recipients` (JSON), `subject`, `html`, `text`, `status` (`queued|sent|failed|throttled`), `error` (nullable), `created_at`, `sent_at`.

Migration: a `bb db migrate` command that adds the columns/tables to an existing DB without losing data (SQLite `ALTER TABLE ADD COLUMN` + `CREATE TABLE IF NOT EXISTS`), and backfills `workspace='hotpot'`.

Leakage rule still holds: no feature reads incident, notification, or workspace tables.

---

## 6. Notifications (SMTP)

### 6.1 Configuration (`.env`)

```
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
SMTP_STARTTLS=0
SMTP_SSL=0
SMTP_FROM="Black Box <alerts@blackbox.local>"
APP_BASE_URL=http://localhost:5173
COST_PER_WRONG_ANSWER_INR=450
NOTIFY_THROTTLE_MINUTES=30
DIGEST_HOUR_LOCAL=9
```

- **Demo / local:** **Mailpit**, a local SMTP server with a web inbox. SMTP on port 1025, inbox at `http://localhost:8025`. Works with no internet.
  - Windows: download `mailpit-windows-amd64.zip` from the Mailpit GitHub releases page, unzip, run `mailpit.exe`.
  - Docker: `docker run -d --name mailpit -p 8025:8025 -p 1025:1025 axllent/mailpit`.
  - Mac: `brew install mailpit && mailpit`.
- **Real email:** Gmail SMTP: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_STARTTLS=1`, user = Gmail address, password = a Gmail **app password** (not the account password). Any company SMTP server works the same way.
- The SMTP password lives only in `.env`. It is never stored in the database, never returned by the API, never logged.

### 6.2 Implementation

- Python standard library only: `smtplib` + `email.message.EmailMessage` (multipart: plain text + HTML). No extra dependency.
- Sending happens on a background worker thread fed by a queue; the API never blocks on SMTP. Each send: 10 s timeout, 2 retries with backoff, result written to `notification_log`.
- **Throttling:** at most one email per (incident, rule kind) every `NOTIFY_THROTTLE_MINUTES`; throttled sends are logged with status `throttled`.
- **Demo-mode safety:** with `BLACKBOX_DEMO_MODE=1`, SMTP still works if it points to `localhost` (Mailpit); if it points to a remote host, emails are logged as `queued` but not sent, and the UI says so.
- If SMTP isn't configured or the server is unreachable, nothing crashes: the log shows `failed` with the error, and Settings shows "Can't reach the mail server at localhost:1025. Start Mailpit or update SMTP settings in .env."

### 6.3 Rules

| Rule kind | Fires when | Default |
|---|---|---|
| `incident_opened` | a new incident is created | on |
| `incident_escalated` | severity rises to high | on |
| `failure_rate` | failure rate over the last 60 min exceeds `params.threshold` (default 0.20) with at least `params.min_runs` (default 10) conversations | on |
| `fix_verified` | an incident becomes `fix_verified` | on |
| `incident_resolved` | an incident is resolved | off |
| `daily_digest` | once a day at `DIGEST_HOUR_LOCAL` | on |

Recipients subscribe to rule kinds. Seed one recipient from `.env` `NOTIFY_DEFAULT_EMAIL` if set (default `support-ai@nimbu.local`).

Digest scheduling: a lightweight background thread in the API process checks every minute; plus `bb notify digest` and a "Send digest now" button.

### 6.4 Email content

Subjects (sentence case, specific, no emoji, no "[ALERT]" prefixes):
- New incident: **"New incident: refund questions answered wrong (14 conversations)"**
- Escalated: **"Incident is now high severity: refund questions answered wrong"**
- Failure rate: **"Support agent failure rate is 31% in the last hour (threshold 20%)"**
- Fix verified: **"Fix verified on 12 of 14 conversations: refund questions answered wrong"**
- Resolved: **"Resolved: refund questions answered wrong"**
- Digest: **"Daily summary for Nimbu Living support: 3 open incidents, ₹6,300 estimated cost"**

Body of the new-incident email (HTML and plain text carry the same content):
1. One-sentence summary: "14 customers got a wrong answer about refunds since 10:42."
2. Example conversation: customer message, agent reply (wrong), correct answer per policy.
3. **Likely cause:** step name in plain words ("Searching the help center") + the top reason sentence + evidence (e.g. "Top article was 'Return policy (2024)', which is archived").
4. Estimated cost (labelled as an estimate).
5. Button **"Open incident"** → `{APP_BASE_URL}/incidents/{id}`; secondary link "View the example conversation".
6. Footer: "You get this email because you're subscribed to new incidents for Nimbu Living support. Change this in Black Box → Settings → Notifications."

HTML email design (emails need table layout and inline CSS):
- 600px max width, white panel on `#EEF1F2`, text `#14202B`, secondary `#5B6873`, borders `#C9D2D8`.
- Wordmark: 12px `#FF4F00` square + "Black Box" in Arial/Helvetica bold (web fonts aren't reliable in email).
- Severity shown as a word with a small colored dot: high `#C8223A`, medium `#D48A00`, low `#5B6873`.
- Evidence in a left-bordered block. Button: `#FF4F00` background, white text, 6px radius, bulletproof table-based button.
- Templates in `blackbox/notify/templates/` using Python `string.Template` or Jinja2 (Jinja2 is acceptable since FastAPI setups often include it; prefer stdlib if simple).

---

## 7. Business UI

The `nimbu` workspace is the default. The navigation becomes:

**Overview · Incidents · Conversations · Evaluation · Live lab · Settings**

(Fleet is folded into Overview. In the `hotpot` workspace, Incidents and Overview still work but are mostly empty; Conversations is the old Runs page.)

Visual identity, tokens, typography, and copy rules: unchanged, from `11-FRONTEND-DESIGN.md`. Currency formatting: `₹6,300` with Indian digit grouping (`Intl.NumberFormat('en-IN')`).

### 7.1 Header

Add a **workspace switcher** left of the nav: current workspace name with a chevron; menu lists workspaces with a one-line description. Persist the choice in the URL (`?ws=nimbu`) and localStorage.

### 7.2 Overview `/` (new home)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Nimbu Living support                                                        │
│ 3 open incidents. Refund questions are failing most.                        │
│                                                                            │
│ 1,240          6.8%            ₹14,850          1.2 ms         9 of 11     │
│ conversations  answered wrong  estimated cost   to find the    fixes       │
│ this week      this week       of wrong answers cause          verified    │
├──────────────────────────────────────┬─────────────────────────────────────┤
│ Wrong answers per day (7 days)       │ Open incidents                     │
│  line chart, threshold line dashed   │  ● High  Refund questions… 14  ₹6,300│
│                                      │  ● Med   Shipping fee…      5  ₹2,250│
├──────────────────────────────────────┼─────────────────────────────────────┤
│ Where failures start                 │ Most common reasons                │
│  bars by step                        │  bars by reason                     │
└──────────────────────────────────────┴─────────────────────────────────────┘
```

- Headline sentence generated from data (largest open incident's category).
- KPI row: same component as Evaluation (`KpiRow`), plain-language captions.
- Line chart: wrong-answer rate per day, threshold from the `failure_rate` rule as a dashed `caution` line.
- Open incidents: compact list (severity dot + word, title, conversations, estimated cost), click → incident.
- "Where failures start" and "Most common reasons": the Fleet charts, scoped to this workspace.
- Empty state: "No conversations yet. Run the traffic simulator from Live lab to see how Black Box catches wrong answers."

### 7.3 Incidents `/incidents`

Table: Severity (dot + word) · Title · Conversations (number) · Estimated cost (₹) · Status chip · Last seen · Owner. Filters: status (default "Open and investigating"), severity, category. Row → incident detail. Empty: "No open incidents. Wrong answers will be grouped here as they happen."

### 7.4 Incident detail `/incidents/:id` — the business hero screen

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ← Incidents                                                                 │
│ Refund questions answered wrong — search returned an archived policy        │
│ ● High   14 conversations   ₹6,300 estimated   Open since 10:42   Owner: —  │
│                         [Notify team] [Assign] [Status: Open ▾]             │
├───────────────────────────────────────────┬────────────────────────────────┤
│ What's going wrong                        │ Timeline                      │
│ Customers asking about refunds get the    │ 10:42 Opened                   │
│ old 30-day policy instead of the current  │ 10:42 Emailed support-ai@…     │
│ 7-day policy.                             │ 10:51 3 more conversations     │
│                                           │ 11:05 Fix tried: current only  │
│ Likely cause: Searching the help center   │ 11:06 Fix verified on 12 of 14 │
│  • Top article was "Return policy (2024)" │                                │
│    — archived                             │                                │
│  • Answer "30 days" contradicts the       │                                │
│    current article                        │                                │
├───────────────────────────────────────────┤                                │
│ Fix                                        │                                │
│ ① Try fixes on the example conversation   │                                │
│ ② Verify on all 14 conversations          │                                │
│ ③ Resolve                                  │                                │
├───────────────────────────────────────────┴────────────────────────────────┤
│ Affected conversations                                                     │
│ Customer message                    Agent reply   Correct    Likely cause  │
│ "can i return my lamp after 2 wks"  "Yes, 30 days" "No…"     retrieve .91  │
└────────────────────────────────────────────────────────────────────────────┘
```

- Header: generated title, severity, conversations, estimated cost, "Open since", owner, actions: **Notify team** (sends the incident email now, bypassing throttle, after a confirm), **Assign** (popover with a name field), **Status** menu.
- "What's going wrong": one plain-language paragraph generated from the representative conversation (e.g. contrast between the archived and current article), then the likely cause with the top 2 reasons and evidence (reuse the Why-tab reason block).
- **Fix panel** — a genuine 3-step sequence, so numbering is earned:
  1. **Try fixes on the example conversation** → opens the existing Try fixes drawer on the representative run.
  2. **Verify on all N conversations** → enabled once a fix works; shows progress "Verifying 9 of 14…", then "Fix verified on 12 of 14 conversations. 2 still fail — open them to investigate." with stat chips (tokens saved across all replays).
  3. **Resolve** → confirm dialog with an optional note; sends the resolved email if that rule is on.
- Timeline: vertical list, newest at the bottom, each event a time (B612 Mono) + one line. Notification events link to the email preview.
- Affected conversations table: customer message (one line), agent reply (in `warning` color), correct answer, likely cause chip with score; row → conversation detail.

### 7.5 Conversations `/conversations` and conversation detail `/conversations/:id`

The existing Runs page and Run detail, with the Nimbu vocabulary from section 2:
- Header shows "Customer message", "Agent reply" (and "Correct answer per policy").
- Retrieval passage cards show the article title, an **"Archived"** badge (`caution-tint`, plain word) for archived articles, and the updated date. This badge is what makes the cause obvious on screen.
- A link "Part of incident: …" when the run belongs to an incident.
- `/runs/:id` routes keep working (redirect to `/conversations/:id`).

### 7.6 Settings `/settings/notifications`

```
┌ Mail server ───────────────────────────────────────────────────────────────┐
│ ● Connected to localhost:1025 (Mailpit)       [Send test email]            │
│ Sender: Black Box <alerts@blackbox.local>                                   │
│ Change these in the .env file on the server.                                │
├ Recipients ────────────────────────────────────────────────────────────────┤
│ Name           Email                     New  High  Rate  Fixed  Digest     │
│ Support AI     support-ai@nimbu.local    ☑    ☑     ☑     ☑      ☑   Remove │
│ [+ Add recipient]                                                           │
├ Rules ─────────────────────────────────────────────────────────────────────┤
│ New incident                  ☑                                             │
│ Failure rate above [20]% with at least [10] conversations in an hour  ☑    │
│ Daily summary at [09:00]      ☑            [Send summary now]               │
│ Cost per wrong answer  ₹[450]  (used for estimates)                          │
├ Sent emails ───────────────────────────────────────────────────────────────┤
│ 11:06  Fix verified on 12 of 14…   support-ai@…   Sent        Preview       │
│ 10:42  New incident: refund…       support-ai@…   Sent        Preview       │
│ 10:44  New incident: refund…       support-ai@…   Throttled   Preview       │
└────────────────────────────────────────────────────────────────────────────┘
```

- Mail server status from `GET /api/notifications/status` (host, port, connected yes/no, last error). Never shows the password.
- "Send test email" → sends to a typed address (defaults to the first recipient); result shown inline: "Test email sent to support-ai@nimbu.local. Check your inbox (Mailpit: localhost:8025)."
- Recipients: inline add (name + email with validation), rule-subscription checkboxes with column headers in plain words, remove with confirm.
- Rules: toggles and numeric inputs; save on change with a small "Saved" confirmation.
- Sent emails log: time, subject, recipients, status chip (Sent `normal`, Failed `warning`, Throttled `graphite`, Queued `caution`), Preview → drawer with the HTML email rendered in a sandboxed iframe (`sandbox=""`, `srcdoc`) plus a "Plain text" tab.

### 7.7 Live lab (business mode)

In the `nimbu` workspace, Live lab gets two modes via a segmented control:
- **One conversation** (existing flow, with Nimbu questions and plain-language failure presets such as "Search returns an archived article").
- **Simulate traffic**: "Send [30] customer messages with about [35]% going wrong" → **Start simulation** → live counters (sent, answered wrong, incidents opened, emails sent) and a link "Open Mailpit inbox" (`http://localhost:8025`) and "Open Overview".

---

## 8. API additions

All existing endpoints accept `?workspace=` (default `hotpot` for backward compatibility; the frontend always sends it).

- `GET /api/workspaces` → `[{id, name, description, n_runs}]`
- `GET /api/overview?workspace=` → `{headline, kpis, daily: [{date, conversations, wrong, rate}], open_incidents: [IncidentSummary], by_step_name, by_reason, threshold}`
- `GET /api/incidents?workspace=&status=&severity=&category=&limit=&offset=` → `{items: [IncidentSummary], total}`
- `GET /api/incidents/{id}` → `{incident, explanation, representative_run, reasons, runs: [RunSummary + {customer_message, agent_reply, correct_answer}], events: [IncidentEvent], notifications: [NotificationSummary]}`
- `PATCH /api/incidents/{id}` body `{status?, owner?, note?}` → incident
- `POST /api/incidents/{id}/verify-fix` body `{repair_run_id}` → `{job_id}`; job result `{n_total, n_passed, run_ids, tokens_saved}`
- `POST /api/incidents/{id}/notify` → `{notification_id}`
- `GET /api/notifications/status` → `{configured, host, port, connected, sender, last_error, demo_mode_blocked}`
- `POST /api/notifications/test` body `{to}` → `{status, error}`
- `GET/POST/PATCH/DELETE /api/recipients[/{id}]`
- `GET /api/rules?workspace=` / `PUT /api/rules/{rule_id}` body `{enabled, params}`
- `GET /api/settings/business?workspace=` / `PUT` body `{cost_per_wrong_answer_inr}`
- `GET /api/notifications?workspace=&limit=` → log list
- `GET /api/notifications/{id}/preview` → `{subject, html, text}`
- `POST /api/notifications/digest` → sends the digest now
- `POST /api/simulate` body `{workspace, n, failure_rate, seed?}` → `{job_id}`; `GET /api/jobs/{id}` progress `{sent, failed, incidents_opened, emails_sent}`

`IncidentSummary = {incident_id, title, severity, status, n_runs, est_cost_inr, category, cause_step_name, first_seen, last_seen, owner}`

---

## 9. Evaluation addition: cross-domain test set D

- Generate Nimbu fault runs the same way as HotpotQA (clean runs, faults, bisect labels) — about 40 questions × faults.
- **Test set D — "Support conversations (never trained on)":** the HotpotQA-trained model, no retraining, evaluated on Nimbu labels. Report Top-1, Top-3, MRR vs. the same baselines.
- Optional calibration: per-workspace reference statistics computed from **successful** Nimbu conversations only (no labels needed). Report D with and without calibration.
- Evaluation page gets a fourth test-set option: "Support conversations".

Pitch line: *"Trained on a public Wikipedia benchmark. Dropped onto a support bot it had never seen. It still finds the cause X% of the time."*

---

## 10. Updated 3-minute demo

1. **Overview** of Nimbu Living support — healthy. (10s)
2. Live lab → **Simulate traffic**, 30 messages. Counters tick; an incident opens. (20s)
3. Switch to the **Mailpit inbox**: "New incident: refund questions answered wrong (9 conversations)" has arrived. Open it: example conversation, likely cause "search returned an archived policy", estimated cost. Click **Open incident**. (25s)
4. **Incident detail**: archived article badge, reasons. Step 1 **Try fixes** → "Search current articles only" passes, with the reuse stats. Step 2 **Verify on all 9** → "Fix verified on 9 of 9." (40s)
5. Back in Mailpit: "Fix verified…" email arrived. (10s)
6. **Resolve**. Close on the results slide, including the cross-domain number. (rest)
