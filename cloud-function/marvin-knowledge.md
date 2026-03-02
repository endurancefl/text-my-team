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
| `schedule` | Schedule | Calendar for contract-based tickets, filterable by crew and division |

### Financials
| View ID | Name | Purpose |
|---------|------|---------|
| `invoices` | Invoices | Invoice management (draft, sent, overdue, paid) |
| `financials` | Financials | Financial reporting dashboard |

### Configuration
| View ID | Name | Purpose |
|---------|------|---------|
| `catalog` | Item Catalog | Labor and material items with production rates by difficulty |
| `services` | Service Catalog | Pre-configured services with default items, visits, billing tiers |
| `production` | Production Rates | Actual vs estimated production analysis |
| `worktickets` | Reminders | Reminder management (active, permanent, completed) |
| `reports` | Reports | Weekly reports view |
| `templates` | Templates | Save/load/duplicate estimate templates |
| `settings` | Settings | Global bid settings (rates, markups, travel, knowledge base) |

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
| Division | Maintenance | Currently only MNT is fully built |

Estimate-level overrides take precedence over bid settings. Property type (Residential/Commercial) determines which markup set is used.

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

### Divisions (MNT is fully built, others planned)
| Code | Name | Description |
|------|------|-------------|
| MNT | Maintenance | Recurring landscape maintenance — mowing, edging, pruning, etc. |
| IRR | Irrigation | Irrigation system maintenance and repair |
| CON | Construction | Hardscape, drainage, sod installations |
| ENH | Enhancement | Large mulch jobs, seasonal color installs, planting projects, renovations |

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
