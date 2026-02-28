# Backend Migration Plan: Node.js + Express + TypeScript + PostgreSQL on AWS

> **Created:** Feb 27, 2026
> **Status:** Not started
> **Purpose:** Replace Google Apps Script backend with a real Node.js API to enable HubSpot integration, proper auth, and future growth

---

## Strategy

Replace `backend/combined-apps-script.js` (5,146 lines, 30 GET + 48 POST endpoints) with a Node.js + Express + TypeScript API backed by PostgreSQL on AWS RDS.

**Keep all existing HTML frontends as-is** — the only frontend change is updating the `GOOGLE_SHEETS_URL` constant in 4 files to point to the new API URL. A compatibility middleware translates the old request format (`?action=` GET params, routing-field POST bodies) so the frontends work without any other modification.

**What drives this:** HubSpot integration requires a real backend (cron jobs, OAuth, persistent database). Apps Script can't do it.

---

## Project Structure

```
text-my-team/
├── api/                              # NEW — Node.js backend
│   ├── package.json
│   ├── tsconfig.json
│   ├── .env.example
│   ├── Dockerfile
│   ├── docker-compose.yml            # local dev: Postgres + API
│   ├── src/
│   │   ├── index.ts                  # Express entry point
│   │   ├── config/
│   │   │   ├── database.ts           # pg Pool + RLS helper
│   │   │   ├── env.ts               # typed env vars
│   │   │   └── cors.ts
│   │   ├── middleware/
│   │   │   ├── compatibility.ts      # KEY FILE: translates Apps Script request format
│   │   │   ├── session.ts            # minimal session token auth (even before BetterAuth)
│   │   │   ├── tenant.ts             # sets RLS tenant context per request
│   │   │   └── error-handler.ts
│   │   ├── routes/                   # one file per domain
│   │   │   ├── bids.ts
│   │   │   ├── contracts.ts
│   │   │   ├── contacts.ts
│   │   │   ├── crews.ts
│   │   │   ├── invoices.ts
│   │   │   ├── properties.ts
│   │   │   ├── reminders.ts
│   │   │   ├── reports.ts
│   │   │   ├── requests.ts
│   │   │   ├── schedule.ts
│   │   │   ├── signing.ts
│   │   │   ├── templates.ts
│   │   │   ├── tickets.ts
│   │   │   ├── time-entries.ts
│   │   │   ├── uploads.ts
│   │   │   └── hubspot.ts
│   │   ├── engine/                   # Extracted calculation engine (tested independently)
│   │   │   ├── bid-calculator.ts     # quantities ÷ rates → hours → labor → markup → price
│   │   │   ├── ticket-generator.ts   # contract → scheduled events with earned value
│   │   │   ├── schedule-dates.ts     # seasonal mowing, weekly, simple distribution
│   │   │   └── invoice-generator.ts  # contract → monthly invoice line items
│   │   ├── services/                 # business logic
│   │   │   ├── stripe.service.ts
│   │   │   ├── email.service.ts      # SES or SendGrid
│   │   │   ├── upload.service.ts     # S3
│   │   │   └── hubspot.service.ts
│   │   ├── db/
│   │   │   ├── migrations/           # numbered SQL files (001-021)
│   │   │   ├── migrate.ts            # migration runner
│   │   │   └── query.ts              # typed query helper
│   │   └── types/                    # shared TypeScript types (extractable to monorepo later)
│   │       ├── bid.ts
│   │       ├── contract.ts
│   │       ├── crew.ts
│   │       ├── ticket.ts
│   │       └── ...
│   ├── tests/                        # Integration + engine tests from day one
│   │   ├── engine/
│   │   │   ├── bid-calculator.test.ts
│   │   │   ├── ticket-generator.test.ts
│   │   │   └── schedule-dates.test.ts
│   │   ├── workflows/
│   │   │   ├── crew-workflow.test.ts     # login → schedule → clock → complete
│   │   │   └── estimating-workflow.test.ts  # load → create bid → finalize
│   │   └── fixtures/                 # sample data captured from real sheets
│   │       ├── sample-bid.json
│   │       ├── sample-schedule.json
│   │       └── sample-time-entries.json
│   └── scripts/
│       ├── import-sheets.ts          # Google Sheets → Postgres migration
│       ├── import-drive.ts           # Google Drive → S3 file migration
│       └── compare-responses.ts      # Hit same endpoint on both backends, diff output
├── estimate.html                     # UNCHANGED (just update URL constant)
├── crew.html                         # UNCHANGED
├── index.html                        # UNCHANGED
├── sign.html                         # UNCHANGED
├── backend/combined-apps-script.js   # STAYS RUNNING during migration
└── ...
```

---

## Phase 1: Local Dev Environment + Database

### Step 1: Scaffold the project
- [ ] Create `api/` directory
- [ ] `npm init` with `package.json`
- [ ] Install dependencies:
  ```
  npm install express pg cors helmet dotenv uuid stripe node-cron multer
  npm install -D typescript tsx nodemon @types/express @types/pg @types/node @types/cors @types/multer vitest
  ```
- [ ] Create `tsconfig.json` (target ES2022, strict mode)
- [ ] Create `docker-compose.yml` with PostgreSQL 16 on port 5432
- [ ] Create `src/index.ts` with basic Express server + `/health` endpoint
- [ ] Verify: `docker compose up -d && npx tsx src/index.ts` → `curl localhost:3000/health` returns OK

**Important:** Pin PostgreSQL version to 16 in docker-compose.yml. Version mismatches cause subtle issues with UUID generation and JSON operators.

### Step 2: Database migrations
Create SQL migration files for all tables from the architecture doc schema (platform-architecture.md lines 742-1141). Foreign key order:

| # | Table | Replaces (Google Sheet) |
|---|-------|------------------------|
| 001 | `tenants` | Settings sheet (key-value → columns) |
| 002 | `users` | — |
| 003 | `customers` | Contacts sheet |
| 004 | `properties` | Properties sheet |
| 005 | `property_contacts` | PropertyContacts sheet |
| 006 | `sub_contractors` | SubContractors sheet |
| 007 | `production_rates` | Item Catalog sheet |
| 008 | `service_catalog` | Service Catalog sheet (see schema below) |
| 009 | `templates` | Templates sheet |
| 010 | `bids` + `bid_services` + `bid_line_items` | Bids sheet |
| 011 | `contracts` + `contract_services` | Contracts sheet |
| 012 | `crews` + `crew_members` | Crew Members sheet |
| 013 | `scheduled_events` | Scheduled Tickets sheet |
| 014 | `time_entries` | Time Entries sheet |
| 015 | `invoices` + `invoice_line_items` + `payments` | Invoices + Payments sheets |
| 016 | `service_requests` | Requests sheet |
| 017 | `reports` + `service_offers` | — |
| 018 | `reminders` | Reminders sheet |
| 019 | RLS policies on ALL tables | — |
| 020 | Seed Endurance Services tenant | — |

**`service_catalog` table schema** (not in the architecture doc — defined here from the current Google Sheet):
```sql
CREATE TABLE service_catalog (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  division        TEXT NOT NULL DEFAULT 'MNT',      -- MNT, IRR, CON, ENH
  service_name    TEXT NOT NULL,                     -- e.g. "Mowing", "Hedge Trimming"
  proposal_name   TEXT,                              -- customer-facing name on proposals
  default_visits  INTEGER,                           -- default visit count per year
  billing_tier    TEXT DEFAULT 'fixed',              -- 'fixed', 'billed_separately', 'recommended'
  default_description TEXT,                          -- HTML from Quill.js editor
  map_color       TEXT,                              -- hex color for schedule/calendar
  duration_type   TEXT DEFAULT 'scalable',           -- 'scalable' (scales with property size) or 'fixed'
  default_line_items JSONB DEFAULT '[]',             -- array of item names from production_rates
  sort_order      INTEGER DEFAULT 0,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);
```

Every table gets:
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `tenant_id UUID NOT NULL REFERENCES tenants(id)`
- `created_at TIMESTAMPTZ DEFAULT now()`
- `updated_at TIMESTAMPTZ DEFAULT now()`
- RLS policy: `USING (tenant_id = current_setting('app.current_tenant')::uuid)`

### Step 3: RLS tenant middleware
- [ ] Create `src/middleware/tenant.ts`
- [ ] Every request runs `SET app.current_tenant = $1` before any query
- [ ] For now, hardcode Endurance Services tenant UUID (only one company)

---

## Phase 2: Extract and Test the Calculation Engine

> **Why this comes before endpoint porting:** If `calculateBidTotals()` is ported inline inside a route handler and something is slightly off, you won't know until a bid comes out wrong in production. Extracting and testing the calc engine first protects you for the entire migration.

### What to extract (from estimate.html)
- [ ] **Bid calculator** — quantities ÷ production rates → hours → labor cost × markup → bid price. Includes three-tier billing (Fixed, Billed Separately, Recommended), material coverage calculations, difficulty adjustments
- [ ] **Ticket/schedule generator** — contract → visit dates via `getDatesForVisitCount()` with three strategies: `generateSeasonalMowingDates()`, `generateWeeklyDates()`, `generateSimpleScheduleDates()`. Earned value distribution with penny reconciliation
- [ ] **Invoice generator** — contract → monthly invoice line items with billing period dedup

### How to test
- [ ] Capture real data: export 3-5 existing bids from Google Sheets as JSON fixtures
- [ ] Run the TypeScript engine against each fixture
- [ ] Compare output (total price, per-service costs, hours, ticket dates, earned values) against the existing estimate.html output
- [ ] **The numbers must match exactly** — penny-for-penny

### Directory
```
api/src/engine/
├── bid-calculator.ts         # core calculation functions
├── ticket-generator.ts       # date distribution + earned value
├── schedule-dates.ts         # seasonal/weekly/simple strategies
└── invoice-generator.ts      # monthly invoice logic

api/tests/engine/
├── bid-calculator.test.ts    # fixture-based tests
├── ticket-generator.test.ts
├── schedule-dates.test.ts
└── fixtures/
    ├── bid-input-1.json      # captured from real sheet data
    ├── bid-expected-1.json   # captured from estimate.html output
    └── ...
```

---

## Phase 3: Compatibility Layer + All Endpoints

### The compatibility middleware (the most important file)

`src/middleware/compatibility.ts` translates the Apps Script request format:

**GET:** `?action=getCrewSchedule&phone=123` → reads `req.query.action`, routes to handler

**POST:** `{ saveBid: true, bidData: {...} }` → checks for routing field, dispatches to handler

**Response format:** Always `{ success: true, ... }` or `{ success: false, error: '...' }` — identical to Apps Script

### Minimal session token auth (even before BetterAuth)

> **Why:** Apps Script had implicit protection because the URL was obscure. A public App Runner URL doesn't have that. Even during migration, add a minimal session token.

- [ ] When `getCrewSchedule` authenticates by phone, return a `sessionToken` (UUID) in the response alongside the schedule data
- [ ] Store the token in a `sessions` table with `user_id`, `created_at`, `expires_at` (24h TTL)
- [ ] crew.html already stores state in memory — it can save the token and send it on subsequent requests via an `X-Session-Token` header or query param
- [ ] **Require the token on all POST endpoints** (writes)
- [ ] **Require the token on sensitive GETs too:** `getCrewSchedule` (customer addresses, crew phones, GPS data), `getInitData` (full business data), `getInvoices` (financial data), `getPayments`, `getCrewMembers`, `getProductionAnalysis`, `getWeeklyReportData`
- [ ] **Leave truly public GETs open** (no token): `getContractForSigning` (has its own UUID token), `verifyPin` (returns only pass/fail), `getProperties` for index.html (PIN-gated at the app level)
- [ ] This is a small frontend change (add token to fetch calls in crew.html + estimate.html) but prevents anyone from scraping sensitive data off the public URL

### Endpoint implementation priority

**Tier 1 — Crew daily ops (build first, crew uses these every day):**
| Endpoint | Apps Script Line | Notes |
|----------|-----------------|-------|
| `getCrewSchedule` | 2208 | Most complex — auth by phone, load tickets + reminders + time entries |
| `verifyPin` | 2462 | PIN check against crew_members |
| `saveTimeEntry` | ~5030 | Auto-generate TE-0001 IDs |
| `updateTimeEntry` | ~5030 | Handle clock-out, crew changes, undo |
| `deleteTimeEntry` | ~5030 | Cancel ticket |
| `completeJob` | ~5030 | Update ticket status + time entry |
| `updateTicketStatus` | 1380 | scheduled/completed/skipped |
| `getRequests` | 1572 | Auth by phone, filter by crew properties |
| `updateStatus` | 1979 | Request status changes |
| `updateAcknowledged` | 1944 | Mark request acknowledged |
| `bulkSkipDay` | 1462 | Rain day bulk skip |
| `saveRouteOrder` / `getRouteOrder` | 2955 | Route optimization |

**Tier 2 — Estimating (build second):**
| Endpoint | Apps Script Line | Notes |
|----------|-----------------|-------|
| `getInitData` | 20 | Bulk load — 10 datasets in one response |
| `getItemCatalog` | 356 | production_rates table |
| `getBidSettings` | 437 | Tenant settings columns |
| `getBids` | ~468 | All bids |
| `saveBid` / `updateBid` / `deleteBid` | 468/532/662 | CRUD |
| `getContracts` | 987 | All contracts |
| `createContract` / `updateContract` | 821/928 | Finalize + revise |
| `saveTickets` / `getTickets` | 1099/1223 | Ticket generation + retrieval |
| `getContacts` / `saveContact` / `updateContact` / `deleteContact` | 3257+ | Customer CRUD |
| `getEstimatingProperties` | 4416 | Properties with measurements |
| `getTemplates` / `saveTemplate` / `deleteTemplate` | 691/757/797 | Template CRUD |
| `getServiceCatalog` | 393 | Service templates |
| `getCrews` | 2509 | Crew definitions |

**Tier 3 — Invoicing & Payments:**
| Endpoint | Notes |
|----------|-------|
| `getInvoices` / `getPayments` | Read with filters |
| `generateInvoiceBatch` | Scan contracts, create drafts, auto-charge auto-pay |
| `finalizeInvoice` / `voidInvoice` | Status transitions |
| `recordPayment` | Append payment, update invoice |
| `sendInvoice` | Stripe Checkout + PDF + email |
| `createStripeCheckoutSession` | Stripe payment mode |
| `setupAutoPay` / `checkAutoPaySetup` / `checkStripePayment` | Stripe setup mode + polling |

**Tier 4 — Signing, reports, uploads, remaining:**
| Endpoint | Notes |
|----------|-------|
| `sendContractForSigning` / `recordSignature` / `getContractForSigning` | Token-based e-signature |
| `uploadPhoto` / `inspectionPhoto` / `siteReportPhoto` | Base64 → S3 |
| `siteReportPdf` / `contractPdf` / `uploadSubContractPdf` | PDF → S3 |
| `siteReportJson` / `getSavedReports` / `getReportData` / `getPhotoBase64` | JSON/photo from S3 |
| `getReminders` / `saveReminder` / `updateReminder` | CRUD |
| `getProductionAnalysis` | Complex aggregation query |
| `getWeeklyReportData` / `sendWeeklyReport` | Weekly report + email |
| `getPropertyContacts` / `linkContactToProperty` / `unlinkContactFromProperty` | Junction CRUD |
| `getSubContractors` / `saveSubContractor` / `updateSubContractor` / `deleteSubContractor` | CRUD |
| `getProperties` | Crew-compatible property list |
| `deleteFutureTickets` / `rescheduleTicket` / `reopenTicketService` | Ticket management |
| `submitTicket` / `submitRequest` | Customer + crew request submission |

### CORS
Allow origin: `https://endurancefl.github.io` (and `http://localhost:*` for dev)

---

## Hazards to Watch For

### Bid data model is the hardest migration
The Bids sheet stores a JSON blob with the full estimate structure. In PostgreSQL, that fans out into `bids` + `bid_services` + `bid_line_items` — a one-to-many-to-many relationship. The `import-sheets.ts` script must parse that JSON and correctly distribute it across three tables. And `getInitData` / `getBids` must reassemble it into the **exact same JSON shape** the frontends expect. Test this exhaustively — if estimate.html can't load a migrated bid, it looks like data corruption.

### `getInitData` runs 10+ queries — use `Promise.all`
This endpoint returns 10 datasets in one response. In PostgreSQL, that's 10+ queries (some with JOINs). Run them in parallel with `Promise.all`, not sequentially, or load time will regress badly. The whole point of the bulk endpoint was speed.

### File uploads: watch App Runner request size limits
Current flow: frontend sends base64 to Apps Script → writes to Google Drive. New flow: frontend sends to Express → Express uploads to S3. Site report photos are 1600px at 85% JPEG — these can be large. Check App Runner's max request body size (default 4MB). For larger files, switch to **S3 presigned URLs** so the frontend uploads directly to S3 and just notifies the API of the key.

### Stripe SDK returns different shapes than raw HTTP
Apps Script's Stripe calls use raw `UrlFetchApp.fetch()` with the secret key in headers. The `stripe` npm package returns typed SDK objects, not raw JSON. The response shapes differ slightly. Make sure your route handlers extract the same fields the frontends expect and return them in the same format.

### Email sending replacement
Apps Script uses `MailApp.sendEmail()`. Replace with Amazon SES (already on AWS, $0.10/1K emails) or SendGrid free tier (100 emails/day). SES requires domain verification before sending.

---

## Phase 4: Data Migration

### Google Sheets → PostgreSQL
`scripts/import-sheets.ts`:
1. Read all sheets via Google Sheets API or CSV export
2. Map column names to database columns
3. Insert into Postgres preserving existing IDs (BID-xxx, CTR-xxx, TKT-xxxx, TE-xxxx)

| Sheet | → Table | Notes |
|-------|---------|-------|
| Item Catalog | `production_rates` | |
| Service Catalog | `service_catalog` | |
| Settings | `tenants` (settings columns) | Key-value pairs → tenant columns |
| Bids | `bids` + `bid_services` + `bid_line_items` | **Parse JSON column** — hardest migration |
| Contracts | `contracts` + `contract_services` | Include signing + auto-pay columns |
| Scheduled Tickets | `scheduled_events` | Preserve Services JSON, earnedValue |
| Time Entries | `time_entries` | |
| Crew Members | `crew_members` + `users` | Create user records from crew members |
| Contacts | `customers` | |
| Properties | `properties` | Include all measurements |
| PropertyContacts | `property_contacts` | |
| SubContractors | `sub_contractors` | |
| Requests | `service_requests` | |
| Reminders | `reminders` | |
| Invoices | `invoices` + `invoice_line_items` | |
| Payments | `payments` | |
| Templates | `templates` | Store as JSONB |

### Google Drive → S3
`scripts/import-drive.ts`:
1. List all files in Drive folders (`ESTIMATE_DRIVE_FOLDER_ID`, `TEXT_MY_TEAM_DRIVE_FOLDER_ID`)
2. Download each file
3. Upload to S3: `{tenant_id}/{property_street}/{type}/{filename}`
4. Update database URL references from `drive.google.com` to S3

### Response comparison script
`scripts/compare-responses.ts` — during migration, call the same endpoint on both Apps Script and Express, diff the JSON output, flag discrepancies. Run this against every endpoint before cutover.

---

## Phase 5: Deploy to AWS

### AWS services

| Service | Config | Est. Cost |
|---------|--------|-----------|
| **RDS** PostgreSQL 16 | db.t4g.micro, 20GB gp3, us-east-1 | $0 free tier / ~$15/mo |
| **App Runner** | 0.25 vCPU, 0.5GB RAM, auto-scale 1-5 | ~$5-15/mo |
| **S3** | `endurance-platform-files` bucket | ~$1-5/mo |
| **SES** | Email sending (replaces MailApp) | $0.10/1K emails |
| **Lambda** | PDF generation (already deployed) | Already running |
| **Total** | | **~$20-35/mo** |

### Deploy steps
1. [ ] Create RDS instance in us-east-1 (same region as Lambda)
2. [ ] Create S3 bucket with CORS for `https://endurancefl.github.io`
3. [ ] Push Docker image to ECR
4. [ ] Create App Runner service from ECR image
5. [ ] Set env vars: `DATABASE_URL`, `STRIPE_SECRET_KEY`, `S3_BUCKET`, `AWS_REGION`, `SES_FROM_EMAIL`
6. [ ] Configure VPC connector (App Runner → RDS on port 5432)
7. [ ] Run migrations against RDS
8. [ ] Run data migration scripts (import-sheets + import-drive)
9. [ ] Run compare-responses script against all endpoints
10. [ ] Test all endpoints against deployed API

---

## Phase 6: HubSpot Integration

### OAuth flow
- [ ] `GET /api/hubspot/connect` → redirect to HubSpot OAuth consent screen
- [ ] `GET /api/hubspot/callback` → exchange code for tokens, store on tenant record
- [ ] Token refresh via interceptor

### Contact sync (cron job, every 10-15 min)
- [ ] Poll `GET /crm/v3/objects/contacts` with incremental `after` timestamp
- [ ] Fields: firstname, lastname, email, phone, address, city, state, zip, lifecyclestage
- [ ] Upsert into `customers` table matching on `hubspot_contact_id`
- [ ] Update `last_synced_at` on customer record

### Write-back custom properties (create in HubSpot first)
- [ ] `active_contract_count` (number)
- [ ] `monthly_revenue` (number)
- [ ] `next_service_date` (date)
- [ ] `customer_pin` (string)
- [ ] `property_addresses` (text)

Write-back triggers:
- Contract finalized → update `active_contract_count` + `monthly_revenue`
- Ticket scheduled → update `next_service_date`
- PIN generated → update `customer_pin`

### Timeline events (log to HubSpot)
- [ ] Contract signed → "Contract {id} signed for {address}"
- [ ] Invoice sent → "Invoice {id} sent, ${amount} due {date}"
- [ ] Payment received → "Payment: ${amount} via {method}"
- [ ] Service completed → "Service completed at {address}: {services}"

---

## Phase 7: Cutover (Per-App, Not All-at-Once)

> **Roll out one app at a time.** If something breaks, you only revert one file.

### Rollout order
1. **crew.html first** (highest daily usage, fastest feedback loop) — switch URL, run for 1 week soak
2. **estimate.html second** — switch URL after crew.html is stable
3. **index.html + sign.html last** — lowest traffic, switch together

### The URL change in each file

```javascript
// crew.html line 953:
const GOOGLE_SHEETS_URL = "https://<app-runner-url>.us-east-1.awsapprunner.com";

// estimate.html line 2437:
const GOOGLE_SHEETS_URL = 'https://<app-runner-url>.us-east-1.awsapprunner.com';

// index.html line 1645:
const GOOGLE_SHEETS_URL = "https://<app-runner-url>.us-east-1.awsapprunner.com";

// sign.html line 455:
const GOOGLE_SHEETS_URL = 'https://<app-runner-url>.us-east-1.awsapprunner.com';
```

Single-line change per file. Commit. Push to GitHub Pages.

### Safe rollback: dual-write during soak week

> **The problem:** Once crew.html starts writing to PostgreSQL (new time entries, completed jobs, status updates), the Google Sheets data goes stale. If you revert the URL back to Apps Script, the crew loses everything they entered since the switch. That's a data reconciliation nightmare.

> **The solution:** During the crew.html soak week, have the new API dual-write — it writes to PostgreSQL (primary) and then fires a background POST to the old Apps Script URL to keep Sheets in sync. This way, reverting is safe because Sheets has all the data.

- [ ] Add a `dual-write.service.ts` that, after each successful PostgreSQL write, asynchronously POSTs the same data to the old Apps Script URL (fire-and-forget, don't block the response)
- [ ] Enable dual-write for crew-critical write endpoints: `saveTimeEntry`, `updateTimeEntry`, `deleteTimeEntry`, `completeJob`, `updateTicketStatus`, `bulkSkipDay`, `updateStatus`, `updateAcknowledged`
- [ ] If the Sheets write fails, log the error but don't affect the user — PostgreSQL is the source of truth
- [ ] After the soak week passes without issues, disable dual-write (delete the service or flip an env var)
- [ ] **Minimum alternative** if dual-write feels like too much work: run a nightly `scripts/sync-pg-to-sheets.ts` script that exports the day's new PostgreSQL records back to Google Sheets. Less safe (you lose up to a day of data on revert) but simpler to build

### Post-cutover
- [ ] Set up CloudWatch alarms (errors, latency, 5xx rate)
- [ ] Monitor RDS via Performance Insights
- [ ] To revert crew.html during soak: change URL back to Apps Script, push to GitHub Pages (safe because Sheets is in sync via dual-write)
- [ ] After all apps are stable for 2+ weeks, disable dual-write and decommission Apps Script

---

## What Does NOT Change

- All HTML frontends (crew.html, estimate.html, index.html, sign.html, payment-success.html)
- Lambda PDF generation (stays on AWS Lambda as-is)
- GitHub Pages hosting for frontends
- All business logic (calculation engine, scheduling, billing) — ported, not rewritten
- Stripe integration logic — ported from UrlFetchApp to `stripe` npm package

---

## Future: React Migration (After Backend Is Stable)

Once the Node backend is running, the `api/src/types/` directory extracts into `packages/shared` for a Turborepo monorepo. React frontends (platform app, crew app, customer portal) replace the HTML files one at a time. The backend doesn't change — React apps use the same API.

**Division catalogs (IRR/CON/ENH)** can be built in parallel on the current estimate.html prototype while the backend migration is underway — these are independent workstreams.

---

## Key Reference Files

| File | What to reference |
|------|-------------------|
| `backend/combined-apps-script.js` | Authoritative source for all 78 endpoints' request/response contracts |
| `docs/platform-architecture.md` lines 742-1141 | Complete PostgreSQL schema (21 tables) |
| `docs/platform-architecture.md` lines 343-441 | Endpoint catalog |
| `crew.html` line 953 + all `fetch()` calls | How crew app calls the API |
| `estimate.html` line 2437 + all `fetch()` calls | How estimate app calls the API |
| `index.html` line 1645 | Customer portal API calls |
| `sign.html` line 455 | Signing page API calls |

---

## Verification Checklist (After Each Phase)

- [ ] crew.html: login → load schedule → start job → clock time → complete job → end day
- [ ] estimate.html: load bids → create/edit bid → finalize → generate contract → send for signing
- [ ] index.html: enter PIN → submit request → upload photo
- [ ] sign.html: open token link → view contract → sign → auto-pay setup → Stripe redirect
- [ ] Run `compare-responses.ts` against all endpoints — diff must be empty
- [ ] Calculation engine tests pass — bid totals match estimate.html penny-for-penny
- [ ] All file uploads (photos, PDFs, reports) stored in S3 and retrievable
- [ ] Stripe payments still work (checkout, auto-pay setup, payment polling)
- [ ] Email sending works (contract signing, invoice, weekly reports)
