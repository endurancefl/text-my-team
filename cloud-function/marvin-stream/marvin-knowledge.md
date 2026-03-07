# MARVIN Knowledge Base — Platform & Industry Reference

This file is loaded by the Lambda at runtime and injected into MARVIN's system prompt.
Update this file whenever the codebase changes, then redeploy with `deploy-docker.sh`.

---

## Platform Overview

Endurance Services is a commercial and residential landscape maintenance company in Central Florida.
The platform has three apps:

1. **Estimate Builder** (`estimate.html`) — Build estimates, manage contracts, invoicing, scheduling
2. **Crew Leader App** (`crew.html`) — Mobile app for daily crew operations, time tracking, reporting
3. **Customer Portal** (`index.html`) — Customers submit service requests and check status

All three connect to a Google Apps Script backend with Google Sheets as the database.
PDF generation and AI features run on AWS Lambda.

---

## Estimate Builder — Views & Navigation

### Operations
| View ID | Name | Purpose |
|---------|------|---------|
| `estimates` | Estimates | Default view. Grid of all saved estimates (Draft, Revision, Finalized) |
| `builder` | Active Estimate | The estimate editor — shows when editing an estimate |
| `contacts` | Contacts | CRM: manage contacts with stages (Lead, Prospect, Customer) |
| `contracts` | Contracts | Active service contracts with schedule and signing status |
| `properties` | Properties | Property entities with measurements, contacts, sub-contractors |
| `schedule` | Schedule | Calendar for contract-based tickets, filterable by crew and division. Shows hours badges per day — green when under Daily Crew Capacity, red when over. |

### Financials
| View ID | Name | Purpose |
|---------|------|---------|
| `invoices` | Invoices | Invoice lifecycle: draft → sent → overdue → paid. Summary cards, batch generation, Record Payment, Stripe auto-pay. |
| `financials` | Financials | Revenue dashboard: Collected vs Earned vs Deferred, monthly bar chart, active contracts table. |

### Configuration
| View ID | Name | Purpose |
|---------|------|---------|
| `catalog` | Item Catalog | Labor and material items with production rates by difficulty |
| `services` | Service Catalog | Pre-configured services with default items, visits, billing tiers |
| `production` | Production Rates | Actual vs estimated production analysis by crew, date range, service, and item. |
| `worktickets` | Reminders | Crew reminders — Active, Permanent, Completed filters. Assign to crew with date. |
| `reports` | Reports | Weekly property reports: visits per property, email to customers, bulk send. |
| `templates` | Templates | Save/load/duplicate estimate templates. Template picker appears when starting a new estimate. |
| `settings` | Settings | Company rates, markups, travel %, Daily Crew Capacity, MARVIN Knowledge Base. |

---

## Item Catalog — Production Rates

All items have production rates at three difficulty levels (Easy / Medium / Hard).
Production rates represent units processed per hour by one person.

### Labor Items

| Item | Unit | Easy | Medium | Hard | Category |
|------|------|------|--------|------|----------|
| Backpack Blowing | SF/Hour | 60,000 | 45,000 | 35,000 | Blowing |
| 21" Mower Walk | SF/Hour | 10,000 | 8,000 | 5,000 | Mowing |
| 30" Mower Walk | SF/Hour | 15,000 | 12,000 | 7,500 | Mowing |
| 32" Mower Ride | SF/Hour | 25,000 | 18,750 | 12,500 | Mowing |
| 48" Mower Ride | SF/Hour | 40,000 | 30,000 | 20,000 | Mowing |
| 60" Mower Ride | SF/Hour | 52,000 | 42,000 | 32,000 | Mowing |
| 72" Mower Ride | SF/Hour | 65,000 | 55,000 | 45,000 | Mowing |
| Blade Edge | LF/Hour | 4,000 | 3,500 | 3,000 | Mowing |
| String Trimmer | LF/Hour | 3,500 | 3,000 | 2,500 | Mowing |
| Trash Pickup | SF/Hour | 60,000 | 45,000 | 35,000 | General |
| Hedge Trimming | SF/Hour | 1,500 | 1,000 | 500 | Pruning |
| Perennial Care | SF/Hour | 500 | 350 | 200 | Pruning |
| Leaf Cleanup | SF/Hour | 28,000 | 20,000 | 14,000 | Leaf Cleanup |
| Leaf Bagging & Hauling | Bags/Hour | 10 | 10 | 10 | Leaf Cleanup |
| Weed Control Liquid | SF/Hour | 20,000 | 15,000 | 10,000 | General |
| Weed Control Hand | SF/Hour | 10,000 | 7,500 | 5,000 | General |
| Irrigation Inspection | Zones/Hour | 12 | 8 | 4 | Irrigation |

### Material Items

| Item | Unit | Easy | Medium | Hard | Category | Cost/Unit | Coverage/Unit | Default Depth |
|------|------|------|--------|------|----------|-----------|---------------|---------------|
| Mulch Spreading Hand | SF/Hour | 500 | 350 | 200 | Mulch | $45/CY | 162 SF | 2" |
| Mulch Spreading Machine | SF/Hour | 1,500 | 1,000 | 600 | Mulch | $45/CY | 162 SF | 2" |
| Pine Straw Application | SF/Hour | 800 | 600 | 400 | Pine Straw | $8/Bale | 50 SF | 3" |
| Spring Seasonal Color | SF/Hour | 200 | 150 | 100 | Seasonal Color | $25/Flat | 12 SF | — |
| Fall Seasonal Color | SF/Hour | 200 | 150 | 100 | Seasonal Color | $25/Flat | 12 SF | — |
| Pre-Emergent Granular | SF/Hour | 2,000 | 1,500 | 1,000 | Pre-Emergent | $35/Bag | 5,000 SF | — |

The catalog is customizable — users can add/edit/delete items via the Item Catalog view.

---

## Service Catalog — Default Services

### Routine Maintenance
| Service | Default Visits | Billing Tier | Items |
|---------|---------------|-------------|-------|
| Weekly Grounds Maintenance | 42 | Fixed | Weed Control, Trash Pickup, Blowing + mowers/edge from takeoffs |
| Shrub Pruning Service | 24 | Fixed | Hedge Trimming |
| Perennial Care | 1 | Fixed | Manual entry |
| Leaf Removal Service | 4 | Fixed | Blowing, Trash Pickup |

### Mulch & Pre-Emergent
| Service | Default Visits | Billing Tier |
|---------|---------------|-------------|
| Pine Straw Application | 1 | Fixed |
| Spring Pre-Emergent Application | 1 | Fixed |

### Seasonal Color
| Service | Default Visits | Billing Tier |
|---------|---------------|-------------|
| Spring Seasonal Color Application | 1 | Fixed |
| Fall Seasonal Color Application | 1 | Fixed |

### Irrigation
| Service | Default Visits | Billing Tier |
|---------|---------------|-------------|
| Irrigation Spring Startup | 1 | Billed Separately |
| Irrigation Winterization | 1 | Billed Separately |

### Turf Applications (all Recommended tier)
| Service | Default Visits |
|---------|---------------|
| Turf Application Round 1 — Late Winter | 1 |
| Turf Application Round 2 — Early Spring | 1 |
| Turf Application Round 3 — Summer | 1 |
| Fall Aeration & Overseeding | 1 |
| Turf Application Round 5 — Early Winter | 1 |

---

## Calculation Formulas

### Labor Hours
```
hoursPerVisit = quantity / productionRate * complexityFactor
annualHours = sum over difficulties: (quantity[diff] / rate[diff]) * complexityFactor * occurrences[diff]
totalHoursWithTravel = annualHours + (annualHours * travelPercent / 100)
```

### Labor Cost & Billing
```
laborCost = totalHoursWithTravel * laborRate
laborBilled = laborCost * (1 + laborMarkup / 100)
billedRatePerHour = laborRate * (1 + laborMarkup / 100)
```
With default 151.72% markup: $22.50 * 2.5172 = ~$56.64/hr billed rate.

### Material Cost
```
effectiveCoverage = coveragePerUnit * (defaultDepth / actualDepth)  [depth-based items]
unitsNeeded = totalSF_annual / effectiveCoverage
materialCost = unitsNeeded * costPerUnit
materialBilled = materialCost * (1 + materialMarkup / 100)
```
Example: Mulch at 3" instead of default 2": coverage = 162 * (2/3) = 108 SF/CY.

### Subcontractor Billing
```
subBilled = subCost * (1 + subMarkup / 100)
```
Each service can override the global sub markup.

### Bid Totals
```
bidTotal = laborBilled + materialBilled + subBilled
internalCost = laborCost + materialCost + subCost
profit = bidTotal - internalCost
margin = (profit / bidTotal) * 100
monthlyPrice = bidTotal / paymentMonths
perVisitPrice = bidTotal / totalVisits
```

### Monthly Payment with CC Gross-Up
```
If ccGrossUp enabled:
  effectiveAnnual = fixedAnnual / (1 - ccFeePercent / 100)
  monthlyPayment = effectiveAnnual / paymentMonths
```

---

## Billing Tiers

| Tier | Key | Behavior |
|------|-----|----------|
| **Fixed Payment** | `fixed` | Included in monthly contract price, divided into equal payments |
| **Billed Separately** | `billed` | Invoiced separately when work is performed, NOT in monthly payment |
| **Recommended/Optional** | `recommended` | Customer can accept or decline. If accepted, included in totals; if not, shown as pending |

---

## Takeoff Sections — Measurement System

Takeoffs connect property measurements to estimate line items.

### Default MNT Sections

1. **Lawn Equipment** (split) — Lawn SF split by mower type percentages (e.g., 70% 48" Ride, 20% 21" Walk, 10% String Trimmer)
2. **Edge** (value) — Total edge LF (hard edge + soft edge)
3. **Hedge Trimming** (split) — Hedge SF split by height: <4ft (Easy), 4-6ft (Medium), 6ft+ (Hard)
4. **Mulch Bed** (value) — Total bed area, % mulched, depth in inches
5. **Weed Control** (split) — Treatable bed SF split between Liquid and Hand methods
6. **Perennial** (value) — % of beds with perennials
7. **Seasonal Color** (calc) — Total flowers ÷ flowers per flat (18) = total flats
8. **Leaf Cleanup** (calc) — Canopy coverage of turf + hardscape → total leaf SF → bags (8,400 SF/bag)
9. **Mulch Sub** (value) — Mulch area, coverage per CY, cost per CY → total CY and cost

### Section Types
- **split**: Divides a parent measurement into sub-rows by percentage. Rows must sum to 100%.
- **value**: Single quantity input, sometimes derived from a parent feature.
- **calc**: Multi-step calculation producing derived values (input → constant → output).

### Measurement Flow
1. Upload Attentive report or enter features manually (Lawn SF, Mulch Bed SF, Hedge SF, etc.)
2. Each feature has difficulty split (Easy/Medium/Hard, must sum to 100%)
3. Takeoff sections use features as parent measurements and apply formulas
4. `buildServicesFromTakeoffs()` injects calculated line items into target services
5. Estimate table recalculates totals

### Property Features
Lawn, Mulch Bed, Gravel Bed, Hedge, Hardscape (auto = Driveway + Pavement + Sidewalk + Drive Lanes + Parking), Total Edge, Tree Count, Irrigation Zones

---

## Bid Settings — Defaults

| Setting | Default | Description |
|---------|---------|-------------|
| Labor Rate | $22.50/hr | Base hourly cost per person |
| Residential Labor Markup | 151.72% | Markup on labor for residential |
| Residential Material Markup | 100% | Doubles material cost for residential |
| Residential Sub Markup | 10% | Subcontractor markup for residential |
| Commercial Labor Markup | 151.72% | Markup on labor for commercial |
| Commercial Material Markup | 100% | Doubles material cost for commercial |
| Commercial Sub Markup | 10% | Subcontractor markup for commercial |
| Default Travel Time | 30% | Added to labor hours |
| Daily Crew Capacity | 33 man-hours | Max crew workload per day. Schedule hours badges turn red when a day exceeds this. Editable in Settings → Daily Crew Capacity (Man-Hours). |
| Division | Maintenance | Currently only MNT is fully built |

Estimate-level overrides take precedence over bid settings. Property type (Residential/Commercial) determines which markup set is used.

---

## Schedule View

The Schedule view shows a calendar of all tickets generated from active contracts. Three modes:

- **Month view**: Calendar grid with hours badges per day. Color-coded against **Daily Crew Capacity** (default 33 man-hours, editable in Settings → Daily Crew Capacity). Green = under capacity, red = over capacity. Helps spot overloaded days at a glance.
- **Week view**: 7-day grid showing ticket cards per day. Hours badges per day, same capacity color coding. Supports drag-and-drop to reschedule tickets to different days.
- **Day view**: Detailed stop list for a single day per crew. Drag-to-reorder stops within the same crew.
- **Filtering**: Filter by crew assignment and/or division (MNT, IRR, CON, ENH).
- **Needs Reschedule queue**: Button with badge count shows skipped tickets that need new dates. Can reschedule individual tickets from the queue.
- **Ticket cards**: Each shows property address, services, estimated hours, assigned crew, and status.

The Daily Crew Capacity setting is found in **Settings → Daily Crew Capacity (Man-Hours)** and represents the total man-hours your crew can handle in a single day.

---

## Financials View

Revenue dashboard showing the health of all active contracts:

- **Summary cards**: Collected To Date (green), Earned To Date (blue), Deferred Revenue or "Ahead of Schedule" (orange or green). Deferred means you've collected more than you've earned — Ahead of Schedule means you've earned more than collected.
- **Monthly Revenue Chart**: Bar chart comparing Earned vs Collected per month. Paginate through months with Older/Newer buttons.
- **Active Contracts Table**: Lists all active contracts with their collected and earned totals.

Revenue is calculated from completed tickets (earned) vs recorded invoice payments (collected). This view helps the user understand cash flow and whether work is keeping pace with billing.

---

## Invoices View

Full invoice lifecycle management:

- **Summary cards**: Outstanding balance, Overdue amount, Collected this month, Draft count.
- **Status filters**: All, Draft, Sent, Overdue, Paid.
- **Invoice statuses**: `draft` (not finalized) → `sent` (delivered to customer) → `overdue` (past due date) → `paid` (fully paid). Also `partial` (partially paid).
- **Generate Invoices**: Batch-generates monthly invoices for all active contracts with deduplication (won't create duplicates for already-invoiced months).
- **Invoice detail**: Shows contract info, line items, payment history. Actions: Finalize (locks draft), Send (emails to customer), Void (cancels), Record Payment (amount, method: check/cash/card/ACH, date, notes).
- **Auto-pay (Stripe)**: Contracts can be set up for automatic payment via credit card (2.9% surcharge) or ACH. Configured from the contract detail view.

---

## Properties View

Property profiles with all linked data:

- **Property list**: Searchable grid of all properties. Filter by contract status.
- **Property profile** (click a property): Shows full details with sub-panels:
  - **Linked Contacts**: People associated with this property, with roles.
  - **Active Contract**: Current contract info if one exists.
  - **Bids/Estimates**: All draft or past estimates for this property.
  - **Projects**: One-off work (Enhancement, Construction, Irrigation jobs).
  - **Service History**: Timeline of completed work at this property.
  - **Sub-Contractors**: Third-party vendors linked to this property.
- **Create Estimate**: Can start a new estimate directly from a property profile, pre-filling the property info.

---

## Contacts View (CRM)

Contact management with sales pipeline stages:

- **Stages**: Lead → Prospect → Customer. Contacts auto-upgrade to "Customer" when a contract is signed and finalized.
- **Contact list**: Searchable, filterable by stage. Shows initials avatar, name, company.
- **Contact profile** (click a contact): Shows linked properties, associated estimates/contracts, and a "Start Estimate" action to begin a new bid for that contact.
- **Stage workflow**: Manually change stages via dropdown in profile, or they auto-upgrade on contract finalization.

---

## Contracts View

Shows only **signed** contracts (the signing workflow happens in Estimates):

- **Contract list**: Cards with property address, dates, assigned crew, status badge. Shows "Needs Schedule" indicator for signed contracts that don't have tickets generated yet.
- **Contract detail** (click a contract):
  - Summary panel: address, status, signing info (who signed, when, IP).
  - Actions: View Tickets, View PDF, View Signed PDF, Generate Schedule, Terminate Contract.
  - **Generate Schedule**: Two-phase process — first Preview (shows proposed tickets), then Finalize (creates actual tickets). Can cancel preview.
  - **Tickets sub-view**: Service list view or Calendar view (drag-and-drop scheduling).
- **Contract statuses**: `active` (running), `signed` (pre-schedule), `terminated` (ended early).
- **Signing statuses**: `unsent` → `sent` → `viewed` → `signed`. Also `revised` (contract changed, needs re-signing).
- **Auto-pay setup**: Can set up Stripe auto-pay (card or ACH) from the contract detail.

---

## Reports View

Weekly property reports for emailing to customers:

- **Week selector**: Navigate between weeks with Prev/Next buttons.
- **Summary**: Properties Serviced count, Total Visits count, Ready to Send count.
- **Report cards**: One per property serviced that week. Shows customer name/email, list of visits with dates and services performed.
- **Email Report**: Send individual report to customer (requires email on file — shows "No Email" if missing).
- **Send All Reports**: Bulk-send all reports for the selected week.

---

## Reminders View (Work Tickets)

Crew reminders and standing instructions, separate from recurring service tickets:

- **Filters**: Active (default), Permanent (recurring/standing reminders), Completed, All.
- **Search**: Filter reminders by text.
- **Create Reminder**: Modal with property selector, description, scheduled date, assign to crew.
- **Permanent reminders**: Standing instructions that persist (e.g., "Gate code changed to 1234" or "Dog in backyard — use side gate").

---

## Templates View

Save and reuse estimate configurations:

- **Template list**: Grid of saved templates with Edit, Duplicate, Delete actions.
- **Save as Template**: Save the current estimate's services and configuration as a reusable template (name + description).
- **Template picker**: When starting a new estimate, a template picker modal appears letting the user choose a saved template to pre-fill services and line items.
- **Duplicate**: Clone a template to create variations.

---

## Production Analysis View

Compare actual crew performance against estimates:

- **Date range picker**: Select a date range to analyze.
- **Crew filter**: Filter by specific crew or all crews.
- **Services tab**: Shows each service with estimated vs actual man-hours, highlighting over/under performance.
- **Item Rates tab**: Shows actual production rates vs catalog rates for individual items (e.g., actual mowing SF/hour vs the catalog rate).
- Helps identify where estimates are too generous or too tight, and which crews are most efficient.

---

## Estimate Builder Details

### Job Type Picker
When starting a new estimate, user chooses:
- **Recurring Contract**: Standard monthly maintenance with scheduled visits. Services can use any billing tier.
- **Work Ticket**: One-off or multi-day project. All services forced to fixed billing, visits = 1. Optional deposit (default 25%).

### Contract Settings Card
- **Recurring**: Start/End dates, Duration (months), Payment months, Price increase %, Payment terms (Net 30), CC fee.
- **Work Ticket**: Project name, Schedule type (Single/Multi-day), Start/End dates, Deposit enabled + percentage.
- **Rate Overrides**: Labor rate, Labor/Material/Sub markup percentages, Travel %. These override the global settings for this estimate only.

### Summary Panel
Shows calculated totals for the current estimate:
- Annual total, Monthly payment, Per-visit price
- Internal cost, Profit, Margin %
- Labor hours breakdown (work hours + travel hours)
- **Finalize button**: Locks the estimate, creates the contract, generates PDF for signing.

---

## Contract & Proposal System

### Estimate Statuses
- **Draft** — Being built, can save and edit freely
- **Revision** — Finalized estimate being modified, preserves completed tickets
- **Finalized** — Locked with active contract, generates tickets and PDF

### Contract Defaults
- Duration: 12 months
- Payment months: 12
- Payment terms: Net 30
- CC Fee: 0% (configurable)
- Price increase on renewal: 0% (configurable)
- Auto-renews unless 60 days written notice

### Ticket Scheduling Rules
- **42 visits (seasonal anchor):** Weekly Apr–Oct, biweekly Nov–Mar
- **50-54 visits:** Weekly all year
- **Other counts:** Evenly distributed across contract, snapped to preferred day
- Tickets bundled by date — all services due same day go into one ticket

### Job Types
- **Recurring Contract** — Standard monthly maintenance contract with scheduled visits
- **Work Ticket** — One-off or multi-day project. All services forced to fixed billing, visits = 1. Optional deposit (default 25%).

### E-Signature Flow
1. Generate contract PDF → upload to Drive
2. Send signing email with UUID token link to `sign.html`
3. Customer reviews and signs with typed name
4. Generate signed PDF with signature, timestamp, SHA-256 hash of original

---

## Crew Operations (crew.html)

### Daily Workflow
1. **Login** — Crew leader enters phone number
2. **Check In** — Each member verifies 4-digit PIN
3. **Start Day** — Day clock starts, travel auto-starts, GPS captured
4. **Work Tickets** — Navigate stops in order, start/complete services, track time
5. **End Day** — Close all tickets, day summary modal

### Ticket Statuses
| Status | Meaning |
|--------|---------|
| `scheduled` | Not yet started |
| `partial` | Some work done, will return later |
| `completed` | All services finished |
| `skipped` | Manually skipped (flagged for reschedule) |

### Time Tracking
- **Entry types:** `day_clock`, `job` (per ticket), `service` (per service), `indirect` (travel, shop)
- **Scalable services:** Man-hours = elapsed minutes × crew count. Adding crew speeds up the work.
- **Fixed services:** Wall-clock time only. Adding crew does NOT change duration (e.g., irrigation inspection).
- **Time splitting:** When crew changes mid-service, old entry closes and new entry opens with accumulated hours carried forward.

### Crew Management
- Members check in with 4-digit PINs
- Mid-day add/remove supported
- Removing a member splits all active time entries
- Members can be assigned to specific services within a ticket
- Reassignment wizard shows "Where to next?" with time projections

### Progress Tracking
- Progress bars update every second per active ticket
- Visual states: blue (<75%), yellow (75-99%), red (100%+)
- Remaining time format: "0:22 left" or "0:12 over"
- Alert fires when elapsed time exceeds estimate

### Reports
- **Site Report** — 4-step wizard: select property → take/upload photos → annotate with categories → generate PDF
  - Categories: Drainage/Erosion, Hardscape, Irrigation, Misc, Priority Areas, Shrub Health, Tree Health
- **Before & After** — Compare current photos with a prior site report
- **Quick Photos** — Bulk upload inspection photos to Drive

### Customer Requests
- Appear as orange warnings in the schedule at the matching property
- Crew can reply (SMS), send to office, or mark complete with photo
- Types: Customer (from portal) or Internal (from crew "Report Issue")

### Business Rules
- **Sequential property enforcement:** Can't start a ticket at a new property while tickets are active at another
- **Skip guards:** Can't skip active tickets, only scheduled/partial
- **End day guards:** Must close all active non-Shop tickets before ending day
- **Travel auto-management:** Starts when no tickets active, stops when a ticket starts

---

## Customer Portal (index.html)

### Authentication
- Customers enter a 4-digit PIN that matches their property record
- If multiple properties share a PIN, customer chooses which one
- Name and phone saved in localStorage for return visits

### Request Submission (3-step wizard)
1. **Photo** — Take or upload photo, optional annotation (draw red rectangles)
2. **Details** — Name, phone, issue description (max 500 chars)
3. **Review & Send** — Confirm and submit

### Features
- Bilingual (English/Spanish)
- Offline support — queues requests when offline, auto-sends when reconnected
- Photo compression and background upload
- Auto-translation between English and Spanish on all messages

---

## Backend — Google Sheets Database

### Sheet Schemas

**Properties:** propertyId, address, city, state, zip, propertyType, pin, crew, crewPhone, lotSizeSF, measurements (lawn, edge, mulch bed, hedge, hardscape, trees, zones), difficultyJson, gateCode, notes

**Bids:** bidId, date, propertyAddress, division, type, lotSizeSF, laborRate, markups, travel%, totals (labor hours, costs, bid total, profit, margin%), status, estimateFileID, contractId, revisionCount, jobType, scheduleType

**Contracts:** contractId, bidId, propertyAddress, crew, preferredDay, dates, months, monthlyPayment, status, paymentTerms, contractValue, ccFee%, contact info, PDF info, signing fields (token, status, signedName, timestamp, IP, hash), auto-pay fields (Stripe)

**Scheduled Tickets:** ticketId, contractId, property, crew, eventDate, servicesJSON, estHours, travelHours, earnedValue, internalCost, status, completedDate, stopOrder, needsReschedule, completedServicesJSON, jobType

**Time Entries:** entryId, crew, date, entryType, ticketId, property, indirectCategory, clockIn/Out, durationMinutes, crewMembersJSON, notes, GPS (lat/lng in/out), serviceName, memberCount, durationType, reopened, estimatedHours

**Crew Members:** name, phone, role, crew, status, pin

**Contacts:** contactId, name, email, phone, company, billingAddress, propertyAddress, stage, source, notes

**Invoices:** invoiceId, contractId, property, contact, dates, invoiceType, status, amounts (subtotal, tax, total, paid, balance), paymentTerms, Stripe fields, PDF info, lineItemsJson

**Reminders:** reminderId, property, description, scheduledDate, isPermanent, status, createdBy, assignedCrew, photoUrl

### Key Business Logic in Backend
- **Auto-translation:** Every customer request auto-translated English↔Spanish
- **Partial ticket carryover:** Partial tickets from any date appear in current schedule
- **Production analysis:** Compares estimated vs actual man-hours at service and item level
- **Invoice batch generation:** Monthly invoices for all active contracts with deduplication
- **Auto-pay with Stripe:** Card (2.9% surcharge) and ACH support
- **Drive folder structure:** Files organized by property → Photos, Site Reports, Contracts, Estimates

---

## Industry Knowledge — Central Florida Landscape

### Typical Property Sizes
- Residential: 5,000–40,000 SF lots
- Commercial: 40,000–500,000+ SF

### Travel Time Guidelines
- Dense routes (properties close together): 15-20%
- Spread-out residential: 25-35%
- Large commercial (less travel): 10-15%

### Common Contract Structures
- Residential maintenance: 12 months, 42 visits/year
- Standard payment terms: Net 30
- Typical CC fee: 2.9%

### Pricing Benchmarks
- Standard labor rate: ~$22.50/hr
- Residential labor markup: ~150% (billed rate ~$56/hr)
- Material markup: ~100% (doubles cost)
- Sub markup: 10%

### Material Costs
- Mulch: ~$45/CY, covers 162 SF at 2" depth
- Pine Straw: ~$8/bale, covers 50 SF at 3"
- Seasonal Color Flats: ~$25/flat, covers 12 SF
- Pre-Emergent: ~$35/bag, covers 5,000 SF

### Named Tropical Event Policy
Storm cleanup billed at $65/hour Time and Materials, in addition to monthly contract price.

### Divisions
| Code | Name | Description |
|------|------|-------------|
| MNT | Maintenance | Recurring landscape maintenance — mowing, edging, pruning, etc. (fully built) |
| ENH | Enhancement | Large mulch jobs, seasonal color installs, planting projects, renovations (fully built) |
| IRR | Irrigation | Irrigation system maintenance and repair (planned) |
| CON | Construction | Hardscape, drainage, sod installations (planned) |

### ENH Division — Enhancement Estimates

ENH estimates are project-based work tickets (not recurring contracts). When `division === 'ENH'`:
- Job type is auto-set to `work_ticket` with `scheduleType: 'single_visit'`
- All services use `billingTier: 'fixed'` and `visits: 1`
- Three schedule types available: **Single Visit**, **Multi-Day**, **Milestone** (non-consecutive dates with per-phase line item assignment)

#### ENH Item Catalog (Labor)

| Category | Items |
|----------|-------|
| Mulch | Mulch Installation (yards/hr), Mulch Bed Edging/Re-cutting (LF/hr), Bed Cleanup/Debris Removal (SF/hr) |
| Color & Annuals | Annual Color Install 4" pot, Annual Color Install 1 gal, Annual Color Removal/Swap, Perennial Install |
| Planting | Shrub Install (1/3/5/7/15 gal), Ornamental Grass Install, Ground Cover Install, Tree Install (15/25 gal), Tree Staking |
| Renovation | Sod Installation, Soil Amendment/Till, Landscape Fabric Install, Rock/Stone Mulch Install, Plant Removal (Shrub/Tree), Grade & Shape Bed |

#### ENH Service Catalog

| Service | Default Items |
|---------|--------------|
| Mulch Installation | Mulch Installation, Bed Edging, Bed Cleanup |
| Seasonal Color Install | Annual Color Install (4" and 1 gal), Color Removal/Swap |
| Planting / Bed Install | Shrub Install (all sizes), Ground Cover, Perennial Install |
| Landscape Renovation | Plant Removal, Grade & Shape, Soil Amendment, Sod, Landscape Fabric |

#### ENH Materials & Subcontractors

ENH services have **per-line material rows** and **per-line subcontractor rows** — distinct from MNT's aggregate material cost model:

**Material rows**: `{ description, quantity, unit, unitCost, markup (default 20%), billedPrice }` — optionally linked to Plant Catalog entries via `plantCatalogId`

**Subcontractor rows**: `{ description, cost, markup (default 15%), billedPrice }` — these are line items *within* a labor service, different from MNT's whole-service `isSubcontractor: true` model

**ENH Bid Total** = Labor Billed + Materials Billed (sum of all material row billedPrices) + Subcontractor Billed (sum of all sub row billedPrices)

#### ENH Takeoff Sections

| Section | Inputs | Auto-calculation |
|---------|--------|-----------------|
| Mulch | Bed area (SF), depth (inches), edging (LF) | `cubicYards = (SF × depth) / 324` |
| Color | 4" pots count, 1 gal count, removals count | Direct quantity mapping |
| Planting | Count per plant size (1/3/5/7/15 gal, grass, ground cover SF, perennial, tree 15/25 gal, staking) | Direct quantity mapping |
| Renovation | Sod SF, bed area SF, shrub removals, tree removals | Direct quantity mapping |

#### Plant Catalog

Standalone database of plants used across ENH estimates:
- Fields: commonName, botanicalName, category, sizes (JSON with size/supplierCost/defaultMarkup/supplier/sku), photoFileId, notes
- Photos stored in Google Drive (file IDs, not base64)
- When a plant is linked to a material row, auto-fills description, unitCost, and markup from catalog
- CSV import stub available (full pipeline planned for follow-up)

#### Milestone Scheduling (ENH only)

When `scheduleType === 'milestone'`, ENH estimates can define non-consecutive phases:
- Each phase has: label, date, and assigned line items (labor, material, sub rows)
- Each phase generates its own ticket
- Earned value splits proportionally across phases by assigned budgeted hours
- Use for projects like "Day 1: Demo & Grading, Day 3: Planting, Day 5: Mulch"

---

## Live Data Tools

MARVIN has 7 custom tools that fetch data directly from the Google Sheets backend, bypassing the need for data to be pre-loaded in the browser:

| Tool | What It Fetches | When to Use |
|------|----------------|-------------|
| `get_schedule` | Schedule tickets (filterable by date range, crew, contract) | "What's on the schedule next week?" — works even if Schedule view wasn't visited |
| `get_contracts` | All contracts with details | "How many active contracts?" — works even if Contracts view wasn't visited |
| `get_invoices` | Invoices (filterable by status, contract) | "What invoices are overdue?" |
| `get_production_data` | Estimated vs actual man-hours analysis | "How efficient was Crew A last month?" |
| `get_properties` | All properties with measurements and contacts | "Which properties need contracts?" |
| `get_contacts` | CRM contact list | "Who's the contact for [address]?" |
| `get_reminders` | All reminders | "Any reminders this week?" |

**Priority:** Use Platform Data context first (faster). Use tools when data is missing from context or when a different date range / filter is needed. Tools add a few seconds to response time.

---

## FILE IMPORT CAPABILITIES

When the user attaches a spreadsheet, you receive ONLY the column headers in `context.attachedFile.headers` — **no row data is sent**. The client has all the data locally and builds previews from it. Your job:

1. Identify what kind of data the headers suggest (plant catalog, contacts, etc.)
2. Suggest the best import target
3. Map source column headers to target fields by name similarity
4. Return an `importData` action with mappings (NO preview field)

**CRITICAL: Since you do not see any actual data rows, NEVER list, guess, or mention specific data values (plant names, contact names, prices, etc.) in your response. Only describe the file structure: number of columns, row count, and what import target the headers match.**

### Available Import Targets

| Target | Required Field | Other Fields |
|--------|---------------|--------------|
| `plantCatalog` | `commonName` | botanicalName, category (Shrub/Tree/Annual/Perennial/Ornamental Grass/Ground Cover), size, unitCost, supplier, notes |
| `contacts` | firstName or lastName or name | displayName, email, phone, company, billingAddress, propertyAddress, stage (Lead/Prospect/Customer), source, notes |
| `itemCatalog` | `item` | type (Labor/Material), unit (SF/Hour, LF/Hour, etc.), category, division (MNT/ENH), easy, medium, hard, purchaseUnit, costPerUnit, coveragePerUnit, defaultDepth |
| `serviceCatalog` | `serviceName` | defaultVisits, billingTier (fixed/billed/recommended), category, mapColor, description, durationType (scalable/fixed) |
| `properties` | `address` | city, state, zip, propertyType (Residential/Commercial), pin, gateCode, crew, crewPhone, lotSizeSF, lawnRawSF, hardEdgeLF, softEdgeLF, mulchBedSF, hedgeSF, drivewayPavementSF, treeCount, irrigationZones, notes |

### importData Action Format

```json
{
  "type": "importData",
  "data": {
    "target": "plantCatalog",
    "targetLabel": "Plant Catalog",
    "mappings": { "Source Column": "targetField" },
    "unmappedColumns": ["Col1", "Col2"],
    "rowCount": 47
  }
}
```

**DO NOT include a "preview" field.** The client builds the preview table from the local file data.

### PDF Handling

For PDFs (`context.attachedFile.type === 'pdf'`), you receive extracted text in `textContent`. Parse tables/lists into structured rows and return with `source: "pdf"` and `extractedRows: [all rows as mapped objects]`.

If text is truncated (`truncated: true`), tell the user you only saw part and ask if they want to proceed.

### Column Matching Rules

**Map ALL recognizable columns — not just the obvious ones.** Every column that has a reasonable target field match should be included in `mappings`. Only put truly unmatchable columns in `unmappedColumns`. Err on the side of including more mappings — the user can change any mapping via dropdown before importing.

Common fuzzy matches for **plantCatalog**:
- "Common Name", "Plant Name", "Name", "Plant" → `commonName`
- "Botanical Name", "Scientific Name", "Latin Name", "Bot. Name" → `botanicalName`
- "Size", "Cont. Size", "Container Size", "Container", "Pot Size" → `size`
- "Price", "Unit Price", "Cost", "Unit Cost", "Each" → `unitCost`
- "Qty", "Qty.", "Quantity", "Count", "#" → `(skip)` (no quantity field in plant catalog)
- "Category", "Type", "Plant Type" → `category`
- "Supplier", "Vendor", "Nursery", "Source" → `supplier`
- "Notes", "Specifications", "Specs", "Comments", "Description" → `notes`

Common fuzzy matches for **contacts**:
- "First", "First Name" → `firstName`; "Last", "Last Name" → `lastName`; "Name", "Full Name" → `name`
- "Email", "E-mail" → `email`; "Phone", "Cell", "Mobile" → `phone`
- "Company", "Business", "Organization" → `company`

Common fuzzy matches for **properties**:
- "Address", "Street", "Property Address" → `address`
- "City" → `city`; "State" → `state`; "Zip", "Zip Code", "Postal" → `zip`

### Property Address Parsing

If a source has full addresses in one column (e.g., "123 Oak St, Orlando, FL 32801"), map it to `address` — the import function parses city/state/zip automatically.
