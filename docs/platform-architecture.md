# Endurance Platform — Landscape Business Management SaaS

## Vision

A complete platform to run a landscape business: CRM, customer communication, bidding/estimating, scheduling, time tracking, invoicing, and financial reporting. Initially built for Endurance Services, designed from day one to be sold to other landscape companies as a multi-tenant SaaS product.

Think: **Jobber meets ServiceTitan, but purpose-built for landscape companies and built lean.**

---

## Business Divisions

The platform supports four divisions, each representing a distinct revenue stream with its own estimating workflow, item catalog, service catalog, and production rates:

| Code | Division | Description | Estimating Status |
|------|----------|-------------|-------------------|
| MNT | Maintenance | Recurring lawn care, mowing, edging, blowing, hedges, weed control, irrigation inspections, mulch | **Built** (estimate.html prototype) |
| IRR | Irrigation | Irrigation system install, repair, retrofit, drip conversion, backflow testing | Planned |
| CON | Construction | Hardscape, retaining walls, drainage, grading, sod installation, tree planting | Planned |
| ENH | Enhancement | Landscape enhancements beyond maintenance — large mulch jobs, seasonal color installs, planting projects, landscape renovations | Planned |

**Shared architecture, division-specific content:** All four divisions use the same estimating engine (items × production rates ÷ difficulty → hours → markups → price). The differences are in what items exist, what services are offered, and how takeoffs feed data. A single estimate can only belong to one division, but a property can have contracts across multiple divisions.

**What's the same across all divisions:**
- Item Catalog structure (item, unit, easy/medium/hard production rates, category)
- Service Catalog structure (services with line items, visits, billing tiers)
- Bid calculation engine (quantities ÷ rates → hours → labor cost × markup → bid price)
- Three-tier billing (Fixed, Billed Separately, Recommended)
- Template system, contract settings, payment schedule
- Ticket generation and earned revenue tracking

**What's different per division:**
- Items and production rates (a "Sod Installation" item only exists in CON)
- Services and their default configurations (IRR has "Irrigation Repair" with billed-separately tier)
- Takeoff sections (MNT has Lawn/Edge/Mulch Bed/Hedge/etc.; CON might have Excavation/Grading/Drainage)
- Default visit counts (MNT services are recurring; CON is typically one-time)
- Schedule types (MNT uses seasonal_mowing for recurring services; CON/ENH use project-based scheduling)

**Implementation approach:** Build Maintenance first (done), then add divisions by extending the catalog and service data without changing the calculation engine. Each division gets its own item catalog entries, service catalog entries, and templates. The `division` field on bids, contracts, and catalogs keeps everything separated.

---

## Current State (What Exists Today)

### Working Prototypes on GitHub Pages

**index.html — Customer Service Request Portal (~3,100 lines)**
- Customer-facing "Text My Team" form with PIN-based property identification
- Multi-step flow: PIN entry → photo capture with annotation → contact details → review → submit
- Full English/Spanish bilingual support via `data-i18n` system
- Photo annotation with canvas-based rectangle drawing tool
- Background photo upload (starts while user fills details — smart UX)
- Offline queuing with `localStorage` and auto-retry on reconnect
- Request status checking by phone number
- iOS-native feel: swipe-back gestures, haptic feedback, pull-to-refresh, safe area insets
- Returning user personalization (remembers name, PIN, language preference)
- PWA manifest with apple-mobile-web-app-capable

**crew.html + crew.css — Crew Dashboard (~9,089 lines HTML/JS + ~4,369 lines CSS)**
- iOS 18-precision mobile app for crew leaders
- **Full English/Spanish bilingual support** via `data-i18n` system — same `localStorage` key `preferredLang` shared with index.html so language choice persists across apps. Toggle pill-button on both login screen and dashboard header. `translations` object with ~160 keys (en/es), `t(key)` lookup function with English fallback, `updateLanguage()` traverses `[data-i18n]` and `[data-i18n-placeholder]` elements + rebuilds JS-generated UI via `renderStopCards()` and `renderRequests()`. All static HTML text tagged with `data-i18n` attributes. All JS-generated strings use `t()` calls with `{name}` template replacement for dynamic values. Date locales switch between `en-US` and `es-US`. Site Report and Before-After wizard internals deferred (large subsystems with ~50+ strings each).
- Phone number authentication against Crew Members sheet (Role = "Leader")
- **Schedule Tab (Home Screen)** — daily route with property-grouped stop cards, day/job clocks, crew check-in:
  - **Property-grouped route cards**: tickets are grouped by property address into collapsed cards (Shop ticket excluded from grouping). Each card shows address, total estimated time, service summary, and ticket count. Tapping expands to reveal individual tickets with Start buttons, per-service controls, and active ticket views. State tracked in `expandedPropertyGroups` map (address → boolean). Groups with active tickets auto-expand and cannot be collapsed. **Column-aligned layout**: est time, Start/Return buttons, Skip buttons, checkmarks, and "Skipped" labels all use fixed `min-width` + `text-align` so they form consistent vertical columns across all ticket rows regardless of content width. Est times use `font-variant-numeric: tabular-nums` for consistent digit widths. Helper functions: `renderPropertyGroupCard()`, `renderTicketSubRow()`, `renderActiveTicketExpanded()`, `togglePropertyGroup()`.
  - **Persistent Shop card**: always rendered at top of route when day is started. Orange-accented card with "S" badge. Tapping the card prompts the crew leader to describe what they're doing at the shop via `iosPrompt()` (`startShopWithDescription()`), then proceeds to member assignment. Description is required — empty input shows an alert. The description is stored as `shopNotes` on the active ticket and passed as `notes` to the backend time entry. While active, the shop card shows the activity description as its subtitle and "Stop" text; tapping calls `clockOutTicket('SHOP')`. Shop never fully "completes" — status resets to 'scheduled' on clock-out. Shop is fully manual (not auto-stopped by job tickets). Shop time shows as its own row in Day Summary, separate from Direct and Travel. Synthetic `SHOP` ticket injected in `loadSchedule()` with `isShopTicket: true`.
  - **Automatic travel time**: all time between stops is automatically tracked as travel behind the scenes. `autoStartTravel()` fires when `startDay()` completes and when a ticket completes with no other non-Shop tickets active. `autoStopTravel()` fires when a non-Shop ticket starts and when `endDay()` runs. Travel entries saved as `entryType: 'indirect'`, `indirectCategory: 'travel'`. State tracked in `currentTravelEntryId`. Indirect category picker UI fully removed.
  - **Sequential property enforcement**: crew cannot start a ticket at a new property while another property has active tickets. A confirmation dialog ("You still have active tickets at another property. Start this ticket anyway?") allows override for edge cases like adjacent properties. Shop tickets are excluded from this check. Enforced in `startTicket()`.
  - **Service-level crew reassignment ("Where to Next?" wizard)**: when a service within a ticket is completed and crew members are freed (not on any other active service in the same ticket), blocking modal via `#crew-reassign-overlay` (`data-reassign-type="service"`) shows an iOS inset-grouped-list of services. **Time-aware decision support**: active services display remaining wall-clock time (e.g. "0:18 left") and a blue projection line showing the time impact of adding the freed member (e.g. "→ 0:12 with Carlos"). Not-started services show their estimated time for 1 crew (e.g. "Not started · Est. 0:50"). **Fixed-duration services** show "Adding crew won't speed this up" instead of the projection line (`.fixed-note` class), display "Active · fixed duration" instead of crew count, and not-started fixed services show "Fixed · Est. 0:24" label. This turns blind reassignment into informed crew allocation — the crew leader can instantly see where the freed member would have the most impact, and won't waste crew on fixed-duration tasks. Active services have green left accent bar and "Active · 2 crew" label (or "Active · fixed duration"); not-started services show "Not started" (or "Fixed") in muted text. Each row has a right chevron affordance. **Tap feedback**: `haptic('light')` fires immediately, button highlights via `.tapped` class (150ms transition), then transitions to `.success` state (green background tint, green checkmark circle replaces chevron, service name turns green). All buttons disabled during 500ms animation to prevent double-taps. `haptic('success')` fires on advance to next member. Auto-dismisses when all ticket members are on a service or no services remain. Ticket-level reassignment between properties is intentionally omitted — freed crew goes into automatic travel time instead. CSS: `.reassign-list` (grouped container), `.reassign-service-btn` (row), `.is-active` (green accent), `.tapped`/`.success` (feedback states), `.reassign-chevron`, `.reassign-check` (green circle checkmark), `.reassign-time-info` (remaining time), `.reassign-time-projection` (blue projected-with-member line), `.reassign-time-projection.fixed-note` (italic muted "won't speed this up" text). Functions: `checkServiceReassignment()`, `showServiceReassignmentModal()`, `renderReassignWizard()`, `assignMemberToService()`, `refreshServiceReassignmentContent()`, `refreshReassignmentModal()`, `confirmReassignment()`. `closeAssignmentOverlay()` calls `refreshReassignmentModal()` to auto-dismiss when all members assigned.
  - **PIN-based crew check-in** (full-screen push overlay): each crew member verifies identity with a 4-digit PIN via `verifyPin` endpoint. Roster shows default crew; members enter PINs to verify. "Add Member" allows subs from other crews to join via PIN. `checkedInMembers` stored as objects `{name, pin, role, defaultCrew}` with backward-compatible `typeof m === 'string' ? m : m.name` pattern everywhere. Check-in slides in from right with back chevron navigation. **Auto-cycling PIN entry**: PIN pad auto-opens for the first crew member on check-in, then auto-advances to the next unverified member after each successful PIN (800ms success flash with green "✓ Name"). Shows "X of Y checked in" counter. "Crew Complete – Start Day" green button (`.start-day-mode` class) on PIN pad lets crew leader stop early without verifying everyone. When all members verified, shows "✓ All checked in!" and auto-closes. Functions: `findNextUnverifiedMember()`, `showPinEntryForNext()`.
  - **Day clock**: Start Day (requires at least 1 verified PIN) → running HH:MM:SS timer → auto-starts travel → End Day with auto-calculated total. End Day excludes Shop from active ticket check, auto-closes Shop if running, auto-stops travel.
  - **Multi-ticket simultaneous clocking**: crews can run multiple tickets at the same property simultaneously. Each ticket has its own elapsed timer and static target time shown in the expanded stop card. State tracked in `activeTickets` map (ticketId → {startTime, interval, assignedMembers, serviceClocks, completedServices, manHoursConsumed, phaseStartTime}).
  - **Member assignment overlay** (iOS bottom sheet): when starting a ticket, crew leader selects which checked-in members work this ticket. Edit Crew mid-ticket updates backend. Slides up from bottom with grabber handle, backdrop blur, tap-scrim-to-dismiss.
  - **Per-service clocking with crew assignment**: starting a service opens the member assignment overlay showing only AVAILABLE members — ticket members not already on another active service are shown; busy members are excluded from the new-service picker. Edit Crew for an existing service shows all ticket members but marks busy-on-other-service members as disabled. `startService()` → `showServiceMemberAssignment()` → `confirmStartService()`. **Solo auto-assign**: when only one member is available, `startService()` auto-assigns via `autoStartService()` without showing the overlay — keeps the flow snappy for solo crews. **All-crew-busy blocking**: when zero members are available (all on other active services), `startService()` blocks with `iosAlert(t('allCrewBusy'))` and returns — crew leader must finish a service to free someone up before starting a new one. Per-service assigned members stored in `at.serviceClocks[serviceName].assignedMembers`. Active services show assigned member names and an "Edit Crew" button (`confirmEditServiceCrew()`). When editing removes members from a service, freed members trigger `checkServiceReassignment()` — same "Where to Next?" wizard used after service completion. Available member list stored on overlay via `data-available-members` for correct checkbox-to-member mapping. Service time entries saved to backend with `serviceName`, per-service `crewMembers`, `memberCount`, and `estimatedHours` (from `getServiceEstHours()`) — making the Time Entries sheet self-contained for production rate analysis. **Service row separators**: individual service rows within expanded active tickets have a 1px gray separator border between them for visual clarity (`.service-row { border-bottom }` with `:last-of-type` exemption). **Consistent service action buttons**: Start, Done, and Edit Crew buttons on service rows all use `.svc-action-btn` class for uniform sizing (13px font, 6px 14px padding, 34px min-height). **Complete Visit separator**: the "Complete Visit" button has a full-width 1px separator line above it via `::before` pseudo-element to visually separate it from the service list.
  - **Clock-out decision overlay** (full-screen push): triggered by "Complete Visit" button on active tickets. Slides in from right with back chevron + "Clock Out" title. Shows est vs actual, over/under, service completion status. "Complete This Ticket" marks all services done. "Return Later" creates partial ticket with completed services carried over and `elapsedBeforePause` stored for timer resume.
  - **Timer resume for partial tickets**: when resuming a partial ticket, `effectiveStart` is offset backward by `elapsedBeforePause` seconds so the UI timer shows cumulative time across sessions. Backend still gets separate time entries per session. `elapsedBeforePause` is in-memory only (lost on page reload, but backend totals are always correct).
  - **PIN entry overlay** (iOS bottom sheet): slides up from bottom with grabber handle, backdrop blur, tap-scrim-to-dismiss. Max-width 500px.
  - **Partial ticket carry-over**: tickets with status "partial" show orange styling, completed services listed, "Return" button resumes with remaining services and cumulative timer.
  - **Request alerts**: Open requests appear as orange-tinted rows at the TOP of each property group card (above ticket rows) so crew leaders see them first. Each row shows warning icon, "Open Request" label, truncated message, customer name, date, an "Office" button, and a chevron. Tapping a request row opens the request detail modal via `openRequestFromCard()`. The "Office" button (`sendRequestToOffice()`) opens an SMS to the office pre-filled with request details so the crew leader can push unhandleable requests back. The request detail modal also includes a "Send to Office" button. Request alert messages and card rows show `translatedMessage` when in Spanish mode. CSS: `.ticket-sub-row.request-row`, `.send-to-office-btn`.
  - **Complete job modal** (legacy, centered): elapsed time vs. estimate, service checklist, optional notes
  - **Day summary** (centered modal): direct time (excludes Shop) vs. budgeted direct, travel time (all indirect = travel) vs. budgeted travel, separate Shop time row (orange), total hours, direct %, over/under badges, crew members. Stop counts exclude Shop ticket. No indirect category breakdown (simplified).
  - **Crew-hours display**: Two-tier time division. Property-group-level estimates are divided by full crew size (man-hours ÷ crew = crew-hours). Ticket-level targets use `at.assignedMembers.length` (the people actually assigned to that ticket) instead of total crew, so individual ticket timers reflect the real crew working that stop.
  - **Split time entries on crew changes**: When crew composition changes on a running entry (member added, removed, or Edit Crew confirms different list), the app splits the backend entry: closes the current entry at the moment of change and opens a new entry with the updated crew list. This prevents man-hour corruption (e.g., 2 crew for 60min + 2 more for 30min = 4 man-hours, not 6). Function `splitTimeEntry(opts)` handles the close+open: uses `queueableFetch` for fire-and-forget close, `fetch` for the new entry (needs entryId). Accepts optional `opts.durationType` and `opts.estimatedHours` to pass through to new time entries. Callers update `entryId` and `startTime`/`phaseStartTime` after split. For fixed-duration services, man-hours accumulation uses wall time (`segmentMinutes`) instead of `segmentMinutes × crewCount`. Functions that trigger splits: `assignMemberToService()` (freed member joins active service), `confirmEditServiceCrew()` (edit service crew), `confirmEditCrew()` (edit ticket crew), `removeCrewMember()` (remove from all running entries), `addMemberMidDay()` (add to all ticket job entries). Only splits when crew actually changed. If a removed member was the last person on a service, the entry is closed without opening a new one.
  - **Service progress bars + remaining time**: Active services show a thin 3px progress bar (green → yellow at 75% → red at 100%) tracking man-hours consumed vs `estimatedHours` from the service object. **Below the progress bar, a live-updating time label shows remaining wall-clock time** (e.g. "0:22 left · 2 crew" or "0:12 over · 3 crew"). Time recalculates instantly when crew changes — adding a member to a service immediately reduces the remaining time displayed. Updated every second in `updateServiceProgressBars()`. Turns red (`.over` class) when over budget. Progress accounts for crew changes via `svcClock.manHoursConsumed` (cumulative man-minutes from prior segments). On each split, `manHoursConsumed += segmentMinutes × oldCrewCount`. **Scalable vs Fixed duration types**: Services have a `durationType` property (`'scalable'` default or `'fixed'`). Scalable services (mowing, pruning) go faster with more crew — time math divides by crew count. Fixed-duration services (irrigation inspection, chemical application) take the same wall time regardless of crew count — progress tracks wall time only, remaining time shows no crew division, `getServiceRemainingWithExtra()` returns `null`, and man-hours accumulation uses wall minutes instead of `segmentMinutes × crewCount`. Fixed services display "fixed duration" instead of crew count in time labels, show a "FIXED" badge next to the service name (`.fixed-badge` CSS class), and in the reassignment wizard show "Adding crew won't speed this up" instead of time projections. Badge text reads "FIXED TIME" (en) / "TIEMPO FIJO" (es). Helper functions: `getServiceEstHours(ticket, serviceName)` extracts per-service hours, `getServiceDurationType(ticket, serviceName)` returns `'scalable'` or `'fixed'`, `isFixedService(ticket, serviceName)` boolean shorthand, `getServiceProgress(svcClock, estManHours, durationType)` computes progress fraction, `getServiceRemainingMin(svcClock, estManHours, durationType)` computes remaining wall-clock minutes for current crew, `getServiceRemainingWithExtra(svcClock, estManHours, durationType)` computes projected remaining with +1 crew member (returns `null` for fixed), `formatEstMin(wallMinutes)` formats as H:MM (e.g. "0:22", "1:15"), `formatRemainingMin(wallMinutes)` appends "left"/"over" suffix (e.g. "0:22 left", "0:12 over"). `formatMinutes()` also uses H:MM format for consistency across all time displays. CSS: `.svc-progress-track`, `.svc-progress-fill`, `.yellow`, `.red`, `.svc-remaining-time`, `.svc-remaining-time.over`, `.fixed-badge`, `.reassign-time-projection.fixed-note`.
  - **Resume support**: app can be closed and reopened mid-day, resumes ALL active ticket timers from saved time entries (multi-ticket aware), resumes open travel entry via `currentTravelEntryId`
  - **Native iOS overlay patterns**: PIN entry and member assignment use bottom-sheet pattern (slide up, rounded top corners, grabber, backdrop blur). Clock-out and check-in use full-screen push pattern (slide in from right, topbar with back chevron, swipe-from-left-edge to dismiss). Confirmations use iOS action sheet pattern (slide up from bottom, rounded button groups). Alerts use top-pill toast pattern. Complete-job, day-summary, and crew-reassignment remain centered modals.
  - **Haptic feedback**: `haptic(style)` utility using `navigator.vibrate()` with iOS-matching patterns: `light` (10ms), `medium` (20ms), `heavy` (30ms), `success` (double-tap), `warning` (triple-pulse), `error` (triple-buzz). Applied to: PIN digit entry, PIN error shake, service completion, day start, ticket start, tab switches, timer target exceeded, pull-to-refresh, swipe-back dismissal, action sheet presentation.
  - **iOS action sheets** (replaces all native `alert()`/`confirm()`/`prompt()`): `iosAlert()` shows a pill-shaped toast that slides down from top and auto-dismisses after 2.8s. `iosConfirm()` shows a bottom action sheet with rounded button groups, destructive styling, and Cancel button — matches iOS Share Sheet pattern. `iosPrompt()` shows a centered iOS-style alert dialog with text input. All 20+ native dialog calls replaced. CSS: `.ios-action-sheet-backdrop`, `.ios-action-sheet-group`, `.ios-action-sheet-btn`, `.ios-toast-alert`.
  - **Scroll-to-top on tab re-tap**: tapping the already-active tab scrolls content to top with `smooth` behavior. Standard iOS pattern. Implemented in `switchTab()`.
  - **Tab badge for requests**: red circle badge (`#requests-badge`) on Requests tab showing count of open requests. Updated in `updateStats()` via `updateRequestBadge()`. Hides when count is zero. CSS: `.tab-badge`.
  - **Theme-color meta tags**: `<meta name="theme-color">` with `prefers-color-scheme` media queries — `#F2F2F7` for light mode, `#000000` for dark mode. Browser chrome matches app background.
  - **Timer target vibration**: when a ticket's elapsed time crosses the estimated target, fires `haptic('warning')` once and turns the timer text red. Tracked in `timerTargetFired` map (ticketId → boolean). Implemented in `updateTicketCountdown()`.
  - **Pull-to-refresh visual indicator**: spinner pill (`#pull-refresh-indicator`) appears during pull-down gesture at scroll top. Rotation tracks pull progress, transitions to spinning animation on release past threshold (80px), auto-hides after 1.2s. Triggers `loadSchedule()` or `loadRequests()` depending on active tab. CSS: `.pull-refresh-indicator`, `.pulling`, `.refreshing`.
  - **Swipe-back gesture on push overlays**: `enableSwipeBack()` attaches touch listeners to full-screen push overlays. Tracks horizontal swipe starting from left 30px edge, translates overlay in real-time, dismisses on 100px+ swipe. Applied to: check-in overlay, clock-out overlay, all `.ios-screen` push views. Cancels if vertical movement exceeds horizontal.
  - **Demo mode** (`?demo=true` URL parameter): enables full-day testing without backend. Monkey-patches `fetch` to intercept all Google Apps Script calls and Cloud Function calls, returning mock data. Provides 5 crew members (Jake Miller/1111, Carlos Rivera/2222, Sam Thompson/3333, Dani Brooks/4444, Tyler Nguyen/5555), 5 tickets across 4 properties with 2-3 services each, with per-service `estimatedHours` matching `totalEstHours` totals. Two demo services have `durationType: 'fixed'` (Irrigation Check, Fertilizer Application) for testing fixed-duration behavior. Demo requests include 4 entries (3 open, 1 completed) across demo properties — including one at Oak Ridge Dr to trigger the open request row when that stop card is expanded, one with a photo indicator, and one internal request. **Demo properties**: 8 properties across 3 crews for Site Report and Before & After property search. **Demo reports**: prior site reports with 2-5 placeholder photos each (colored PNG images with notes and categories) for Oak Ridge Dr, Magnolia Blvd, and Mallard Circle — enables full Before & After workflow testing including report selection, photo loading, and comparison. **Demo PDF generation**: Lambda/Cloud Function calls intercepted (checks for `execute-api` and `cloudfunctions.net` in URL) and return a minimal valid PDF blob, allowing full site report and before-after wizard flows to complete. Auto-skips login, shows dashboard immediately. All write operations (saveTimeEntry, updateTimeEntry, deleteTimeEntry, completeJob, updateTicketStatus, reopenTicketService, saveSiteReport, inspectionPhoto) return mock success with `DEMO-*` entry IDs. Split operations logged with `[DEMO] saveTimeEntry` and `[DEMO] closeEntry` details. All intercepted calls logged to console with `[DEMO]` prefix.
  - **Cancel started ticket**: "Cancel Ticket" button in active ticket expanded view, only visible before any services are completed. Deletes the job time entry and any active service time entries from backend via `deleteTimeEntry`. Stops timer, resets ticket status to `scheduled`, dismisses reassignment overlay if open. Auto-starts travel if no other non-Shop tickets are active. Function: `cancelStartedTicket()`.
  - **Undo completed service** (15-second toast): after marking a service done, a toast slides up from bottom with "[Service] marked done" text and "Undo" button. Blue progress bar counts down 15 seconds then auto-dismisses. Undo reopens the service clock (clears `endTime`), removes service from `completedServices`, clears clock-out on backend via `updateTimeEntry` with empty `clockOut`, and dismisses the reassignment wizard if open. Only one undo active at a time — new completion replaces previous. State: `undoServiceData`, `undoToastTimer`. Functions: `showUndoServiceToast()`, `dismissUndoToast()`, `undoCompleteService()`. CSS: `.undo-toast` with `@keyframes undoCountdown`.
  - **Reopen completed service** (post-undo window): after the 15-second undo window expires, tapping a completed service row prompts "Reopen {name}? A new time entry will be created." via `iosConfirm()`. On confirm, opens member assignment overlay (title: "Reopen Service: {name}", button: "Reopen Service"), then creates a NEW time entry with `reopened: true` flag. Original entry stays closed — enables crew leader training reports on reopens. Progress resumes from prior man-hours (`manHoursConsumed` carries over). Notes auto-populated: "Reopened — originally completed at {time}". **Completed-ticket edge case**: if ALL services were completed and the ticket is fully closed, tapping a completed service reverts ticket status to `partial` via `reopenTicketService` endpoint, reactivates the ticket via `startTicket()`, then auto-triggers reopen flow. Backend `reopenTicketService()` endpoint removes service from `Completed Services` JSON column and optionally reverts ticket status. Time Entries sheet auto-upgrades with `Reopened` column. **Undo guard**: while undo toast is visible (first 15s), completed service rows are NOT tappable — undo is the primary action. State: `pendingReopenContext`, `pendingReopenService`. Functions: `promptReopenService()`, `reopenService()`, `confirmReopenService()`. CSS: `.service-row[onclick]` tap feedback. Translation keys: `reopenService`, `reopenConfirm`, `reopened`, `reopenedNote` (en + es). Demo mode: `reopenTicketService` logged to console, `saveTimeEntry` log includes `(REOPENED)` label when `body.reopened` is truthy.
  - **Offline queuing**: `queueableFetch()` wrapper sends POST immediately when online, queues to `localStorage` (`crewOfflineQueue` key) when offline. Orange "No signal" banner with queued count (`#crew-offline-banner`) when offline. Green "Back online" banner on reconnect, auto-flushes queue in FIFO order via `flushOfflineQueue()`. Fire-and-forget calls (skip, service clock-out, GPS updates) use `queueableFetch`; response-dependent calls (`saveTimeEntry` needing `entryId`) keep direct `fetch`.
  - **Skip entire property**: "Skip" button on property group card header for non-active, non-completed, non-skipped groups when day is started. Prompts for reason via `prompt()`, then skips all non-completed tickets in the group via `updateTicketStatus`. Uses existing `.skipped` CSS for muted styling. Function: `skipProperty()`.
- **Requests Tab** — customer request management: open/completed filtering, request detail view, status updates, completion photos
- SMS deep-linking for customer communication (iOS-specific `sms:/open` URL handling)
- Request acknowledgement tracking with timestamps
- Spanish translation support in request messages
- **Report Issue** — crew-submitted internal tickets with property search, photo capture
- **Quick Photos** — batch photo upload to Google Drive organized by property
- **Site Report Wizard** — multi-step flow: property selection → mode choice → photo capture with categories/notes → thumbnail strip → **service offer attachment** (recommend services with photos and catalog pricing) → PDF generation via AWS Lambda (ReportLab) → auto-upload to Google Drive → customer receives report with embedded approval buttons for offered services
- **Before & After Reports** — pulls photos from previous site reports, pairs with new "after" photos, generates comparison PDF. **Photo orientation matching (Layers 1 & 2 built)** — real-time orientation hint banner in detail modal with green/red color indicator via `window.resize` + `orientationchange` events, shows landscape/portrait guidance based on before photo's `naturalWidth`/`naturalHeight`; mismatch warning dialog via `iosConfirm()` when after photo orientation doesn't match before photo. Layer 3 (ReportLab) unnecessary — existing fill-and-crop scaling handles mixed orientations
- iOS design system: SF Pro typography, exact system colors, dark mode, frosted glass tab bar with `backdrop-filter`, iOS spring animations, 44px touch targets, `prefers-reduced-motion` support
- Bottom tab bar: Schedule (home) | Requests | Report Issue | Reports

**estimate.html — Bidding & Estimating Tool (~18,400 lines)**
- **Division: Maintenance (MNT) fully built** — Irrigation, Construction, and Enhancement divisions planned, will reuse the same engine with division-specific catalogs and takeoffs
- **Division & Job Type Selection**: When creating a new estimate, the user selects two things upfront:
  1. **Division** — Maintenance (MNT), Irrigation (IRR), Construction (CON), or Enhancement (ENH). This determines which item catalog, service catalog, and takeoff measurements are available. Stored as `division` on the estimate/bid.
  2. **Job Type** — **Recurring Service** or **Work Ticket**. Recurring services generate a contract with scheduled tickets over the contract duration (weekly mowing, monthly irrigation inspections). Work Tickets are one-off jobs with a defined scope and completion date — no recurring schedule, no monthly amortization (large mulch install, irrigation repair, retaining wall build, seasonal color rotation). Stored as `jobType` on the estimate (`'recurring'` or `'work_ticket'`).

  **How job type affects the pipeline:**
  | Aspect | Recurring Service | Work Ticket |
  |--------|------------------|-------------|
  | Billing tier | Fixed / Billed Separately / Recommended | Single total or milestone-based |
  | Payment schedule | Monthly amortization over contract months | Upon completion, 50/50 split, or milestone draws |
  | Ticket generation | `getDatesForVisitCount()` across contract duration | Single ticket or milestone tickets (e.g., "Demolition", "Install", "Cleanup") |
  | Contract PDF | Full contract with payment schedule + T&Cs | Proposal/work order with scope, price, timeline |
  | Schedule view | Recurring dots on calendar | One-time block on calendar |
  | Finalization | Creates contract row + recurring scheduled tickets | Creates work order + work ticket(s) |

  **Division × Job Type combinations** — All four divisions support both types:
  - MNT Recurring: weekly mowing contract, monthly hedge program
  - MNT Work Ticket: one-time leaf cleanup, storm damage cleanup
  - IRR Recurring: monthly irrigation inspection contract
  - IRR Work Ticket: sprinkler head repair, zone addition, backflow replacement
  - CON Recurring: rare (ongoing drainage maintenance)
  - CON Work Ticket: patio install, retaining wall, grading project
  - ENH Recurring: quarterly seasonal color rotation
  - ENH Work Ticket: large mulch job, landscape renovation, planting project

  The division and job type selection appears as the first step when clicking "New Estimate" — before the builder loads. The builder UI adapts: Work Tickets hide the payment schedule card and replace "Contract Duration" with "Project Timeline", and the billing tier picker is replaced with a simpler total/milestone pricing structure.

  **Work Ticket Scheduling (Hybrid Model)**: When a work ticket is created, the estimator picks a schedule type that controls how the job appears on the calendar and in the crew app:

  | Schedule Type | When to Use | What Gets Generated |
  |---------------|-------------|-------------------|
  | **Single Visit** | Small jobs done in one trip | One ticket, one date |
  | **Multi-Day** | Simple labor spanning consecutive days | N consecutive day tickets, same scope. Estimator picks start date and number of days. Hours split evenly or manually allocated per day. |
  | **Milestone** | Complex projects with distinct phases | Named phases, each independently scheduled with its own date, estimated hours, crew needs, and line items. Estimator defines the phases during estimation (e.g., "Demo → Grade & Base → Paver Install → Cleanup"). |

  **Schedule view rendering:**
  - **Day view**: Work ticket visits show like normal stop cards but with a project badge (division color) and progress indicator ("Day 2 of 4" or "Phase: Paver Install — 2/4").
  - **Week view**: Multi-day and milestone tickets render a colored bar spanning the date range (Gantt-style), with individual day markers inside the bar. Single-visit work tickets show as a single dot like recurring tickets.
  - **Month view**: Spanning bar across the date range with the project name. Distinct from recurring ticket dots.

  **Same man-hour engine, same crew app experience:** Work tickets use the exact same estimation pipeline as recurring services — items × production rates ÷ difficulty → man-hours. The estimated hours flow into each generated ticket identically to recurring tickets. In the crew app, work ticket stop cards show the same per-service progress bars, remaining wall-clock time, crew assignment overlays, and time entry tracking. The crew leader starts services, assigns members, splits time entries on crew changes, and completes services the same way. All time data feeds back into production rate analysis. The only difference is the project badge and progress label — the underlying time tracking is identical.

  **Crew app rendering:**
  - Stop card shows project name, phase/day label, and overall progress: "Mulch Install — Day 2 of 3" or "Patio Build — Phase: Base Prep (2/4)".
  - Same per-service clocking, progress bars, remaining time labels, and reassignment wizard as recurring tickets.
  - Completing the final visit/milestone marks the entire work ticket as complete.
  - If a multi-day job finishes early (done in 2 days instead of 3), crew leader can mark remaining day tickets as "Not Needed" which removes them from the schedule without counting as skipped.
  - Actual vs estimated comparison at completion feeds into production rate analysis — building the same data loop for work ticket service types (mulch spreading, paver install, grading) as exists for recurring services (mowing, edging, hedge trimming).

  **Data model**: Work ticket schedule type stored as `scheduleType` on the bid (`'single'`, `'multi_day'`, `'milestone'`). Multi-day tickets store `plannedDays` (integer). Milestone tickets store an ordered array of `milestones` — each with `name`, `sortOrder`, `estimatedHours`, `scheduledDate`, and associated `lineItems`. All generated tickets reference the parent work ticket via `workTicketId` and carry `sequenceIndex` (day number or milestone order) and `sequenceTotal`.

- Three-panel Google Workspace layout (sidebar, main content, summary panel)
- **Bid Builder**: Spreadsheet-style table with columns: Item, OCC, QTY, Unit, P/H, AH, TH, P/P, TP, GM%
- **Real-time calculation engine**: labor hours from quantities ÷ production rates, material costs from coverage rates, travel time percentage, separate markups for labor/materials/subcontractors
- **Three-tier billing structure**: Fixed Payment Services (monthly amortized), Services Billed Separately (upon completion), Recommended/Optional (customer opt-in with accepted/pending toggle)
- **Property Takeoff System** with Attentive.ai Excel import (SheetJS):
  - Lawn: equipment splits (48" Mower, 21" Mower, String Trimmer) with percentage allocation + difficulty splits (Easy/Med/Hard must sum to 100%)
  - Edge: Hard edge LF + Soft edge LF → Blade Edge line items
  - Mulch Bed: SF × percentage mulched → Mulch Spreading items with depth-adjusted coverage
  - Perennial: percentage of bed area → Perennial Care items
  - Weed Control: percentage liquid vs. hand weeding → separate line items
  - Seasonal Color: flowers ÷ flowers per flat → Spring/Fall items
  - Leaf Cleanup: canopy coverage × SF per bag → cleanup + hauling items
- **Item Catalog**: 20+ items with production rates by difficulty (SF/Hour, LF/Hour), material pricing (purchase unit, cost per unit, coverage per unit, default depth)
- **Service Catalog**: Pre-configured service templates with default visits, billing tiers, proposal names, descriptions (rich text via Quill.js editor), map colors, line item assignments, duration type (scalable or fixed)
- **Template System**: Save/load estimate structures (services, tiers, visits, travel %, contract duration), excludes property-specific data
- **Contract Settings**: Start/end dates, duration, payment months, price increase %, payment terms (Net 30, etc.), CC processing fee %, CC gross-up toggle, "Edit Terms & Conditions" button (opens Quill.js rich text editor modal)
- **CC Gross-Up**: When enabled, monthly payment is adjusted: `grossedUpMonthly = baseMonthly / (1 - ccFeePercent/100)`. Applied in summary panel, payment schedule, and finalize calculations. Data model fields: `ccFeePercent` (number), `ccGrossUp` (boolean).
- **Payment Schedule Generator**: Monthly payment distribution with penny rounding algorithm
- **Rich Text Editors (Quill.js v2)**: Three Quill.js rich text editors replace plain textareas for formatted content that flows into contract PDFs:
  - **Service Catalog Description**: Quill editor in the service catalog edit modal — stores HTML as `defaultDescription`
  - **Service Details Description**: Quill editor in the per-estimate service details modal — stores HTML in `service.description`, pre-populated from catalog `defaultDescription` when service is added
  - **Terms & Conditions**: Quill editor in a dedicated modal (opened from Contract Settings card) — stores HTML in `currentEstimate.contract.termsAndConditionsHtml` (null = server defaults). Pre-populated with 12 default clauses containing placeholder tokens `{duration}`, `{startDate}`, `{endDate}`, `{paymentTerms}`, `{priceIncrease}` that resolve at PDF generation time. "Reset to Defaults" button restores original text.
  - **Toolbar**: Headers (H1-H3), bold/italic/underline, text color (dark, red, gray), ordered/bullet lists, indent/outdent, clear formatting
  - **CDN**: Quill v2 via jsdelivr (~43KB gzipped), MIT license, no build step
- **Contract PDF Generation**: Generates professional contract PDFs via AWS Lambda/WeasyPrint pipeline. Two templates based on `propertyType`:
  - **Residential (3 pages)**: Quote page (services table, totals, recipient info), Description of Services (rich text HTML per-service from Quill editors, falls back to hardcoded descriptions if no per-service rich text), Terms & Conditions (custom rich text HTML with resolved tokens, falls back to 12 structured clauses) + signature section
  - **Commercial (5-6 pages)**: Cover page (logo, property info, optional service map image), Three-tier services tables (Fixed/Billed Separately/Recommended with category groupings), Payment schedule (12-month breakdown with penny rounding), Description of services (rich text HTML per-service, falls back to tier-grouped paragraphs), Terms & Conditions (custom rich text or structured fallback), Signature page
  - T&C clauses 11-12 (Price Increase, Tropical Event Policy) highlighted in red (in default structured fallback)
  - "Generate Contract PDF" button appears in header after estimate is finalized (when no PDF URL exists)
  - PDF auto-downloads and uploads to Google Drive (property folder → Contracts subfolder)
  - After upload, the Google Drive PDF URL and file ID are saved to the contract record via `updateContract`
  - Once a PDF URL is stored, header shows "View PDF" button (opens Drive link in new tab) + small "Regenerate" button
  - When opening a saved finalized estimate, the contract's `pdfUrl` is loaded from `allContracts` (or fetched) so the View PDF button persists across sessions
- **Estimate Revision & Re-Finalize Workflow**: Three-status lifecycle (Draft → Finalized → Revision → Finalized). When a finalized estimate is reopened and edited, status transitions to "Revision" (amber badge) instead of resetting to Draft. Re-finalizing updates the existing contract row and regenerates only future scheduled tickets — completed, skipped, and today's tickets are never touched. `revisionCount` tracks how many times a contract has been revised. The "Revise Estimate" button enters revision mode explicitly; "Update Contract" opens the finalize modal with revision-aware text ("Update Contract & Regenerate Tickets"). First-time finalization is unchanged.
- **Finalization Contact Validation**: Before finalizing, linked contact must have both email address and billing address populated. Shows toast error if missing. Prevents creating contracts without essential invoicing data.
- **Weekly Reports**: per-property visit summaries with services performed, dates, notes, customer email — send individually or batch send to all customers
- **Service Offers in Weekly Reports**: attach recommended services with catalog pricing and photos to weekly reports — customer approves with one tap from their email
- **Contacts (Lite CRM)**: Lightweight contact management built into estimate.html as a placeholder until HubSpot integration. Contacts have lifecycle stages (Lead → Prospect → Customer), are linked to estimates via `contactId`, and auto-promote to "Customer" when an estimate is finalized. Searchable by name, email, phone, address. Contact picker in the estimate builder auto-fills property address. Contact profile shows linked estimates and linked contracts (with View PDF links when available). Standalone `.contacts-grid` layout (8px card gap, individual card borders/radius). `setTimeout`-based scroll-to-top on all view switches and data loads (fires after browser layout completes). Stored in a "Contacts" Google Sheet. The `contactId` foreign key pattern survives the HubSpot migration — the field becomes `hubspot_contact_id` but the linking pattern is the same.
- **Properties View**: Central hub for every service address in the system. A property is the core operational entity — a single customer can have multiple properties, and a single property can have maintenance contracts, enhancement projects, and construction jobs running simultaneously. Each property card shows address, lot size, linked contact(s), and status indicators for active contracts. Clicking a property opens its profile with the following sections:
  - **Measurements (Attentive Takeoffs)**: All property measurements sourced from Attentive.ai takeoff reports or entered manually. Displays lawn SF, mulch bed SF, hedge SF/LF, hard/soft edge LF, tree count, irrigation zones, driveway/pavement SF, and all perimeters. Difficulty splits (Easy/Medium/Hard percentages) shown per measurement category. `measurement_source` badge indicates origin (`attentive`, `manual`, `polygon`, `gps_trace`, `drone`). Link to the original Attentive report file when available. These measurements drive every estimate — changing a measurement here propagates to future bids. In the current prototype, measurements live in the estimate's Property Setup tables (mower splits, edge splits, etc.); the Properties view centralizes them so they're entered once and reused across all estimates for that address.
  - **Contacts**: All contacts associated with this property — property owner, property manager, HOA contact, tenant. Linked via the contact's `propertyAddress` field. Each contact shows name, role/stage, email, phone. Click-through to full contact profile.
  - **Estimates (Open Bids)**: All draft and revision-status estimates for this property. Shows estimate date, annual value, service count, status badge (Draft/Revision). Click to open the estimate in the builder.
  - **Contracts (Finalized)**: All active and expired contracts. Shows contract ID, division (MNT/IRR/CON/ENH), start/end dates, annual value, status. View PDF link. Click to open the contract in schedule view.
  - **Enhancements & Construction** *(future)*: One-off projects that aren't recurring maintenance — large mulch installs, seasonal color rotations, hardscape jobs, drainage projects, sod installations. Each project has its own estimate, timeline, and completion status. These correspond to the ENH and CON divisions. Unlike maintenance contracts with recurring tickets, these generate a single set of work tickets with milestone-based scheduling.
  - **Service History** *(future)*: Timeline of all completed visits, skipped dates, reopened tickets, crew assignments, and time entries for this property. Aggregated from scheduled tickets. Useful for customer disputes, renewal negotiations, and production analysis.
  - **Notes & Files** *(future)*: Property-specific notes, photos, site maps, HOA guidelines, gate codes, irrigation maps, Attentive reports.

  **Data model (current prototype)**: Properties are implicitly created via `propertyAddress` on estimates and contacts — no dedicated Properties sheet yet. The Properties view will initially aggregate data from the Estimates, Contracts, and Contacts sheets by matching `propertyAddress`. When the platform migrates to PostgreSQL, properties become a first-class `properties` table (schema already defined in Database Schema section) with `property_id` foreign keys on bids, contracts, and contacts.

  **Nav placement**: Between Contacts and Production Rates in the sidebar. Icon: map pin or building.

- **Production Rates View**: Compares catalog production rates against actual field data from completed tickets. Nav item between Item Catalog and Schedule. Date range + crew filter. Two tabs: **Services tab** shows service-level comparison table sorted by worst efficiency — per-service visit count, avg est vs actual man-hours, variance badges (green/yellow/red), expandable rows with per-ticket breakdown and item-level implied rates. **Item Rates tab** shows item catalog with field rate columns — measured rates (from single-item services, direct qty/hours), inferred rates (from multi-item services, proportional via efficiency ratio), delta vs catalog rates, data point counts. Summary cards: tickets analyzed, overall efficiency, services over budget, reopened count. Ticket Services JSON enriched with per-item `quantities` (easy/medium/hard), `unit`, and `complexityFactor` during ticket generation for rate calculation. Functions: `initProductionView()`, `loadProductionAnalysis()`, `setProdTab()`, `renderProductionView()`, `renderProdServicesTable()`, `renderProdItemsTable()`, `renderProdTicketDetail()`, `toggleProdDetail()`, `populateProdCrewFilter()`. CSS: `.prod-variance-badge`, `.prod-confidence-tag`, `.prod-detail-row`, `.prod-detail-content`, `.prod-item-table`, `.prod-reopened-badge`, `.prod-empty-state`.
- **Schedule View (Route Management)**: Three display modes — day view with property stop cards and drag-drop reordering (`schedDrop()` + `saveRouteOrder()`), week calendar grid with drag-to-reschedule between dates, month calendar with ticket dots. Crew filter dropdown. Stop detail panel with earned value, margin, services. Functions: `loadScheduleView()`, `renderSchedDay()`, `renderSchedWeek()`, `renderSchedMonth()`, `showSchedTicketDetail()`, `rescheduleFromDetail()`, `skipFromDetail()`.
- **Financials Dashboard (Earned Revenue)**: Summary cards (contract value, collected, earned, deferred revenue, completion %). Monthly bar chart comparing earned vs collected with pagination. Contract table with per-contract breakdown. Deferred revenue = collected - earned (orange if positive/deferred, green if ahead of schedule). Functions: `loadFinancials()`, `renderFinancials()`, `calcCollectedToDate()`, `calcMonthlyData()`, `renderMonthlyChart()`, `renderContractTable()`.
- **Properties View**: Aggregated view of all unique service addresses derived client-side from contacts, savedBids, and allContracts arrays matched on normalized `propertyAddress`. No dedicated backend sheet — properties are virtual entities computed by `aggregateProperties()`. Nav item between Contacts and Invoices with house icon. List view with search + filter (All / Active Contract / No Contract). Each property card shows address, primary contact name, contract status badge, and monthly value. Click to open property profile showing: **Measurements** (from most recent bid's takeoffs — lot SF, lawn SF, hard/soft edge LF), **Linked Contacts** (clickable cards), **Estimates** (all bids for this address), **Contracts** (all contracts with status badges), **Service History** (lazy-fetched completed tickets via getScheduleView). State: `properties[]`, `currentProperty`, `propertySearchQuery`, `propertyFilter`. Functions: `normalizeAddress()`, `aggregateProperties()`, `loadProperties()`, `filterProperties()`, `renderPropertiesList()`, `openPropertyProfile()`, `fetchPropertyServiceHistory()`, `showPropertiesList()`. CSS: `.property-measurements-grid`, `.property-measurement-card`, `.property-measurement-value`, `.property-measurement-label`, `.property-contract-badge`.
- **Invoices View**: Full invoicing system with Stripe Checkout integration. Nav item between Properties and Settings with receipt icon. **Invoice Lifecycle**: `draft → finalized → sent → partial/paid` (any non-paid status can be voided). **Summary Cards**: Outstanding, Overdue, Collected This Month, Drafts. **List View**: Searchable + filterable (All / Draft / Sent / Overdue / Paid) invoice cards showing ID, property, contact, due date, total, status badge (color-coded per status). **Batch Generation**: "Generate Invoices" button calls `generateInvoiceBatch` which scans all active contracts, checks for existing invoices in the billing period (dedup), creates draft invoices, auto-charges auto-pay contracts via Stripe PaymentIntents API. Batch review modal shows auto-pay results, open ticket warnings, and draft invoices with checkboxes for batch finalization. **Invoice Detail**: Full invoice display with header/dates/line items table/totals/payment history. Action buttons change by status: Draft→Finalize, Finalized→Send, Sent→Record Payment + Check Payment + Void, Partial→Record Payment, Overdue→Record Payment + Resend. **Record Payment Modal**: Amount (pre-filled with balance due), method (check/cash/card/ACH), date, notes. **Send Invoice**: Creates Stripe Checkout Session (payment mode) for Pay Now link, generates invoice PDF via HtmlService (fallback) or Lambda, uploads to Drive, emails customer with PDF attachment + Pay Now button. **Payment Status Polling**: Checks Stripe session status, auto-records payment if paid. **Auto-Pay**: Contract-level auto-pay setup via Stripe Checkout (setup mode) — saves `stripeCustomerId` + `stripePaymentMethodId` on contract. During batch generation, auto-pay contracts are charged immediately. State: `invoices[]`, `currentInvoice`, `invoiceSearchQuery`, `invoiceFilter`, `invoicePayments[]`. Functions: `loadInvoices()`, `filterInvoices()`, `renderInvoiceSummaryCards()`, `renderInvoicesList()`, `openInvoiceDetail()`, `loadInvoicePayments()`, `showInvoicesList()`, `generateInvoiceBatch()`, `openInvoiceBatchModal()`, `closeInvoiceBatchModal()`, `finalizeBatchInvoices()`, `finalizeCurrentInvoice()`, `voidCurrentInvoice()`, `sendCurrentInvoice()`, `checkCurrentPaymentStatus()`, `openRecordPaymentModal()`, `closeRecordPaymentModal()`, `submitRecordPayment()`, `setupAutoPayForContract()`, `checkAutoPaySetupStatus()`. CSS: `.invoice-status-badge` (7 status colors), `.invoice-detail-header`, `.invoice-detail-meta`, `.invoice-line-items-table`, `.invoice-totals`, `.invoice-actions`, `.invoice-payment-history`, `.invoice-payment-item`, `.invoice-batch-item`, `.invoice-batch-warning`.
- **Ticket Scheduling Engine**: Three date distribution strategies dispatched by visit count in `getDatesForVisitCount()`: `generateSeasonalMowingDates()` (weekly Apr–Oct, biweekly Nov–Mar; fills dormant gaps for higher targets (e.g. 52), trims dormant dates for lower targets — visits === seasonalAnchor), `generateWeeklyDates()` (every week, 50-54 visits), `generateSimpleScheduleDates()` (even distribution, all others). Item-level visit override via `lineItem.itemVisits`. Tickets bundled by date with earned value proportionally distributed and penny reconciliation. `previewTickets()` shows breakdown before committing.
- Material Design styling with Google Sans/Roboto fonts

**payment-success.html — Stripe Payment Success Redirect**
- Receives `session_id` from Stripe Checkout redirect, shows success confirmation
- Also handles auto-pay setup success (`?setup=true`) with different messaging
- Minimal standalone page, no framework dependency

**payment-cancel.html — Stripe Payment Cancel Redirect**
- Simple "payment not completed" message when user cancels Stripe Checkout
- No backend calls needed

### Backend & Infrastructure
- **Backend** — Single consolidated Google Apps Script (Code.gs) serving both Estimating and Crew endpoints from one "Estimating" spreadsheet
- **PDF Generation** — AWS Lambda + API Gateway (Python/WeasyPrint container image, ReportLab fallback). Rich text HTML from Quill.js editors rendered natively by WeasyPrint via `.rich-text-content` CSS class. Template variable resolution via `_resolve_template_vars()` for T&C placeholders.
- **Hosting** — GitHub Pages (endurancefl.github.io)
- **Auth** — Crew leaders: phone number against Crew Members sheet (Role = "Leader"). Customers: 4-digit PIN against Properties sheet.
- **Data storage** — Google Sheets as database, Google Drive for files (estimates JSON, photos, site reports, invoice PDFs), localStorage for auto-save
- **Invoices Sheet** — Auto-provisioned. Columns: invoiceId (INV-0001), contractId, propertyAddress, contactName, contactEmail, billingAddress, invoiceDate, dueDate, billingPeriodStart, billingPeriodEnd, invoiceType (fixed_monthly/work_ticket/deposit), status (draft/finalized/sent/partial/paid/overdue/void), subtotal, taxRate, taxAmount, total, paidAmount, balanceDue, paymentTerms, payLinkToken, stripeSessionId, stripePaymentUrl, pdfUrl, pdfFileId, lineItemsJson (JSON column), createdAt, updatedAt
- **Payments Sheet** — Auto-provisioned. Columns: paymentId (PAY-0001), invoiceId, paymentDate, paymentMethod (card/ach/check/cash), amount, stripePaymentIntentId, stripeSessionId, status, notes, createdAt
- **Contracts Sheet (new columns for auto-pay)**: autoPay (YES/NO), stripeCustomerId, stripePaymentMethodId, stripeSetupSessionId — added dynamically by `ensureContractAutoPayColumns()`
- **Stripe Integration** — API calls via `UrlFetchApp.fetch()`, secret key in Script Properties (`STRIPE_SECRET_KEY`). No webhooks (Apps Script limitation) — uses polling from frontend + redirect pages. Zero card data touches our system (SAQ A PCI). Checkout flows: payment mode (one-time Pay Now) and setup mode (save card for auto-pay)

#### Combined Apps Script Endpoints

**GET endpoints (24):**
| Endpoint | Source | Description |
|----------|--------|-------------|
| `getItemCatalog` | Estimating | Returns item catalog with production rates |
| `getBidSettings` | Estimating | Returns settings key-value pairs |
| `getBids` | Estimating | Returns all bids |
| `getTemplates` | Estimating | Returns all templates |
| `getTemplate` | Estimating | Returns single template by ID |
| `getServiceCatalog` | Estimating | Returns service catalog (includes `durationType` if "Duration Type" column exists) |
| `getContracts` | Estimating | Returns all contracts (includes pdfUrl, pdfFileId) |
| `getContacts` | Estimating | Returns all contacts from the Contacts sheet (auto-creates sheet if missing) |
| `getCrews` | Crew | Returns crew names + crewSizes (active member counts per crew) |
| `getTickets` | Estimating | Returns tickets (with travelHours, needsReschedule), optionally filtered by contractId, startDate/endDate, crew, or `needsReschedule=true` (returns only queue tickets, ignores date filters) |
| `getRequests` | Crew | Auth by phone → returns crew's requests |
| `getProperties` | Crew | Returns all properties with address, crew, phone, pin |
| `getSavedReports` | Crew | Returns JSON report files from Drive for a property |
| `getReportData` | Crew | Reads JSON report data from Drive by fileId |
| `getPhotoBase64` | Crew | Reads photo from Drive, returns base64 |
| `getCrewSchedule` | Crew | Auth by phone → returns crew members, today's tickets (with travelHours, completedServices for partial), time entries |
| `verifyPin` | Crew | Validates 4-digit PIN against Crew Members sheet, returns {success, name, role, crew} |
| `getProductionAnalysis` | Estimating | Compares catalog production rates vs actual field data. Params: startDate, endDate, crew. Reads Scheduled Tickets (completed/partial) + Time Entries (service type), aggregates by service and item. Returns service-level efficiency (est vs actual man-hours) with per-ticket detail, and item-level field rates (measured from single-item services, inferred from multi-item services) compared to catalog rates |
| `getCrewMembers` | Crew | Returns all crew members from Crew Members sheet |
| `getRouteOrder` | Crew | Returns stop order for a crew on a given date |
| `getWeeklyReportData` | Estimating | Returns weekly property visit summaries for report emails |
| `getServiceOffers` | Estimating | Loads offers for a property or report |
| `getInvoices` | Invoicing | Returns all invoices, optional filters (status, contractId). Auto-creates Invoices sheet if missing |
| `getPayments` | Invoicing | Returns payments for a specific invoiceId. Auto-creates Payments sheet if missing |

**POST endpoints (44):**
| Endpoint | Source | Description |
|----------|--------|-------------|
| `saveContact` | Estimating | Creates a new contact in the Contacts sheet with auto-generated C-{timestamp} ID |
| `updateContact` | Estimating | Updates an existing contact by contactId |
| `deleteContact` | Estimating | Deletes a contact by contactId |
| `uploadEstimateJson` | Estimating | Saves estimate JSON to Drive |
| `createContract` | Estimating | Creates contract row with fields: bidId, propertyAddress, assignedCrew, preferredDay, startDate, endDate, contractMonths, monthlyPayment, paymentTerms, contractValue, ccFeePercent, ccGrossUp, contactName, contactEmail, billingAddress, pdfUrl, pdfFileId. Auto-creates new columns on existing sheets |
| `updateContract` | Estimating | Updates existing contract row by contractId — all fields including paymentTerms, contractValue, ccFeePercent, ccGrossUp, contactName, contactEmail, billingAddress, pdfUrl, pdfFileId |
| `saveTickets` | Estimating | Batch-creates scheduled tickets |
| `deleteFutureTickets` | Estimating | Deletes future scheduled tickets for a contractId (status='scheduled' AND eventDate > afterDate) — used during estimate revision to regenerate tickets |
| `updateTicketStatus` | Estimating | Updates ticket status/completed date; auto-sets `Needs Reschedule=TRUE` when status is `skipped` |
| `rescheduleTicket` | Estimating | Moves ticket to new date; clears `Needs Reschedule` flag |
| `bulkSkipDay` | Estimating | Bulk-skips all scheduled/partial tickets for a crew on a date — sets status to `skipped`, `Needs Reschedule=TRUE`, Notes to reason |
| `saveBid` | Estimating | Creates new bid row |
| `updateBid` | Estimating | Updates existing bid row |
| `saveBidSettings` | Estimating | Saves settings key-value pairs |
| `saveTemplate` | Estimating | Creates or updates template |
| `deleteTemplate` | Estimating | Deletes template by ID |
| `deleteBid` | Estimating | Deletes bid by ID |
| `saveTimeEntry` | Crew | Creates time entry (day_clock, job, indirect, service). Accepts optional `estimatedHours` for service entries (auto-upgrades Estimated Hours column) |
| `updateTimeEntry` | Crew | Updates existing time entry (fills in clockOut/duration/crewMembers/memberCount). Supports clearing clockOut (empty string) for undo operations. Finds by entryId or by crew+date+type fallback |
| `deleteTimeEntry` | Crew | Deletes a time entry row by entryId. Used by cancel-ticket and undo flows |
| `completeJob` | Crew | Marks ticket completed/partial + updates time entry. Supports `partial: true` with `completedServices` array for partial carry-over |
| `reopenTicketService` | Crew | Removes a service from the Completed Services JSON column on a ticket. Optionally reverts ticket status from `completed` to `partial` when `revertStatus: true` |
| `uploadPhoto` | Crew | General photo upload to Drive |
| `updateAcknowledged` | Crew | Marks request as acknowledged |
| `updateStatus` | Crew | Updates request status |
| `uploadInspectionPhoto` | Crew | Quick Photos upload with subfolder organization |
| `uploadSiteReportPdf` | Crew | Uploads site report PDF to Drive |
| `uploadContractPdf` | Estimating | Uploads contract PDF to Drive (property folder → Contracts subfolder). Returns `{ pdfUrl, fileId }` — caller saves these to the contract record via `updateContract` |
| `saveSiteReportJson` | Crew | Saves report JSON data to Drive |
| `saveServiceOffer` | Crew/Estimating | Creates service offer attached to a report |
| `approveServiceOffer` | Customer (token) | Customer approves an offered service |
| `declineServiceOffer` | Customer (token) | Customer declines an offered service |
| `saveRouteOrder` | Crew | Persists drag-drop stop reordering for a crew day |
| `sendWeeklyReport` | Estimating | Sends weekly property report email to customer |
| `uploadSiteReportPhoto` | Crew | Uploads individual site report photo to Drive |
| `submitRequest` | Text My Team | Submits customer service request with photo |
| `saveServiceOfferResponse` | Estimating | Records customer approval/decline of service offer |
| `generateInvoiceBatch` | Invoicing | Scans active contracts, creates draft invoices for current billing period (dedup by contractId + period), auto-charges auto-pay contracts via Stripe PaymentIntents, flags open tickets. Returns `{ invoices, openTickets, autoPayResults }` |
| `finalizeInvoice` | Invoicing | Updates invoice status from `draft` → `finalized` |
| `voidInvoice` | Invoicing | Updates invoice status to `void` (any non-paid status) |
| `recordPayment` | Invoicing | Appends to Payments sheet, updates invoice paidAmount/balanceDue/status (→ `partial` or `paid`) |
| `sendInvoice` | Invoicing | Creates Stripe Checkout Session (payment mode), generates PDF via HtmlService, uploads to Drive, emails customer with PDF + Pay Now link, updates invoice status → `sent` |
| `createStripeCheckoutSession` | Invoicing | Creates Stripe Checkout Session in `payment` mode. Returns `{ sessionId, url }` |
| `setupAutoPay` | Invoicing | Creates Stripe Customer + Checkout Session in `setup` mode, emails customer setup link. Adds `autoPay`, `stripeCustomerId`, `stripePaymentMethodId`, `stripeSetupSessionId` columns to Contracts sheet |
| `checkAutoPaySetup` | Invoicing | Polls Stripe setup session, stores payment method + customer ID on contract when complete |
| `checkStripePayment` | Invoicing | Polls Stripe payment session, auto-records payment if paid. Returns `{ paid, status }` |

### What Works Well
- The UX patterns and workflows are production-quality — crew uses them daily
- Deep domain knowledge encoded in the calculation engine (production rates, takeoff pipeline, difficulty adjustments, material coverage, payment schedules)
- iOS design quality on crew.html is genuinely native-feeling
- Bilingual support (English/Spanish) is baked into both index.html and crew.html, not bolted on — shared `preferredLang` localStorage key persists choice across apps
- Offline resilience (index.html queues requests, crew.html has `queueableFetch` with localStorage queue + auto-flush on reconnect)

### What Won't Scale
- Google Sheets as a database (no relationships, slow at volume, concurrent write issues)
- Apps Script as an API (6-min timeout, cold starts, URL changes on redeploy)
- Phone number "auth" (no security, no roles, no multi-company support)
- Single HTML files (can't share code between pages, hard to maintain as features grow)
- GitHub Pages (static only, no server-side logic, no API routing)
- No tenant isolation — single-company only
- No relational integrity, no foreign keys, no data backup strategy

### What's Highly Reusable (Migration to React/PostgreSQL)

**Extract almost directly to TypeScript service modules (→ `packages/calculation-engine`):**
- `calculateBidTotals()` → `bidCalculator.ts`
- `calcServiceHours()`, `calcLineItemMaterialCost()` → reusable calculation functions
- `calculateTierTotals()` → Fixed/Billed/Recommended separation logic
- `calculatePaymentSchedule()` → penny distribution algorithm
- `buildServicesFromTakeoffs()` → master takeoff-to-line-item pipeline
- All individual takeoff calculators (lawn, edge, mulch bed, perennial, weed control, seasonal color, leaf cleanup)
- Item catalog structure → seed data for `production_rates` table (Maintenance division first, then IRR/CON/ENH)
- Service catalog → seed data for service templates (per division)
- `currentEstimate` data model → maps cleanly to PostgreSQL schema + shared TypeScript types

**Rebuild as React + TypeScript components (preserving UX patterns):**
- Three-panel layout → React layout components with Tailwind (`apps/platform`)
- Spreadsheet-style bid table → `BidTable.tsx`
- Property setup with Attentive upload → `PropertySetupCard.tsx`
- Takeoff tables → `TakeoffTables.tsx`
- iOS design system (crew.html CSS variables) → Tailwind config + `packages/ui` shared component library
- Property search autocomplete → `packages/ui/PropertySearch/`
- Bottom tab navigation → `packages/ui/BottomTabBar/`

---

## Recommended Technology Stack

Chosen for: simplicity, type safety, hiring ease, low cost at small scale, ability to grow, and strong Claude Code support.

**Language: TypeScript** across the entire stack (frontend + backend). Type-safe, easy to hire for, easy to code in, and catches bugs at compile time. With ~100k lines projected for production, type safety pays for itself immediately.

**Cloud Provider Decision:** AWS or Azure — both work. Key mapping:
| Concern | AWS | Azure |
|---------|-----|-------|
| File storage | S3 | Blob Storage |
| Containers | ECS / App Runner | Container Apps |
| Database | RDS PostgreSQL | Azure Database for PostgreSQL |
| Auth | Cognito (or BetterAuth) | Azure AD B2C (or BetterAuth) |
| Functions | Lambda | Functions |
| CDN / Hosting | CloudFront + S3 | Static Web Apps |

Pick based on which ecosystem you're more comfortable in or which your dev has experience with. The architecture works on either.

**Repository Structure: Monorepo** — both apps (Management Platform + Crew App) live in one repo and share the component library, TypeScript types, API client, and utilities while being independently deployable. Tools: Turborepo or Nx for monorepo management.

### Frontend
**React + Vite + Tailwind CSS + TypeScript — Two Apps in a Monorepo**

#### Management Platform (Desktop-First)
- The full business management suite: bidding/estimating, scheduling, CRM, invoicing, reports, admin
- Optimized for desktop/laptop with responsive support for tablet
- Data-dense layouts, tables, sidebars, multi-panel views (preserving the three-panel layout from estimate.html)
- Used by: Owners, Managers

#### Crew App (Mobile-First)
- Streamlined field operations app: schedule/route, time clock, customer requests, site reports, quick photos
- Optimized for iPhone — native iOS feel, one-hand usable, fast
- Preserves the iOS 18 design system from crew.html (SF Pro, system colors, frosted glass, spring animations)
- Offline-capable for time clock and daily schedule
- Used by: Crew Leaders, Crew Members
- Evolves from the current crew.html

Both apps live in the same monorepo, share the component library (`packages/ui`), TypeScript types (`packages/shared`), calculation engine (`packages/calculation-engine`), and API client (`packages/api-client`) — but have different page layouts and navigation patterns. The Crew App uses bottom tab navigation. The Management Platform uses a left sidebar. Each app is independently deployable.

### Backend API
**Node.js + Express + TypeScript, deployed on Cloud Run (GCP) / App Runner (AWS) / Container Apps (Azure)**
- Serverless containers — you only pay when requests come in. Scales to zero when idle, scales up automatically under load. No server management.
- Express: simple, well-documented, Claude Code writes it fluently
- Why not Apps Script: Can't handle real auth, real database connections, background jobs, file uploads, or webhook integrations.
- TypeScript on the backend shares types with the frontend — a `Ticket` type defined once is used in the API response, the API route handler, and the React component that renders it.

### Database
**PostgreSQL on a managed cloud service (Cloud SQL / RDS / Azure Database for PostgreSQL)**
- Relational database — perfect for business data with relationships (customers → properties → contracts → schedules → time entries → invoices)
- Managed service: automatic backups, patching, scaling. You don't manage the server.
- Why not Firestore/NoSQL: Your data is highly relational. Invoices reference time entries which reference schedules which reference properties which reference customers. SQL is built for this.
- **Row Level Security (RLS)** for tenant isolation — pass `tenant_id` once and all queries are automatically scoped to that tenant. Simple to implement, impossible to accidentally leak data across tenants.
- **Realistic cost: $50-75/month** for a cloud-managed PostgreSQL instance in production. Dev environments can be cheaper, but budget for this range once you have real data and users.

### Authentication
**BetterAuth (Node.js)**
- Open-source, self-hosted auth library for Node.js/TypeScript — no vendor lock-in
- Handles login/signup, password reset, email verification, phone auth, OAuth (Google, Apple)
- Issues JWT tokens that your API verifies on every request
- Multi-tenant support built in — tenants are first-class citizens
- Role-based access control (Owner, Manager, Crew Leader, Crew Member, Customer)
- Why BetterAuth over Firebase Auth: No external dependency, runs on your own server, full control over the auth flow, tenant-aware out of the box, and you're already running Node.js

### File Storage
**S3 (AWS) or Blob Storage (Azure) — same thing, different names**
- Photos from inspections, site reports, signed proposals, invoice PDFs, drone orthomosaics
- Cheap, fast, virtually unlimited
- Direct upload from the browser (presigned URLs) — no bottleneck through your API
- Pick based on your cloud provider choice

### PDF Generation
**Current: AWS Lambda + API Gateway (Python/WeasyPrint + ReportLab dual engine) — Container image deployment**
- Endpoint: `https://ibjyxrp542.execute-api.us-east-1.amazonaws.com/prod/generate_site_report`
- **Architecture**: API Gateway HTTP API receives multipart/form-data → Lambda parses event → `pdf_generator.py` (WeasyPrint, default) or `main.py` (ReportLab, fallback) generates PDF → base64-encoded response
- **Rendering engines**: Two engines coexist during migration. The `renderer` field in metadata JSON selects the engine (`"weasyprint"` default, `"reportlab"` fallback). `DEFAULT_RENDERER` in `lambda_function.py` controls the global default.
- **WeasyPrint engine** (`pdf_generator.py`): Jinja2 HTML/CSS templates rendered to PDF via WeasyPrint. Photos embedded as base64 data URIs. Templates live in `cloud-function/templates/`. CSS edits are previewable in a browser via `test_local.py --html`.
- **ReportLab engine** (`main.py`): Original coordinate-based PDF generation (~2,193 lines). Kept as fallback during migration. Will be deleted after all 4 PDF types are validated in production.
- `lambda_function.py` — Lambda handler: parses multipart boundary from API Gateway event, extracts metadata JSON + photo blobs, selects rendering engine, routes by `metadata.type`: `invoice` → `generate_invoice_pdf()` (WeasyPrint only), `contract` → `generate_contract_pdf()`, `before_after` → `generate_before_after_report()`, `standard` → `generate_standard_report()`
- Lambda config: Python 3.11, **1024MB memory** (WeasyPrint needs more than ReportLab), 60s timeout
- **Deployment**: **Docker container image** (not zip). `Dockerfile` in `cloud-function/` uses `public.ecr.aws/lambda/python:3.11` base with system deps (pango, cairo, gdk-pixbuf2, libffi, fontconfig, freetype, harfbuzz). SAM template uses `PackageType: Image`. ECR repo created on first `sam deploy --guided`. Deploy via `cloud-function/deploy/deploy.sh`.
- **Template structure**:
  ```
  cloud-function/templates/
    base.html                   # Shared @page rules, CSS vars, footer
    site_report.html            # Photo grid report
    before_after.html           # Comparison report
    contract_residential.html   # 3-page residential contract
    contract_commercial.html    # 5-6 page commercial contract
    invoice.html                # Invoice PDF template with line items, totals, pay link
    styles/
      common.css                # Shared print CSS (header, info box, category bars)
      site_report.css           # 2-column CSS grid, photo frames, note boxes
      before_after.css          # BEFORE/AFTER paired layout
      contract.css              # Tables, signatures, terms, payment schedule
      invoice.css               # Invoice table, totals, bill-to, details box
  ```
- **Color palette** (CSS variables in `base.html`): `--green: #3A5F4B`, `--dark: #1A2E24`, `--gray-header: #666666`, `--light-gray: #CCCCCC`, `--contract-light-gray: #F5F5F5`, `--contract-red: #C62828`, `--before-red: #DC2626`, `--after-green: #16A34A`
- Handles Site Report, Before & After, and Contract PDF types (distinguished by `metadata.type` field)
- **Site Report layout**: 2-column CSS grid. Photos grouped by category with category headers, notes below each photo, page numbering via `@page` counters, logo on page 1. `object-fit: cover` replaces ReportLab's manual crop algorithm.
- **Before & After layout**: Side-by-side comparison — BEFORE (red banner) left, AFTER (green banner) right. CSS grid pairs with `page-break-inside: avoid`. New page per category.
- **Contract PDF layout**: Two templates based on `propertyType`. Residential: 3-page (quote, service descriptions, T&C + signatures). Commercial: 5-6 page (cover, three-tier services tables, payment schedule, service descriptions, T&C, signatures). Both include 12 standard terms clauses with template variables. Clause 12 (Named Tropical Event Policy) uses numbered sub-items instead of plain text. `_get_terms_clauses()` returns `(title, text)` tuples where text is a string or a list of sub-item strings. Both engines and all templates handle both formats. Optional `service_map` photo for commercial cover page. Functions: `generate_contract_pdf()`, `_generate_residential_contract()`, `_generate_commercial_contract()`
- Request format: `multipart/form-data` with JSON `metadata` field + photo blobs (`photos`, `before_photos`, `after_photos`)
- Photos composited client-side (annotations burned onto canvas) before upload. Site Report: max 1600px, 85% JPEG quality. Before & After: max 1000px, 75% quality
- PDF returned as binary blob (base64 via API Gateway) → auto-downloaded to device → uploaded to Google Drive via Apps Script (`siteReportPdf: true`)
- Individual photos and report JSON also uploaded to Drive for future reference (Before & After pulls prior photos from these)
- CORS configured at API Gateway level + Lambda response headers for GitHub Pages origins
- Demo mode: `crew.html` intercepts `execute-api` URLs (and legacy `cloudfunctions.net`) to return mock PDF blobs
- **Local dev workflow**: `python test_local.py standard --html` opens HTML in browser for rapid CSS iteration. `python test_local.py standard` generates WeasyPrint PDF. `--reportlab` flag uses old engine for comparison.

**Built: Before & After photo orientation matching (Layers 1 & 2):**

1. **Layer 1 — Real-time orientation hint banner + landscape Take Photo button** (crew.html, ✅ built): In `baOpenDetailModal()`, a new `Image()` loads the before photo and reads `naturalWidth`/`naturalHeight`. Stores `photo.beforeIsLandscape` on the photo object. Shows a persistent banner (`#ba-orientation-hint`, `.ba-orientation-hint` in crew.css) above the Take Photo / Upload buttons. Uses `window.resize` + `window.orientationchange` events with `window.innerWidth > window.innerHeight` detection for real-time color updates: green (`.hint-match`, `rgba(76,175,80,0.85)`) with "✅ Orientation matches — ready to shoot" when device matches before photo, red (`.hint-mismatch`, `rgba(255,59,48,0.85)`) with rotation guidance when mismatched. CSS transition on background-color for smooth color change. When device is landscape and orientation matches, a full-screen white overlay (`#ba-landscape-overlay`, `.ba-landscape-overlay`) appears with a large centered green "Take Photo" button (`#ba-landscape-take`, `.ba-landscape-take`) so users don't have to scroll past the zoomed-in before photo. Hidden in portrait, hidden once an after photo is saved. Listener cleaned up in `baCloseDetailModal()`.

2. **Layer 2 — Mismatch warning dialog** (crew.html, ✅ built): In `baProcessAfterPhoto()`, after the after image loads and dimensions are known (`w > h` vs `photo.beforeIsLandscape`), if orientations mismatch, shows `iosConfirm()` dialog: "This photo is [portrait/landscape] but the original was [landscape/portrait]. The report looks best with matching orientations." Buttons: "Use Anyway" (saves the photo) / Cancel (discards the photo). Save logic wrapped in `saveAfterPhoto()` inner function called by both paths.

3. **Layer 3 — ReportLab layout normalization** (not needed): The PDF renderer already handles mixed orientations with fill-and-crop scaling inside fixed bounding boxes. Client-side guidance is sufficient.

- WeasyPrint HTML/CSS templates now replace the need for Puppeteer/Playwright — CSS print layout gives full control over page breaks, headers, footers, and photo grids while remaining previewable in any browser

### Hosting (Frontend)
**Cloud-native static hosting (S3 + CloudFront / Azure Static Web Apps / Firebase Hosting / Vercel)**
- Free or near-free SSL, global CDN, automatic deployments
- Connects to your custom domain
- Serves your React/Vite build
- Vercel is also an excellent option if you want zero-config deployments with preview URLs per PR

### Google Calendar (Optional Sync Target)
**Sync, not source of truth — the schedule lives in the database**
- Google Calendar receives a copy of scheduled events for crew visibility
- Crew leaders see tomorrow's route on their iPhone lock screen without opening the app
- Push notifications 15 minutes before each stop
- Manager gets a bird's-eye weekly view of all crews in Calendar's native UI (color-coded by crew)
- Shared calendars viewable by office staff in Google Workspace
- Calendar cannot handle: time clock, service bundling, ticket status, smart request prompts, actual vs. estimated tracking
- Implementation: Apps Script `CalendarApp` for prototype, migrate to Calendar API on Cloud Run later
- Calendar sync is an add-on, not a blocker — the crew app schedule tab works independently

### CRM
**Current: Lite CRM in estimate.html (Google Sheets "Contacts" sheet) → Future: HubSpot**
- **Today**: A built-in Contacts feature in estimate.html stores contacts in a Google Sheets "Contacts" sheet. Contacts have lifecycle stages (Lead/Prospect/Customer), are linked to estimates via `contactId`, and auto-promote to Customer on estimate finalization. Contact profile view shows linked estimates AND linked contracts (matched via bids that have a contractId). Contract cards show property address, contract ID, status, date range, monthly payment, and a "View PDF" link when a PDF URL is stored. This is a placeholder — the `contactId` foreign key pattern, the contact picker UI, the profile page layout, and the linked-estimates/contracts views all carry forward to HubSpot.
- **Future**: HubSpot becomes the source of truth for customer contact data — your team enters and manages customers in HubSpot
- Your platform syncs from HubSpot via REST API (poll every 10-15 min) and caches locally
- Free tier: up to 1,000,000 contacts, full API access, 10 custom properties
- Starter ($20/seat/month): more custom properties, HubSpot branding removed
- Each tenant connects their own HubSpot account via OAuth — clean multi-tenant separation
- Your platform writes summary data back to HubSpot (active contracts, monthly revenue, next service date) so the office team sees the big picture without leaving HubSpot
- Platform events (contract signed, job completed, invoice sent) logged to HubSpot timeline

### Email / SMS
**SendGrid (email) + Twilio (SMS)** — add when needed for customer communication
- SendGrid free tier: 100 emails/day
- Twilio: pay-per-message for SMS/text notifications
- All outbound messages logged back to HubSpot as timeline events

### Accounting
**QuickBooks Online — the accounting backbone**
- Tenants connect their own QBO account via OAuth
- Platform pushes invoices, payments, and direct labor expenses to QBO — the accountant works in QuickBooks as they always have
- QBO produces the official P&L, balance sheet, and tax reports
- Direct labor expenses calculated from time entries (crew hours × rates) and pushed monthly
- Platform keeps earned revenue and operational analytics internally (management accounting)
- Two views: QBO for "did we make money?" (cash accounting) / Platform for "are we on track?" (operational)

### E-Signature
**Built-in signature pad (default) + optional DocuSign**
- Default: HTML5 Canvas signature capture — finger, stylus, or mouse. Zero cost, no external dependency.
- Optional: tenants who want DocuSign connect their own account via OAuth. One toggle to enable.
- Both paths produce the same outcome: a signed PDF and a contract activation trigger.

---

## Multi-Tenant Architecture

Since other companies will use this platform, every piece of data belongs to a **tenant** (a company). This is the most important architectural decision.

### How It Works
- Every table in the database has a `tenant_id` column
- Every API request includes the tenant context (derived from the authenticated user's company)
- **Row Level Security (RLS)** in PostgreSQL enforces tenant isolation at the database level — pass `tenant_id` once via `SET app.current_tenant`, and every query is automatically filtered. Even a bug in application code can't leak data across tenants.
- The API middleware sets the tenant context on every request based on the logged-in user's JWT

### Why RLS Over Application-Level Filtering
- **Simple**: One policy per table, applied automatically to every query
- **Safe**: Impossible to forget a `WHERE tenant_id = ?` clause — the database enforces it
- **Fast**: PostgreSQL optimizes RLS policies into query plans efficiently
- **Early priority**: Implementing RLS early is simple and prevents data leaks from day one. Retrofitting it later is harder.

### User Hierarchy
```
Tenant (Company)
  └── Users
       ├── Owner — full access, billing, company settings
       ├── Manager — scheduling, contracts, timesheets, bidding, reports
       ├── Crew Leader — view schedule, time clock, tickets, reports
       ├── Crew Member — view schedule, time clock
       └── Customer — view proposals, invoices, request service (future portal)
```

### Onboarding a New Company
1. Company signs up → creates a tenant record
2. First user becomes the Owner
3. Owner invites managers and crew via email or phone
4. Crew members get a simple sign-up link tied to that tenant
5. All their data is isolated from every other company

---

## Database Schema (Core Tables)

This is the foundation. Every feature builds on these relationships.

**Design principles:**
- Every table has `tenant_id` for RLS isolation (including the `tenants` table itself, which uses its own `id` as `tenant_id` for self-referencing consistency)
- Tables that store one row per tenant (settings, preferences, billing config) are consolidated into the `tenants` table itself or a single `tenant_settings` table — this makes queries and joins dramatically simpler and makes route configuration 10x easier
- Foreign keys enforce relational integrity
- `created_at` / `updated_at` timestamps on every table

```sql
-- Multi-tenant foundation
tenants (
  id,                              -- UUID, also serves as tenant_id for self-reference
  tenant_id,                       -- references self (id) — enables RLS consistency across all tables
  name, slug, address, phone, email, logo_url,
  -- Consolidated settings (one row per tenant — avoids separate settings tables)
  default_labor_rate, default_labor_markup, default_material_markup, default_sub_markup,
  default_travel_time_pct, default_contract_months, default_payment_terms,
  -- HubSpot integration (each tenant connects their own HubSpot account)
  hubspot_access_token,            -- encrypted OAuth token
  hubspot_refresh_token,           -- encrypted OAuth refresh token
  hubspot_portal_id,               -- HubSpot account ID
  hubspot_last_sync_at,            -- last successful full sync
  -- DocuSign integration (optional — tenant-level add-on)
  docusign_access_token,           -- encrypted OAuth token (null if not connected)
  docusign_refresh_token,          -- encrypted OAuth refresh token
  docusign_account_id,             -- DocuSign account ID
  use_docusign_for_signing,        -- boolean: true = DocuSign, false = built-in signature
  -- QuickBooks Online integration (optional — tenant-level add-on)
  qbo_access_token,                -- encrypted OAuth token (null if not connected)
  qbo_refresh_token,               -- encrypted OAuth refresh token
  qbo_realm_id,                    -- QuickBooks company ID
  -- Stripe integration
  stripe_customer_id,              -- Stripe customer ID for this tenant's billing
  stripe_connected_account_id,     -- Stripe Connect account (for receiving customer payments)
  plan, billing_status,
  timezone, locale,
  created_at, updated_at
)

users (
  id, tenant_id, email, phone, name, role,
  auth_uid,                        -- BetterAuth user ID
  avatar_url,
  active, created_at, updated_at
)

-- CRM — HubSpot Integration
-- HubSpot is the source of truth for customer contact data.
-- This table is a local cache synced from HubSpot, not manually entered.
-- Your team enters/edits customers in HubSpot. Your platform reads from here.
customers (
  id, tenant_id,
  hubspot_contact_id,              -- HubSpot record ID (the link between systems)
  -- Cached from HubSpot (updated by sync service every 10-15 min)
  name, email, phone, address, city, state, zip,
  lifecycle_stage,                 -- subscriber, lead, customer, etc. (from HubSpot)
  -- Platform-owned fields (NOT in HubSpot)
  pin,                             -- 4-digit PIN for customer portal (index.html)
  last_synced_at,                  -- when we last pulled from HubSpot
  created_at, updated_at
)

properties (
  id, tenant_id, customer_id,
  address, city, state, zip, lat, lng,
  lot_size_sf,
  -- Property measurements (sourced from Attentive takeoffs or in-house)
  measurement_source,          -- 'attentive', 'polygon', 'gps_trace', 'drone', 'manual'
  attentive_report_url,        -- link to stored Attentive export file
  drone_ortho_url,             -- link to stored drone orthomosaic in Cloud Storage
  -- 2D features (area-based)
  lawn_sf, lawn_perimeter_lf,
  mulch_bed_sf, mulch_bed_perimeter_lf,
  hedge_sf, hedge_perimeter_lf,
  driveway_sf, drive_lanes_sf,
  pavement_sf, sidewalk_sf,
  gravel_bed_sf, parking_spot_sf,
  -- Linear features
  hard_edge_lf, soft_edge_lf,
  -- Count features
  tree_count, irrigation_zones,
  -- Difficulty splits (stored as decimals, e.g., 0.80)
  lawn_easy_pct, lawn_med_pct, lawn_hard_pct,
  mulch_easy_pct, mulch_med_pct, mulch_hard_pct,
  hedge_easy_pct, hedge_med_pct, hedge_hard_pct,
  hard_edge_easy_pct, hard_edge_med_pct, hard_edge_hard_pct,
  soft_edge_easy_pct, soft_edge_med_pct, soft_edge_hard_pct,
  notes, status,
  created_at, updated_at
)

-- Bidding / Estimating
production_rates (
  id, tenant_id, division,        -- 'MNT', 'IRR', 'CON', 'ENH'
  service, equipment, unit,
  rate, easy_mult, medium_mult, hard_mult,
  created_at, updated_at
)

kits (
  id, tenant_id, division,        -- 'MNT', 'IRR', 'CON', 'ENH'
  name,
  material_cost, material_unit, coverage, coverage_unit,
  spread_rate, spread_unit,
  created_at, updated_at
)

bids (
  id, tenant_id, property_id, customer_id, created_by,
  division,                       -- 'MNT', 'IRR', 'CON', 'ENH'
  job_type,                       -- 'recurring' (contract with scheduled tickets) or 'work_ticket' (one-off job)
  bid_date, status, -- draft, sent, accepted, rejected, expired, finalized, revision
  property_type, -- residential, commercial
  contract_start_date, contract_end_date, contract_months,
  labor_rate, labor_markup, material_markup, sub_markup,
  travel_time_pct, cc_gross_up, -- boolean: include CC processing in price
  fixed_services_total,         -- tier 1: amortized monthly
  billed_separately_total,      -- tier 2: billed on completion
  recommended_total,            -- tier 3: optional add-ons
  internal_total, bid_total, profit, margin,
  monthly_payment,              -- fixed_services_total ÷ contract_months
  annual_increase_pct,          -- e.g., 3% auto-escalation
  notes, valid_until,
  created_at, updated_at
)

bid_services (
  id, bid_id,
  service_name,                 -- e.g., "Weekly Grounds Maintenance", "Shrub Pruning"
  billing_tier,                 -- 'fixed', 'billed_separately', 'recommended'
  frequency,                    -- number of visits/occurrences
  cost_per_occurrence,          -- customer-facing price per visit
  annual_cost,                  -- frequency × cost_per_occurrence
  description,                  -- service description for proposal PDF
  service_map_color,            -- color zone on aerial photo (green, pink, blue, yellow)
  is_subcontracted,             -- boolean
  sub_vendor, sub_cost, sub_markup,
  sort_order,
  created_at
)

bid_line_items (
  id, bid_service_id,           -- belongs to a bid_service (not directly to bid)
  item_name, difficulty,        -- e.g., "48" Mower Ride", "Easy"
  measurement_source,           -- Lawn, Hedge, Mulch Bed, Hard Edge, etc.
  quantity, unit,
  production_rate,
  hours_per_visit, additional_hours,
  total_hours,                  -- (hours_per_visit + additional_hours) × frequency
  labor_cost, billed_cost,
  -- Material fields (for mulch, pine straw, etc.)
  material_qty, material_unit, material_unit_cost,
  material_cost, material_markup, material_billed,
  sort_order,
  created_at
)

-- Contracts & Scheduling
contracts (
  id, tenant_id, property_id, customer_id, bid_id,
  division,                       -- 'MNT', 'IRR', 'CON', 'ENH'
  start_date, end_date, contract_months,
  status, -- active, paused, completed, cancelled
  monthly_payment,              -- fixed services amortized
  contract_value,               -- total bid value over the contract period
  annual_increase_pct,
  cancellation_notice_days,
  assigned_crew_id,
  preferred_day,                -- 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
  created_at, updated_at
)

contract_services (
  id, contract_id,
  service_name, billing_tier,   -- 'fixed', 'billed_separately'
  total_visits,
  schedule_type,                -- 'seasonal_mowing', 'simple'
  estimated_hours_per_visit,    -- from bid calculations
  line_items,                   -- JSON array of line item names for this service
  preferred_day, -- 0=Mon..6=Sun
  created_at
)

-- Crews
crews (
  id, tenant_id,
  name,                          -- 'MNT Crew 1', 'IRR Crew 1'
  division,                      -- MNT, IRR, CON, ENH
  status,                        -- active, inactive
  created_at, updated_at
)

crew_members (
  id, tenant_id, crew_id, user_id,
  role,                          -- leader, member
  status,                        -- active, inactive
  created_at, updated_at
)

-- Scheduled Events (Tickets)
scheduled_events (
  id, tenant_id, contract_id,
  property_id, assigned_crew_id,
  event_date, start_time, end_time,
  -- Bundled services for this visit
  services,                     -- JSON array: [{name, items: [{name, hours}], estimatedHours}]
  total_estimated_hours,         -- man-hours (production time, per-person rate)
  travel_estimated_hours,        -- man-hours for budgeted indirect/travel (total_estimated_hours × travel_time_pct)
  travel_time_pct,               -- the travel % used at generation time (snapshot)
  status,                       -- scheduled, completed, skipped, rescheduled
  -- Revenue tracking
  earned_value,                 -- billed cost of this ticket's services (calculated at generation)
  internal_cost,                -- labor + material cost at internal rates
  -- Completion data
  completed_date, completed_by,
  notes, completion_photo_url,
  -- Google Calendar sync (optional)
  google_calendar_event_id,
  color,
  created_at, updated_at
)

-- Time Tracking
time_entries (
  id, tenant_id, user_id,
  crew_id,                         -- which crew this entry belongs to
  entry_type, -- day_clock, job, indirect
  date,
  property_id, scheduled_event_id, -- null for day_clock and indirect
  -- Indirect time categorization (only used when entry_type = 'indirect')
  indirect_category,              -- travel, shop, dump_run, fuel, break, meeting, equipment, other
  indirect_from_property_id,      -- property just left (for travel entries)
  indirect_to_property_id,        -- property heading to (for travel entries)
  clock_in, clock_out, duration_minutes,
  crew_members_present,           -- JSON array of user_ids checked in for this entry
  services_completed, -- JSON array (for job entries)
  notes, lat_in, lng_in, lat_out, lng_out,
  created_at, updated_at
)

-- Signed Proposals (e-signature records)
signed_proposals (
  id, tenant_id, bid_id, customer_id, property_id,
  -- Signing method
  signing_method,                  -- 'built_in' or 'docusign'
  -- Built-in signature data
  signature_image_url,             -- PNG of drawn signature (stored in S3/Blob)
  signer_name,                     -- typed name confirmation
  signer_ip,                       -- IP address at time of signing
  signer_user_agent,               -- browser/device info
  signer_geolocation,              -- lat/lng if available
  consent_text,                    -- exact legal text they agreed to
  -- DocuSign data (when signing_method = 'docusign')
  docusign_envelope_id,            -- DocuSign envelope ID
  docusign_status,                 -- sent, delivered, completed, declined, voided
  -- Shared
  proposal_pdf_url,                -- the PDF they signed (stored in S3/Blob)
  signed_pdf_url,                  -- PDF with signature embedded + acceptance footer
  signed_at,                       -- timestamp of signature
  created_at
)

-- Invoicing — Landscape-Specific
-- Your platform owns invoicing entirely. QuickBooks receives finished invoices downstream.
-- The billing model is unique to landscape: fixed monthly payments that don't match work done,
-- billed-separately services on completion, optional/recommended services, annual escalation.
invoices (
  id, tenant_id, customer_id, property_id, contract_id,
  invoice_number,                    -- sequential: INV-001, INV-002, etc.
  invoice_date, due_date,
  billing_period_start,              -- e.g., 2026-04-01 (the month this invoice covers)
  billing_period_end,                -- e.g., 2026-04-30
  invoice_type,                      -- 'fixed_monthly' (maintenance), 'deposit' (project), 'final' (project), 'one_time'
  status,                            -- draft, sent, viewed, partial, paid, overdue, void
  subtotal, tax_rate, tax_amount, total,
  paid_amount, balance_due,
  -- Earned revenue context (internal tracking, not on the invoice itself)
  earned_revenue_this_period,        -- sum of completed ticket earned values in this billing period
  variance,                          -- earned - invoiced (positive = working ahead, negative = collecting ahead)
  -- Payment tracking
  payment_method,                    -- card, ach, check, cash (set when paid)
  stripe_checkout_session_id,        -- Stripe Checkout Session ID (if paid via Stripe)
  -- QuickBooks sync
  qbo_invoice_id,                    -- QBO invoice ID (null if not synced)
  qbo_synced_at,                     -- when pushed to QBO
  -- Pay Now link
  pay_link_token,                    -- unique token for the "Pay Now" URL (e.g., ?payInvoice=TOKEN)
  notes,
  created_at, updated_at
)

invoice_line_items (
  id, invoice_id,
  line_type,                         -- 'fixed_service', 'deposit', 'final_payment', 'material', 'credit', 'adjustment'
  description,                       -- e.g., "Monthly Landscape Maintenance (April 2026)"
  service_name,                      -- links to contract service for reporting
  contract_service_id,               -- FK to contract_services
  quantity, unit_price, amount,
  -- For project work: link to the specific ticket(s) if applicable
  scheduled_event_ids,               -- JSON array of ticket IDs (for billed-separately services)
  sort_order,
  created_at
)

-- Overhead & Company-Wide Financials
-- This is the missing piece in every landscape software: connecting job-level profitability
-- to company-wide P&L. The owner enters overhead costs once, the platform allocates them
-- across crews/properties, and suddenly you see TRUE profitability — not just direct margin.
overhead_categories (
  id, tenant_id,
  name,                            -- e.g., 'Truck Payments', 'Insurance', 'Shop Rent'
  category_group,                  -- 'vehicle', 'facility', 'insurance', 'equipment', 'office', 'other'
  monthly_amount,                  -- fixed monthly cost (e.g., $2,400 for truck payments)
  allocation_method,               -- 'per_crew', 'per_revenue', 'per_hour', 'fixed'
  -- Allocation rules:
  --   per_crew: split evenly across active crews (truck payment → divided by # crews)
  --   per_revenue: allocated proportional to revenue generated (insurance → higher revenue properties bear more)
  --   per_hour: allocated proportional to labor hours (fuel → more hours = more fuel)
  --   fixed: not allocated — company-level only (office rent)
  notes,
  active,                          -- boolean: include in current period calculations
  qbo_expense_category,            -- optional: maps to QBO expense category for reconciliation
  created_at, updated_at
)

-- Monthly overhead snapshots (locks in the numbers each month for historical accuracy)
overhead_snapshots (
  id, tenant_id,
  period_month,                    -- '2026-04' (year-month)
  snapshot_data,                   -- JSON: [{category_id, name, amount, allocation_method, allocated_amounts: {crew_id: $, ...}}]
  total_overhead,                  -- sum of all categories for this month
  created_at
)

-- Communication
-- Messages/communication history lives in HubSpot (emails, calls, notes, timeline).
-- When your platform sends an SMS or email (via Twilio/SendGrid), log it back
-- to HubSpot as a timeline event so the full history stays in one place.
-- No local messages table needed.

-- Service Requests (replaces current Google Sheets storage)
service_requests (
  id, tenant_id, customer_id, property_id,
  category, message, urgency,
  status, -- open, in_progress, completed, cancelled
  assigned_to, -- user_id
  photos, -- JSON array of Cloud Storage URLs
  acknowledged_at, acknowledged_by,
  completed_at, completed_by, completion_photo_url,
  source,  -- 'customer' (from index.html) or 'internal' (from crew.html Report Issue)
  created_at, updated_at
)

-- Reports (site reports, before & after reports)
reports (
  id, tenant_id, property_id,
  report_type, -- site_report, before_after
  created_by, report_date,
  data, -- JSON blob with report-specific fields
  photos, -- JSON array of Cloud Storage URLs
  pdf_url,
  created_at
)

-- Service Offers (upsells embedded in weekly reports and site reports)
service_offers (
  id, tenant_id, property_id, customer_id,
  report_id,                      -- links to reports table (weekly report or site report)
  report_type,                    -- 'weekly_report' or 'site_report' (denormalized for fast queries)
  -- What's being offered
  service_name,                   -- e.g., "Mulch Refresh", "Hedge Trimming", "Spring Seasonal Color"
  description,                    -- customer-facing description of the work
  quantity,                       -- e.g., 12 cubic yards, 1 service visit
  unit,                           -- e.g., "CY", "visit", "flat"
  price,                          -- customer-facing price
  photos,                         -- JSON array of photo URLs (crew photos showing why the service is needed)
  crew_notes,                     -- internal notes from crew ("mulch beds are bare, customer asked about it")
  -- Approval
  status,                         -- 'pending', 'approved', 'declined', 'expired'
  approval_token,                 -- unique token for customer approval link (no login required)
  approved_at,                    -- timestamp of customer approval
  approved_by_name,               -- name entered by customer when approving
  approved_ip,                    -- IP address at time of approval
  declined_at,
  expires_at,                     -- auto-expire after 30 days if no response
  -- Fulfillment
  converted_to,                   -- 'ticket' or 'contract_service' (what it became after approval)
  ticket_id,                      -- if converted to a one-time scheduled event
  contract_service_id,            -- if added to existing contract as recurring service
  scheduled_date,                 -- when the work is scheduled (set by office after approval)
  completed_at,
  created_by,                     -- user_id of crew member or manager who created the offer
  created_at, updated_at
)

-- Payments
payments (
  id, tenant_id, invoice_id,
  amount, method,          -- card, ach, check, cash
  check_number,            -- null unless method = check
  stripe_checkout_session_id,  -- null unless method = card/ach (from Stripe webhook)
  stripe_payment_intent_id,    -- Stripe payment intent ID (from webhook event data)
  status,                  -- completed, pending, failed
  received_date, notes,
  created_by,              -- who recorded it (for manual entries, null for auto/Stripe)
  qbo_payment_id,          -- QBO payment ID (null if not synced)
  created_at
)
```

### Key Relationships
```
HubSpot Contact → synced to local Customer (cache)
Customer → has many Properties (properties are platform-owned, not in HubSpot)
Property → has many Contracts, Bids, Service Requests, Reports
Property → has measurements, difficulty splits, equipment splits (all platform-owned)
Bid → can convert to Contract (accepted bid → signed proposal → active contract)
Bid → has Signed Proposal (built-in signature or DocuSign envelope)
Contract → has many Contract Services → generates Scheduled Events (Tickets)
Contract → assigned to a Crew (e.g., "MNT Crew 1")
Crew → has many Crew Members (leader + members)
Scheduled Event → bundles multiple services for one property visit
Scheduled Event → links to Time Entries (actual hours)
Time Entries → belong to Crew, track crew_members_present per entry
Time Entries + Contract Services → generate Invoice Line Items
Invoice → sent to Customer (via Stripe)
Service Requests → linked to Property, surfaced to crew on arrival (smart prompt)
Report → has many Service Offers (recommended services embedded in customer-facing reports)
Service Offer → approved by customer → converts to Scheduled Event (one-time) or Contract Service (recurring)
```

### The Core Pipeline
```
HubSpot Contact → Customer (cache) → Property → Bid → Proposal → Sign → Contract → Schedule → Time Entry → Invoice → Financial Report
                                                              ↑                ↓           ↓           ↓             ↓           ↓
                                                    Built-in sig or      Contract     Scheduled    Time Entries   Earned vs.  QuickBooks
                                                    DocuSign (optional)  Services      Events      (day + job)    Invoiced     sync
                                                                              ↓           ↓           ↓             ↓
                                                                       Visit counts   Crew route   Actual hours   Revenue
                                                                       + schedule     + earned     vs. estimated  recognition
                                                                         type          value       (feedback loop)  by month

Events logged back to HubSpot timeline ← Contract signed, job completed, invoice sent, payment received
Payments processed through Stripe ← Webhooks auto-mark invoices paid
```

---

## The Estimate → Ticket → Schedule → Time Clock Pipeline

This is the central data flow that connects bidding to daily crew operations. Each step feeds the next with minimal manual entry.

### Step 1: Contract Activation (estimate.html / Management Platform)

When an estimate is accepted, the "Accept Estimate → Create Contract" action:
1. Locks the estimate (prevents edits — status becomes "Finalized")
2. Creates a contract record with property, customer, crew, dates, monthly payment
3. Creates contract_services — one per service with visit count and **schedule type**
4. Generates scheduled event tickets distributed across the contract period
5. Calculates **earned value** per ticket (the billed cost of the items on that ticket)
6. Optionally syncs events to Google Calendar

**Revision workflow (re-finalization):** If a finalized estimate is reopened and edited, the status transitions to "Revision" instead of Draft. The estimate retains its `contractId` link. When the user clicks "Update Contract," the system:
1. Updates the existing contract row (crew, dates, payment) — no duplicate contract created
2. Deletes future scheduled tickets (status='scheduled' AND eventDate > today)
3. Regenerates future tickets from the updated estimate
4. Preserves all completed, skipped, and today's tickets untouched
5. Sets status back to "Finalized" and increments `revisionCount`

| Ticket Status | Date | On Revision |
|---|---|---|
| completed | Any | NEVER touched |
| skipped | Any | NEVER touched |
| scheduled | Today | Preserved (strict `>` date comparison) |
| scheduled | Tomorrow+ | Deleted and regenerated |

**Item-level scheduling:** Each line item within a service can have its own visit count (`itemVisits`). If not set, it follows the service's visit count. This means a "Weekly Grounds Maintenance" service (42 visits) can contain Blade Edge at 52 visits (weekly all year) and Weed Control at 12 visits (monthly). Each ticket only lists the items actually due that day.

**Schedule types determine how visits are distributed:**

| Schedule Type | Rule | Example |
|---------------|------|---------|
| `seasonal_mowing` | Weekly Apr–Oct, biweekly Nov–Mar; fills dormant gaps for higher targets (52), trims dormant for lower | Mowing, Blowing, Detail Mowing, Trash Pickup |
| `weekly` | Every week, all year (~52 visits) | Blade Edge, Blowing (when set to 52 visits) |
| `simple` | Evenly distributed across contract, snapped to preferred day | Hedge Trimming (12/yr), Irrigation (12/yr), Mulch (1/yr) |

**Mowing seasonal rule** for a 12-month contract starting April 1:
- April–October (30 weeks): ~30 weekly visits
- November–March (22 weeks): ~11 biweekly visits
- Total: ~41 visits (matches the 42-visit default template)

**Co-scheduling**: Services that follow the mowing schedule (Blowing, Detail Mowing, Trash Pickup) share the same dates and are bundled into the same ticket. One visit to a property = one ticket with multiple services.

### Step 2: Ticket Bundling

Tickets group all services scheduled for the same date at the same property into a single stop. Each ticket lists only the items actually due that day:

```
Ticket: TKT-2026-04-01-123
Property: 123 Main St
Date: April 1, 2026 (weekly season)
Services:
  - Weekly Grounds Maintenance (1.5 hrs)
      → 48" Mower Ride (0.8 hrs)
      → 21" Mower Walk (0.2 hrs)
      → Blade Edge (0.15 hrs)
      → String Trimmer (0.1 hrs)
      → Weed Control Liquid (0.25 hrs)
  - Blowing (0.3 hrs)
      → Backpack Blowing (0.3 hrs)
Total Estimated: 1.8 man-hours (production)
Travel Budget: 0.54 man-hours (30% of production)
Earned Value: $142.50
Status: scheduled

Display for 2-person crew:
  Office sees:    "54m · 1.8 mh"  (crew-hours + man-hours)
  Crew sees:      "54m"            (crew-hours only — what matters on-site)
```

```
Ticket: TKT-2026-01-15-123
Property: 123 Main St
Date: January 15, 2026 (biweekly season — no mowing this week)
Services:
  - Weekly Grounds Maintenance (0.4 hrs)
      → Blade Edge (0.15 hrs)    ← 52 visits, scheduled every week
      → String Trimmer (0.1 hrs)
      → Weed Control Liquid (0.15 hrs)
  - Blowing (0.3 hrs)
      → Backpack Blowing (0.3 hrs)
Total Estimated: 0.7 man-hours (production)
Travel Budget: 0.21 man-hours (30% of production)
Earned Value: $52.80
Status: scheduled
```

### Step 2.5: Earned Value Calculation

Each ticket carries a dollar value representing the revenue earned when the crew completes it. This is calculated at ticket generation time using the bid's rates and markups:

```
For each item on the ticket:
  item_hours = quantity / production_rate × complexity_factor
  item_labor_cost = item_hours × labor_rate × (1 + travel_pct)
  item_billed = item_labor_cost × (1 + labor_markup_pct)
  (+ material cost × material markup if applicable)

ticket_earned_value = sum of all item billed amounts
```

The total earned value across all tickets for a contract equals the contract's total bid value. But the distribution is uneven — summer tickets with full mowing cost more than winter tickets with just edging and blowing.

**Why this matters:**
- **Invoiced revenue** = flat monthly payment ($1,200/month). Predictable for the customer.
- **Earned revenue** = sum of completed ticket values that month. Reflects actual work performed.
- Over the full contract, total earned = total invoiced = contract value.
- But month-to-month they diverge, revealing the true financial picture:

| Month | Tickets | Earned | Invoiced | Difference |
|-------|---------|--------|----------|------------|
| April | 5 | $1,425 | $1,200 | Working ahead |
| May | 4 | $1,180 | $1,200 | About even |
| July | 5 | $1,520 | $1,200 | Working well ahead |
| January | 2 | $680 | $1,200 | Collecting for future work |
| **Year** | **~45** | **$14,400** | **$14,400** | **Balanced** |

This earned-vs-invoiced tracking enables:
- **Deferred revenue reporting**: How much have you collected but not yet earned?
- **Property-level profitability**: Is earned revenue exceeding invoiced? You're underwater.
- **Cash flow forecasting**: Heavy earning months vs. light months.
- **Contract valuation**: If a customer cancels mid-contract, you know exactly how much work remains unearned.

### Step 3: Crew Schedule (crew.html / Crew App) — ✅ Built

Tickets appear as the crew's daily route — ordered list of property stops with services, estimated hours, and status. The crew leader sees their full day at a glance.

**Implementation:** `getCrewSchedule(phone, date)` endpoint authenticates crew leader via Crew Members sheet, resolves crew name (e.g., "MNT Crew 1"), returns all active crew members, today's tickets filtered by assignedCrew + eventDate, and any existing time entries for resume support.

### Step 4: Time Clock — ✅ Built (GPS pending)

Three levels of tracking:
- **Day clock**: Clock in/out for the workday (runs at top of schedule tab)
- **Job clock**: Clock in/out per property stop (tracks actual time vs. estimated per ticket)
- **Indirect time**: Everything between job clocks — automatically captured, optionally categorized

GPS captured at clock-in/out for verification.

**Man-hours vs. crew-hours (two-tier division):** Production rates in the item catalog are per-person (man-hours). Tickets store `totalEstHours` as man-hours and `travelHours` as budgeted indirect man-hours. At display time, values are divided by crew count to show crew-hours — the actual wall-clock time expected. **Property-group level** uses full crew size (`getCrewSize()`) because that's the site visit duration. **Ticket level** (expanded stop card target, timer-turns-red threshold, clock-out modal) uses `at.assignedMembers.length` because only assigned crew are working that ticket. A 4-person crew with 2 assigned to a 1 man-hour ticket sees "30m" target, not "15m". The stored man-hours are never modified — the division happens only in the UI.

**Budgeted vs. actual indirect time:** Each ticket now carries `travelHours` (production man-hours × travel %). The day summary compares actual indirect time (gaps between job clocks) against budgeted indirect time (sum of `travelHours` ÷ crew size). This gives crew leaders immediate feedback: "50m indirect / 36m budget — 14m over."

**How indirect time works:**

The day clock runs continuously. Job clocks mark direct (billable) time on properties. The gaps between job clocks are **indirect time** — automatically calculated as the difference.

```
6:30 AM  Day clock in (at shop)
6:30–7:00  Indirect: shop (load truck, morning meeting)
7:00 AM  Job clock in — 123 Main St
8:15 AM  Job clock out — 123 Main St (1h 15m direct)
8:15–8:35  Indirect: travel (GPS shows driving)
8:35 AM  Job clock in — 456 Oak Ave
9:50 AM  Job clock out — 456 Oak Ave (1h 15m direct)
9:50–10:20  Indirect: dump run
10:20 AM  Job clock in — 789 Pine Ln
...
4:00 PM  Day clock out

Day summary:
  Direct time:    6h 15m (on properties)
  Indirect time:  3h 15m (travel, shop, dump, break)
  Total day:      9h 30m
  Direct %:       66%
```

**Day summary with budget comparison (2-person crew):**
```
Day Summary
Crew (2):       Jack, Mike
Stops:          6 of 6
─────────────────────────
Direct Time:    1h 40m / 2h budget     20m under
Indirect Time:  50m / 36m budget        14m over
─────────────────────────
Total Day:      2h 30m / 2h 36m         6m under
Direct %:       67%
```

Crew leaders can optionally tap a category when starting travel or non-job time (travel, shop, dump run, fuel, break, meeting, equipment, other). If they don't categorize, it's still captured as uncategorized indirect time — the total is always accurate even without categories.

**Indirect time categories:**
| Category | Description |
|----------|-------------|
| `travel` | Driving between properties |
| `shop` | Morning load, end-of-day cleanup, organizing |
| `dump_run` | Hauling debris to dump/transfer station |
| `fuel` | Fueling trucks/equipment |
| `break` | Lunch, rest breaks |
| `meeting` | Morning meeting, training, safety talk |
| `equipment` | Equipment maintenance, repair, sharpening |
| `other` | Anything else (add note) |

**Why this matters for profitability:**
- A crew with 70% direct time is more profitable than one at 55% — same labor cost, more billable output
- Travel time between properties reveals route inefficiency
- Shop time reveals morning routine problems (late starts, slow loading)
- Dump run frequency reveals whether you're allocating enough trailer capacity
- This data feeds into the estimating tool's travel time percentage — currently a guess, eventually data-driven

### Step 5: Feedback Loop

After collecting time data:
- Actual hours per property/service compared against estimated hours from the bid
- Properties consistently over budget → crew is slower than estimated, or difficulty split was wrong
- Properties consistently under budget → opportunity to tighten the bid, or crew is efficient
- This data feeds back into the production rate database over time, making future bids more accurate

---

## Crew App — Tab Structure

### Four-Tab Bottom Navigation
```
┌──────────┬──────────┬──────────┬──────────┐
│ Schedule │ Requests │  Report  │ Reports  │
│  (home)  │          │  Issue   │          │
└──────────┴──────────┴──────────┴──────────┘
```

### Schedule Tab (Built — Default Home Screen)

**Daily crew check-in flow:**
1. Crew leader opens app → sees today's date, stop count, estimated hours
2. Taps "Start Day" → crew check-in modal shows all active members with checkboxes
3. Checks off who's working today → taps "Start Day" → day clock begins
4. Day clock banner (dark, always visible): running timer + crew names + "End Day" button

**Stop cards (ordered route):**
- Numbered cards with property address (street only), service list, estimated time (crew-hours, adjusted for crew size)
- Status indicators: ○ pending, ▶ next (with Start Job button), ✅ completed (green, with actual time), ⊘ skipped
- Only the next available stop shows "Start Job" + "Skip this stop" buttons
- Completed cards show actual time vs. estimated with color coding

**Job clock flow:**
1. Crew leader taps "Start Job" → blue active-job banner appears with property name and running timer
2. **Request alert check**: app scans for open customer requests at this property address
   - Yellow banner shows each request with message, customer name, date
   - Two buttons per request: "Handle It" (marks In Progress) or "Office" (dismisses, leaves for office)
3. Crew completes work → taps "Complete" in banner → Complete Job modal:
   - Est vs. Actual time comparison (green if under, red if over)
   - Service checklist (pre-checked)
   - Optional notes field
4. Taps "Complete" → ticket marked completed, time entry saved, next stop activates

**End of day:**
1. All stops completed or skipped → crew leader taps "End Day"
2. Day Summary modal: crew members (with count), stops completed, direct time vs. budget, indirect time vs. budget, total hours vs. budget, over/under badges per category, direct %
3. Indirect time = total day time minus sum of job times (auto-calculated)
4. Budgeted indirect = sum of `travelHours` from today's tickets ÷ crew size

**Resume support:** If app is closed mid-day and reopened, `loadSchedule()` checks for open time entries (day_clock without clockOut, job without clockOut) and resumes the active timers from the saved timestamps.

**Crew naming:** Crews are simply "Crew 1", "Crew 2", "Crew 3", etc. Contracts and tickets reference the crew name, not the individual leader. Crew names are division-agnostic by default — any crew can work any division's tickets.

**Optional division specialization:** A crew can optionally be tagged with a `divisionFilter` (e.g., `['MNT']` or `['MNT', 'ENH']`). When set, the schedule builder only assigns that crew tickets from the specified division(s), and the crew app filters their daily route accordingly. When `divisionFilter` is null (the default), the crew sees all assigned tickets regardless of division. This supports the full spectrum:
- **Small company (today)**: Crew 1, Crew 2, Crew 3 — all division-agnostic. A crew's Monday route might mix MNT mowing, an IRR repair, and an ENH mulch job. Everyone does everything.
- **Growing company**: Crew 1 and Crew 2 stay general. Crew 3 gets tagged `['IRR']` because they're the irrigation techs. They only see irrigation tickets. The manager can still override and assign them an MNT ticket if needed.
- **Large company (future multi-tenant customers)**: A customer might want dedicated division crews — "MNT Crew 1", "MNT Crew 2", "IRR Crew 1". They rename their crews and set `divisionFilter` per crew. The system enforces it in scheduling but the crew leader can still be overridden by a manager for edge cases.

The crew name is always freeform text — if a company wants to call them "MNT Crew 1" they can, but the system doesn't derive division from the name. Division filtering is a separate data field.

**Reporting**: Production rate analysis, earned revenue, and time tracking all segment by the ticket's division, not the crew. A crew working MNT tickets in the morning and an ENH work ticket in the afternoon generates separate production data for each division automatically.

### Requests Tab (Existing System — Relocated)
- The current crew.html dashboard: open/completed request filtering, request cards, detail view, status updates, completion photos
- Customer requests from index.html + internal tickets from crew.html "Report Issue"
- No changes to the existing request flow — it just moves from being the home screen to its own tab

### Report Issue Tab (Existing)
- Crew-submitted internal tickets with property search, photo capture, message

### Reports Tab (Existing + Service Offers)
- Quick Photos batch upload, Site Report wizard, Before & After reports — unchanged
- **NEW: Service Offers in Site Reports** — after completing a site report, crew can attach recommended services (e.g., "Mulch beds need refresh — 12 CY @ $85/CY = $1,020"). Crew takes a photo of the area, selects a service from the catalog, enters quantity and notes. The offer is embedded in the site report PDF and sent to the customer with an "Approve" button.
- **NEW: Service Offers in Weekly Reports** — manager or crew leader can attach service recommendations when generating weekly reports. Same flow: pick service, set price, add photo/notes. Customer sees the offer inline in their weekly report email with one-tap approval.

---

## Google Calendar Integration (Optional Sync)

Google Calendar is a **sync target, not the source of truth**. The schedule lives in the database (Google Sheets for prototype, PostgreSQL for production). Calendar gets a copy for crew convenience.

### What Calendar Provides
- Crew leader sees tomorrow's route on their iPhone lock screen without opening the app
- Push notifications before each stop (configurable: 15 min, 30 min, etc.)
- Manager gets a bird's-eye weekly view of all crews in Calendar's native color-coded UI
- Shared calendars viewable by office staff in Google Workspace
- Route visible alongside personal calendar events

### What Calendar Cannot Do
- Time clock in/out (no API for this)
- Actual vs. estimated hours tracking
- Service completion checklists
- Smart customer request prompts on arrival
- Ticket status management (skip, reschedule, complete)
- Bundling multiple services into one stop display
- Offline time tracking

### Implementation
**Prototype (current stack):** Apps Script `CalendarApp.createEvent()` called when tickets are generated. Event IDs stored on ticket records for update/delete sync.

**Production:** Google Calendar API with service account. Called from `server/src/services/calendar.ts`.

### Calendar Event Format
- **Title**: "🏡 123 Main St — Mowing + Blowing"
- **Time**: Based on route order and estimated hours
- **Location**: Property address (enables Google Maps navigation)
- **Description**: Services list, estimated hours, customer contact info
- **Color**: By crew assignment

### Sync Rules
| Action | Calendar Effect |
|--------|----------------|
| Tickets generated | Events created on crew's calendar |
| Job completed | Event color → green, description updated with actual time |
| Job skipped | Event color → gray, "SKIPPED" in title |
| Job rescheduled | Old event deleted, new event on new date |
| Contract cancelled | All future events deleted |

### Calendar is Phase B — Not a Blocker
Build the schedule tab and time clock in crew.html first (core value). Add Calendar sync later as a "Sync to Google Calendar" button when creating a contract. Crew leaders who want it get it; those who just use crew.html don't need it.

---

## Feature Modules & Phased Roadmap

Build in this order. Each phase builds on the previous one and delivers usable value.

> **Important phasing note:** The bidding/estimating tool (estimate.html) is already substantially built as a prototype for the **Maintenance (MNT) division**. The three remaining divisions (Irrigation, Construction, Enhancement) will be added by extending the item catalog, service catalog, and takeoff sections — the calculation engine, billing tiers, template system, and ticket generation are shared. The roadmap reflects this — Phase 2 focuses on the Estimate → Ticket → Schedule pipeline rather than rebuilding the estimating UI, and the React migration of the estimating tool happens alongside other phases.

### Phase 0: Foundation (Weeks 1-3)
**Goal: Set up the infrastructure and migrate existing features**

- [ ] Choose cloud provider (AWS or Azure) and set up project structure
- [ ] Set up monorepo with Turborepo: `packages/shared`, `packages/ui`, `packages/calculation-engine`, `apps/platform`, `apps/crew`, `server/`
- [ ] Set up TypeScript across all packages with shared `tsconfig.base.json`
- [ ] Set up BetterAuth (email + phone login, multi-tenant aware)
- [ ] Create the PostgreSQL database with core tables (tenants, users, customers, properties)
- [ ] **Enable RLS immediately** — create policies for all tables scoped to `tenant_id`
- [ ] Build the Express + TypeScript API skeleton with auth middleware and RLS tenant context
- [ ] Set up the React + Vite + Tailwind + TypeScript frontend apps with dual-app structure
- [ ] Build the login/signup flow (routes to Platform or Crew App based on user role)
- [ ] Deploy frontend to static hosting, API to container service
- [ ] Set up CI/CD (GitHub Actions → auto-deploy on push)
- [ ] Migrate existing property data from Google Sheets to PostgreSQL
- [ ] Extract calculation engine from estimate.html into `packages/calculation-engine` (TypeScript, tested against prototype outputs)
- [ ] Recreate crew.html as the Crew App (mobile-first — same functionality, React architecture, four-tab structure)
- [ ] Recreate the Management Platform dashboard (desktop-first — admin view of requests, crew, properties)
- [ ] Keep index.html running for customer service requests (POST to new API instead of Apps Script)

**Deliverable:** Both apps work on the new stack. Crew members open the Crew App on their phone, managers open the Platform on their laptop. Same data, different experiences.

### Phase 1: Scheduling & Time Clock (Weeks 4-7)
**Goal: Daily crew operations — the features they use every day**

#### Schedule Tab + Time Clock (Crew App)
- [ ] Build the Schedule tab as the Crew App home screen (today's route)
- [ ] Day clock: clock in/out for the workday with running timer at top of schedule
- [ ] Job clock: start/stop per property stop, GPS capture at clock-in/out
- [ ] **Indirect time tracking**: gaps between job clocks automatically captured as indirect time
- [ ] **Indirect time categorization**: optional quick-tap categories (travel, shop, dump run, fuel, break, meeting, equipment, other)
- [ ] Property stop cards: address, bundled services, estimated hours, status
- [ ] Job completion flow: service checklist, optional completion photo, notes
- [ ] Actual vs. estimated time display after completing each job
- [ ] **Day summary**: direct time, indirect time (by category), total hours, direct %
- [ ] Schedule summary: total estimated, completed, remaining
- [ ] Smart request prompt: check for open customer requests when starting a job
- [ ] Offline support: cache today's route in localStorage, queue time entries for sync

#### Contract & Ticket Generation (Management Platform)
- [ ] "Accept Estimate" action on bid summary → creates contract
- [ ] Mowing seasonal schedule: weekly year-round, trims winter dates first for lower targets
- [ ] Simple schedule distribution for all other services
- [ ] Ticket bundling: co-scheduled services grouped into single property stops
- [ ] Schedule preview before generation (show ticket counts by service)
- [ ] Crew assignment and preferred day selection
- [ ] Save contracts and tickets to database

#### Route Management (Management Platform)
- [ ] Weekly route view — list of stops per day per crew
- [ ] Reschedule: move a ticket to a different date
- [ ] Skip: mark a visit as skipped (rain day, gate locked, etc.)
- [ ] Bulk skip: mark all tickets for a date as skipped (weather day)
- [ ] Timesheet review for managers

#### Google Calendar Sync (Optional)
- [ ] Create calendar events when tickets are generated
- [ ] Update events on completion/skip/reschedule
- [ ] Delete future events on contract cancellation

**Deliverable:** Estimates convert to contracts with auto-generated schedules. Crews clock in, follow their route, clock out per job. Managers build schedules and review timesheets. Optionally synced to Google Calendar.

### Phase 2: Bidding & Estimating (Weeks 8-10)
**Goal: Migrate the estimating tool to the new stack**

> The Maintenance (MNT) calculation engine and UX already exist in estimate.html. This phase migrates them to React while preserving all business logic, then extends the system to support all four divisions.

#### Multi-Division Estimating
- [ ] Division selector on new estimate creation (MNT, IRR, CON, ENH)
- [ ] Division-specific item catalogs with their own production rates
- [ ] Division-specific service catalogs with default visits, billing tiers, and line items
- [ ] Division-specific takeoff sections (MNT: Lawn/Edge/Mulch/Hedge; IRR: Zones/Heads/Pipe; CON: Excavation/Grading/Materials; ENH: Planting/Mulch/Features)
- [ ] Division-specific templates (e.g., "Standard Residential Maintenance", "Irrigation Install", "Paver Patio")
- [ ] Division filter on estimates list, contracts list, and financial reports
- [ ] Each estimate belongs to exactly one division; a property can have estimates across multiple divisions

#### Property Measurements — Phased Approach
> Start with Attentive.ai takeoffs, evolve to in-house measurement tools over time.

**Phase 2a — Attentive Takeoffs (start here)**
- [ ] Upload Attentive.ai Excel export for a property → auto-parse all measurements
- [ ] Extract: lot size, lawn SF, mulch bed SF, hedge SF, hard/soft edge LF, tree count, all perimeters
- [ ] Store parsed measurements on the property record with `measurement_source = 'attentive'`
- [ ] Store the original Attentive file in Cloud Storage, link on property record
- [ ] Difficulty split UI: assign Easy/Medium/Hard percentages per measurement category (default 80/10/10)
- [ ] Manual override: edit any measurement after import
- [ ] Manual entry: for properties without an Attentive report, enter measurements by hand (`measurement_source = 'manual'`)

**Phase 2b — In-House Measurement Tools (future)**

Three measurement methods that can be used independently or layered together:

**Method 1: Map-Based Polygon Tool (desktop)**
- [ ] Draw polygons on satellite imagery to measure areas (SF) and edges (LF)
- [ ] Integration with Google Maps or Nearmap for aerial imagery
- [ ] Auto-detect lawn, beds, hardscape from imagery (AI-assisted)
- [ ] Segment-level difficulty tagging (draw on the map to mark easy/medium/hard zones)
- [ ] Snap-to-edge for clean polygon drawing
- [ ] Layer toggle: show/hide lawn, beds, hardscape, edges independently

**Method 2: GPS Walk-Trace (crew app)**
- [ ] Crew walks a property boundary, bed edge, or hedge line with their phone
- [ ] App records GPS path in real-time, shows trace on map
- [ ] Calculates area (SF) for closed polygons, length (LF) for open paths
- [ ] Assign each trace to a measurement category (lawn, mulch bed, hedge, edge)
- [ ] Multiple traces per property, merged into total measurements
- [ ] Accuracy: ~1-3 ft with phone GPS, acceptable for estimating

**Method 3: Drone Mapping (high-detail properties)**
- [ ] Fly property with DJI or similar drone, capture overlapping photos
- [ ] Upload photos → photogrammetry pipeline generates orthomosaic (stitched top-down map) and elevation model
- [ ] Options for processing: DroneDeploy, Pix4D, OpenDroneMap (open-source, self-hosted)
- [ ] Ortho map becomes the base layer in the polygon tool — far higher resolution than satellite imagery
- [ ] AI-assisted feature detection on ortho maps: identify lawn, beds, trees, hardscape, pavement from drone imagery
- [ ] Elevation model enables slope/grade analysis (relevant for Construction division — drainage, grading)
- [ ] Measure tree canopy coverage from overhead (improves Leaf Cleanup estimates)
- [ ] Before/after comparison: fly the same property months apart to track landscape changes
- [ ] Store ortho maps in Cloud Storage, linked to property record
- [ ] `measurement_source = 'drone'` on property record

**Combining sources:**
- [ ] Attentive.ai for initial takeoff (fast, no site visit needed)
- [ ] GPS walk-trace to verify or supplement in the field
- [ ] Drone for high-value commercial properties where accuracy justifies the flight time
- [ ] Any source can override any other — most recent measurement wins, with full history
- [ ] `measurement_source` tracks which method produced each measurement: 'attentive', 'polygon', 'gps_trace', 'drone', 'manual'
- [ ] Measurement history: track changes over time with source and date

#### Bid Builder (React Migration)
- [ ] Desktop-first spreadsheet-style table (preserving estimate.html's three-panel layout)
- [ ] Extract calculation functions to `packages/calculation-engine/src/bidCalculator.ts`
- [ ] Extract takeoff pipeline to `packages/calculation-engine/src/takeoffService.ts`
- [ ] Migrate item catalog to `production_rates` table with seed data
- [ ] Migrate service catalog to service templates
- [ ] Test calculation accuracy against estimate.html outputs
- [ ] Real-time calculation engine (internal costs, markups, profit, margin)
- [ ] Three-tier billing structure (Fixed/Billed Separately/Recommended)
- [ ] Template save/load
- [ ] Credit card gross-up toggle

#### Proposals & Signing
- [ ] PDF proposal generation (Cloud Function or API route)
- [ ] Three-tier pricing page, payment schedule, service descriptions, terms & conditions
- [ ] **Built-in signature capture** (see E-Signature section below)
- [ ] Bid → Contract conversion (accepted bid creates contract with visit counts, schedule types, billing tier assignments, and payment schedule automatically)
- [ ] Saved bids, duplicating, versioning

#### E-Signature — Built-In + Optional DocuSign

**Built-in signing flow (default for all tenants, zero cost):**

The customer receives an email or SMS with a "Review & Sign" link. They open it in the customer portal (no account needed — token-based access). The flow:

1. **Review** — proposal displays with three-tier pricing, payment schedule, service descriptions, terms & conditions. Clean, mobile-friendly layout. Customer scrolls through everything.
2. **Sign** — canvas-based signature pad at the bottom. Customer draws their signature with a finger (phone), stylus (tablet), or mouse (desktop). The physical act of signing matters — it creates psychological commitment and feels official.
3. **Confirm** — "I agree to the terms above" checkbox + "Submit Signed Agreement" button.
4. **Record** — platform captures: drawn signature (as PNG), timestamp, IP address, user agent, geolocation (if available). Generates a signed PDF with the signature image embedded, acceptance footer with legal record, and stores it in file storage.
5. **Trigger** — signed proposal auto-converts to active contract → tickets generate → lifecycle stage updates in HubSpot → welcome email sends. Zero manual steps.

The signature pad component uses HTML5 Canvas (or a library like `signature_pad`). It supports touch, pen, and mouse input. The drawn signature is stored as a base64 PNG and embedded into the finalized PDF. This is legally valid under ESIGN Act and UETA for service agreements — the combination of drawn signature + timestamp + IP + consent checkbox creates a defensible record.

**Optional DocuSign add-on (tenant-level setting):**

For companies that want the DocuSign brand, audit trail, or are doing higher-value construction contracts where additional legal formality matters:

1. Tenant admin goes to Settings → Integrations → DocuSign
2. Clicks "Connect DocuSign" → OAuth flow → done
3. A toggle appears: "Use DocuSign for proposal signing" (on/off)
4. When enabled: proposal PDF is pushed to DocuSign via API → customer signs in DocuSign's embedded experience → webhook fires on completion → same auto-conversion pipeline triggers
5. When disabled (or not connected): built-in signing flow is used (default)

The platform doesn't care which path was taken — the outcome is the same: a signed PDF, a timestamp, and a contract activation trigger. DocuSign is a drop-in enhancement, not a dependency.

**Signature component (`packages/ui/SignaturePad/`):**
- Touch, pen, and mouse input on HTML5 Canvas
- "Clear" button to retry
- Responsive — works full-width on phone, constrained on desktop
- Exports signature as base64 PNG
- Dark stroke on white background for clean embedding into PDFs
- Shared between customer portal (proposal signing) and crew app (future: customer sign-off on completed work)

**Deliverable:** Full estimating tool on the new React/PostgreSQL stack with feature parity to estimate.html for Maintenance. All four divisions supported with division-specific catalogs and takeoffs sharing the same calculation engine. Upload an Attentive report, build a bid in minutes, generate a PDF proposal, send it for signing (built-in signature or DocuSign), and auto-convert signed proposals into scheduled contracts with zero manual steps.

### Phase 3: HubSpot Integration & Customer Communication (Weeks 11-14)
**Goal: Connect HubSpot as the CRM, add customer communication**

> You are not building a CRM. HubSpot is the CRM. Your platform integrates with it the same way it integrates with Stripe for payments — let the best-in-class tool own what it's best at.

#### HubSpot Integration
- [ ] OAuth flow: tenant admin connects their HubSpot account (stores tokens on tenant record)
- [ ] Sync service: poll HubSpot contacts every 10-15 minutes, upsert into local `customers` cache table
- [ ] Sync fields: name, email, phone, address, city, state, zip, lifecycle stage
- [ ] HubSpot → Platform direction: customer contact data (source of truth)
- [ ] Platform → HubSpot direction: write-back summary properties (active contract count, monthly revenue, next service date, customer PIN)
- [ ] Log platform events to HubSpot timeline: contract signed, service completed, invoice sent, payment received — so the full customer story is visible in HubSpot without switching apps
- [ ] On new customer: team creates contact in HubSpot → sync picks it up → platform auto-creates local customer record
- [ ] On customer update: team edits in HubSpot → next sync updates local cache
- [ ] Customer search in platform: searches local cache (fast), links to HubSpot for full profile

#### What Lives Where
| Data | Where It Lives | Why |
|------|---------------|-----|
| Customer name, email, phone, address | **HubSpot** (synced to local cache) | CRM data — entered and managed in HubSpot |
| Communication history (calls, emails, notes) | **HubSpot** | HubSpot is built for this |
| Sales pipeline, lifecycle stage | **HubSpot** | CRM workflow |
| Properties (service addresses) | **Your platform** | A customer can have many properties; each has measurements |
| Property measurements (lawn SF, edge LF, etc.) | **Your platform** | Deeply operational — drives bids, schedules, crew time |
| Difficulty splits, equipment splits | **Your platform** | Domain-specific production rate data |
| Measurement sources (Attentive, drone, GPS) | **Your platform** | Operational |
| Bids, contracts, tickets, schedules | **Your platform** | Core business logic |
| Time entries, earned revenue | **Your platform** | Operational |
| Invoices, payments | **Your platform + Stripe** | Financial |
| Customer PIN (service portal) | **Your platform** | Operational (synced back to HubSpot as custom property) |
| Service requests | **Your platform** | Operational (crew workflow) |
| Service offers | **Your platform** | Revenue generation from reports (approval flow, conversion tracking) |

#### Customer Communication
- [ ] SMS integration (Twilio) — appointment reminders, service completed notifications
- [ ] Email integration (SendGrid) — proposals, invoices, follow-ups
- [ ] Log all outbound SMS/email to HubSpot as timeline events (full communication history stays in HubSpot)
- [ ] Customer portal (evolves from index.html) — customers see schedule, invoices, request service

#### Service Offers in Reports
- [ ] **Service offer creation UI** (crew app Reports tab + management platform weekly reports) — pick service from catalog, quantity, price auto-fills, attach photo, add note
- [ ] **Service offer embedding** in weekly report emails — clean card layout with service description, photo, price, and Approve/Decline buttons
- [ ] **Service offer embedding** in site report PDFs and companion emails — same card layout, approval link in the email (PDFs link to web approval page)
- [ ] **Customer approval page** — token-based (no login), shows service details, photo, price, customer confirms with name entry → records approval with timestamp + IP
- [ ] **Offer management queue** — approved offers appear as notifications to office staff, who schedule the work as a one-time ticket or add to existing contract
- [ ] **Offer lifecycle** — pending → approved/declined/expired (30-day auto-expiry), 7-day follow-up reminder for pending offers
- [ ] **Revenue attribution** — track offers sent, approved, declined, expired by crew member, property, service type, and month
- [ ] Log service offer events to HubSpot timeline: offer sent, approved, declined, work completed

**Deliverable:** Customer data entered once in HubSpot, available everywhere. Your platform reads from HubSpot for customer info, writes operational data locally. Communication logged back to HubSpot so the full customer story is in one place. Every report sent to a customer is a revenue opportunity — crew recommendations convert to approved work with one tap.

### Phase 4: Invoicing & Payments (Weeks 15-18)
**Goal: Get paid**

> **Key decisions made:** (1) Invoice types are simple — fixed monthly maintenance contracts and project work (deposit + final payment), NOT per-ticket earned revenue billing. (2) Credit card fees are baked into the contract price so the customer never sees a surcharge. (3) Stripe Payments (core) handles payment processing — NOT Stripe Invoicing — because the platform generates its own invoice PDFs via Lambda/ReportLab. (4) QuickBooks handles accounting — invoices push to QBO, direct expenses push to QBO, QBO produces the P&L. (5) No sensitive payment data (card numbers, bank accounts) ever touches the platform — Stripe Checkout hosted page only.

#### Invoice Types

**Fixed monthly maintenance contracts:**
- Same amount every month, pulled directly from the contract's `monthly_payment` field
- Invoice line: "Monthly Landscape Maintenance — $X,XXX.XX"
- Generated in bulk at billing cycle (e.g., 1st of the month for all active contracts)

**Project work:**
- Deposit invoice (percentage or fixed amount) created from estimate at contract signing
- Final payment invoice created on project completion
- Invoice lines reference the estimate/contract for the project

#### Invoice Generation & Delivery
- [x] "Generate Invoices" batch action in estimate.html — scans contracts, creates invoice records, generates PDFs, sends emails with Stripe Pay Now links
- [ ] Bulk monthly invoice generation — one click to generate invoices for all active maintenance contracts
- [ ] Invoice PDF generation via AWS Lambda (ReportLab) — same pipeline as site reports, new invoice template
- [ ] Invoice PDF includes: company logo, customer info, invoice number, date, due date, line items, total, and a **"Pay Now" link**
- [ ] Email delivery via Apps Script `GmailApp.sendEmail()` with PDF attachment
- [ ] Automated payment reminders for overdue invoices
- [ ] Invoice numbering: sequential (INV-001, INV-002, etc.)

#### "Pay Now" Link Strategy

> **Problem:** Stripe Checkout Session URLs expire (max 30 days). A monthly invoice PDF sitting in email could outlive the link.

> **Solution:** The "Pay Now" link on the invoice PDF points to the platform's own Apps Script endpoint, NOT directly to Stripe. When clicked, the endpoint creates a fresh Stripe Checkout Session on demand and redirects the customer to Stripe's hosted payment page. The link never expires. If the invoice is already paid, redirect to a "This invoice has been paid" confirmation page instead of allowing double-payment.

**Flow:**
1. Customer receives invoice PDF via email
2. Clicks "Pay Now" link → hits Apps Script `doGet()` with `?payInvoice=INV-001`
3. Apps Script checks invoice status — if already paid, show confirmation page
4. If unpaid, creates a Stripe Checkout Session (card + ACH enabled) with invoice metadata
5. Redirects customer to Stripe's hosted payment page (on stripe.com)
6. Customer enters payment info **on Stripe's site** — platform never sees card/bank data
7. Stripe processes payment → fires `checkout.session.completed` webhook
8. Apps Script `doPost()` receives webhook → marks invoice paid in Google Sheet
9. Payment details pushed to QuickBooks

#### Stripe Integration (Core Payments Product)

> **Why Stripe Payments, not Stripe Invoicing:** Stripe Invoicing charges $0.50/invoice on top of processing fees and generates its own PDFs/emails. Since the platform already has PDF generation (Lambda/ReportLab) and email delivery (Apps Script), using the core Payments product avoids the per-invoice fee and gives full control over invoice design and delivery.

- [ ] Stripe account setup (set `STRIPE_SECRET_KEY` in Script Properties)
- [x] Stripe Checkout Sessions via API — `createStripeCheckoutSession()` in Apps Script, payment mode for one-time + setup mode for auto-pay
- [x] Credit card payments via Stripe Checkout (payment mode)
- [ ] ACH bank transfer payments (0.8% capped at $5) — future Stripe Checkout configuration
- [x] Stripe payment polling via `checkStripePayment()` — no webhooks needed (Apps Script limitation), uses redirect pages + frontend polling instead
- [x] Auto-mark invoices as paid when polling confirms payment
- [x] Invoice metadata attached to Checkout Session for routing
- [x] **No sensitive payment data touches the platform** — Stripe Checkout hosted page handles all card/bank input (SAQ A PCI compliance)
- [x] Auto-pay setup via Stripe Checkout (setup mode) — `setupAutoPay()` creates customer + saves payment method
- [x] Auto-pay charging via Stripe PaymentIntents API — `chargeAutoPayInvoice()` in `generateInvoiceBatch()`

#### Credit Card Fee Strategy (Decided: Gross Up Contract Price)

> **Decision:** Bake the ~3% credit card processing cost into the contract price at the estimating stage. The customer agrees to a clean monthly number upfront — no surcharge line item, no surprise at checkout. This avoids customer friction and legal complexity around surcharging.

- [ ] In estimate.html: toggle "Customer will pay by card" → grosses up the contract price by ~3%
- [ ] Example: to net $1,200/month after 3% fee, price the contract at $1,237.12
- [ ] Bid summary shows base price and CC-adjusted price side by side so you know your true margin
- [ ] If customer later pays by ACH or check, you keep the slightly higher price (or offer a discount as incentive)
- [ ] `cc_gross_up` boolean already exists in the `bids` table schema

#### Manual Payment Recording (Check, Cash)
- [x] "Record Payment" button on invoice detail view
- [x] Payment method selector: Check, Cash, Card, ACH
- [x] Payment fields: amount (pre-filled with balance), date, notes (check #, reference)
- [x] Partial payment support — multiple payments against one invoice, tracks remaining balance, auto-updates status to `partial` or `paid`
- [ ] Invoice status auto-updates: sent → partial → paid based on total payments vs amount due

#### Invoice Dashboard (estimate.html) — ✅ Built
- [x] Invoice list view with status filters: All, Draft, Sent, Overdue, Paid
- [x] Color-coded status badges: draft (gray), finalized (blue), sent (blue), partial (orange), paid (green), overdue (red), void (gray strikethrough)
- [x] Quick stats: Total Outstanding, Overdue, Collected This Month, Drafts
- [x] Individual invoice detail with line items table, totals, payment history
- [x] Batch invoice generation — scans active contracts, dedup by period, creates drafts, auto-charges auto-pay
- [x] Invoice lifecycle actions: Finalize, Send (email + PDF + Stripe Pay Now link), Record Payment, Check Payment Status, Void
- [x] Invoice PDF generation via HtmlService (Apps Script fallback) and WeasyPrint (Lambda)
- [ ] Aging report: 0-30, 31-60, 61-90, 90+ days outstanding

#### QuickBooks Integration (Accounting & Financials)

> **QuickBooks is the accounting system.** The platform generates invoices and collects payments — then pushes both to QBO so the books stay current. QBO produces the P&L, balance sheet, and tax reports. The platform also pushes direct expense data (labor costs from time entries) to QBO so the P&L reflects true profitability.

**Two-way relationship:**
- **Platform → QBO (push):** Invoices, payments, and direct labor expenses
- **QBO → Platform (read):** Invoice payment status (for dashboard), expense categories (optional overhead pull)

**What gets pushed to QuickBooks:**
- [ ] Invoices — when created in the platform, pushed to QBO as an invoice
- [ ] Payments — when recorded (Stripe webhook or manual check), pushed to QBO as a payment against the invoice
- [ ] Direct labor expenses — monthly labor cost calculated from time entries (crew hours × rates), pushed as an expense entry categorized by crew/property
- [ ] Material and subcontractor costs — pushed as expenses when recorded

**What stays in the platform only (not pushed to QBO):**
- Earned revenue tracking (management accounting, not bookkeeping)
- Earned vs. invoiced variance analysis
- Per-property and per-crew profitability breakdowns
- Contract completion percentages

**Setup:**
- [ ] OAuth flow: connect QBO account in Settings
- [ ] Customer mapping: map platform customers to QBO customer records
- [ ] Expense category mapping: map labor/materials to QBO expense accounts
- [ ] One-way push for invoices/payments/expenses — the accountant works in QuickBooks as they always have

**Result — two views of the business:**
- **QuickBooks** → "Did we make money this month?" (cash accounting, tax-ready P&L)
- **Platform dashboard** → "Are we on track on our contracts?" (earned revenue, operational efficiency, crew profitability)

#### Phase 6 Consideration: Stripe Connect for Multi-Tenant

> When other landscaping companies use the platform (Phase 6), each company needs their own Stripe account receiving their own customer payments. **Stripe Connect** with **Express accounts** handles this — the platform creates a connected Stripe account via API during company onboarding, pre-filled with info from signup. The new company completes Stripe's hosted onboarding (bank account, identity verification) as part of the platform signup flow. From their perspective, it feels like one signup process, not two separate systems.

**Deliverable:** Monthly maintenance invoices go out as branded PDFs with a "Pay Now" link. Customers pay online (card or ACH) on Stripe's hosted page — the platform never touches payment data. Stripe webhook auto-marks invoices paid. Check payments are recorded manually. Invoices, payments, and labor expenses all push to QuickBooks for accounting. The dashboard shows what's paid, what's outstanding, and what's overdue.

### Phase 5: Financial Reporting & Company-Wide P&L (Weeks 19-22)
**Goal: Show the owner their TRUE numbers — not just job margin, but real profitability after overhead**

> This is where you beat every competitor. Every landscape software shows direct job profitability. Almost none connect that to company-wide financials. The owner sees a 38% margin in their field service software, then opens QuickBooks and realizes they barely broke even. That gap is where businesses die. Your platform closes it.

#### Earned vs. Invoiced Revenue
- [ ] **Earned revenue dashboard**: sum of completed ticket earned values, grouped by day/week/month
- [ ] **Invoiced revenue dashboard**: sum of invoices sent, grouped by day/week/month
- [ ] **Earned vs. invoiced comparison chart**: monthly overlay showing when you're working ahead vs. collecting ahead
- [ ] **Deferred revenue report**: total invoiced minus total earned across all active contracts — how much have you collected for work not yet done?
- [ ] **Property-level earned vs. invoiced**: flag properties where earned consistently exceeds invoiced (you're losing money)
- [ ] **Contract completion tracking**: percentage of total contract value earned to date, with projection to contract end

#### Direct Profitability (Job-Level)
- [ ] Profitability by property (earned revenue − direct labor cost − material cost − sub cost)
- [ ] Profitability by service type (which services make money, which don't)
- [ ] Profitability by crew (which crews are efficient, which are burning hours)
- [ ] Profitability by division (MNT vs IRR vs CON vs ENH)
- [ ] Customer lifetime value (total revenue − total cost over contract history)
- [ ] **Bid accuracy report**: bid estimates vs. actual costs per property — are you pricing correctly?

#### Overhead Setup & Allocation
- [ ] **Overhead entry screen**: owner enters monthly overhead costs by category (or pulls from QBO)
- [ ] Built-in categories: Truck Payments, Fuel, Insurance (GL/WC/Auto), Shop Rent, Equipment Leases, Office Salaries, Phone/Internet, Uniforms, Dump Fees, Licenses, Marketing, Other
- [ ] Each category has an allocation method:
  - **Per crew**: divide evenly across active crews (e.g., truck payment per crew)
  - **Per revenue**: allocate proportional to revenue (e.g., insurance — bigger contracts bear more)
  - **Per labor hour**: allocate proportional to hours worked (e.g., fuel — more hours = more fuel)
  - **Fixed**: not allocated to jobs — company-level only (e.g., office rent, marketing)
- [ ] **Monthly snapshot**: at month-end, lock in the overhead numbers for historical accuracy. Changing a truck payment in June doesn't retroactively change April's P&L.
- [ ] If QBO is connected: offer to pull expense totals by category to pre-populate — owner just confirms and adjusts

#### Company-Wide P&L (The Killer Feature)
- [ ] **True P&L by month**: Revenue (earned) − Direct Costs (labor + materials + subs) − Allocated Overhead = **Net Profit**
- [ ] **Margin waterfall**: start with gross revenue, subtract each cost category visually, end with net profit. The owner sees exactly where the money goes.
- [ ] **P&L by crew**: Revenue generated by crew − crew's direct labor − crew's allocated overhead (truck, fuel, equipment) = crew net contribution. Which crews actually make money?
- [ ] **P&L by property**: Revenue − direct costs − allocated overhead share = true property profitability. A property might show 35% direct margin but only 8% after overhead. That changes pricing decisions.
- [ ] **Breakeven analysis**: how many properties (or how much revenue) does each crew need to cover its overhead? At what point does adding a crew become profitable?
- [ ] **Budget vs. actual**: set monthly revenue and cost targets, compare against actual — are you on track for the year?
- [ ] **Year-over-year comparison**: same month last year vs. this year, with growth rates

#### Example: The Financial Picture That Changes Decisions

```
Monthly P&L — April 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Revenue (earned)                    $48,200
  └─ MNT Crew 1                    $28,400
  └─ MNT Crew 2                    $19,800

Direct Costs                       ($28,920)  60.0%
  └─ Labor (822 hrs × $18/hr)      ($14,800)
  └─ Materials                       ($3,120)
  └─ Subcontractors                  ($1,000)
  └─ Travel/indirect labor          ($10,000)

Gross Profit                        $19,280   40.0%

Overhead                           ($14,600)
  └─ Trucks (2 × $1,200)            ($2,400)
  └─ Fuel                           ($2,800)
  └─ Insurance (GL/WC/Auto)         ($3,200)
  └─ Shop rent                      ($1,800)
  └─ Equipment leases               ($1,600)
  └─ Office salary                  ($2,000)
  └─ Phone/misc                       ($800)

Net Profit                           $4,680    9.7%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Without overhead: "We're at 40% margin, great!"
With overhead:    "We're at 9.7% — we need to raise prices or cut costs."
```

**That's the report that changes how an owner runs their business.**

#### Operational Metrics
- [ ] Crew productivity (properties per day, hours utilized vs. indirect time)
- [ ] **Direct vs. indirect time dashboard**: per crew, per day/week/month — direct hours, indirect hours, direct %, trend over time
- [ ] **Indirect time breakdown**: time by category (travel, shop, dump run, fuel, break, meeting, equipment) — identify where non-billable time goes
- [ ] **Travel time analysis**: average travel between stops, total daily travel, route efficiency score
- [ ] **Shop time report**: morning start time trends, average load/unload time, late start frequency
- [ ] **Data-driven travel percentage**: actual indirect time ÷ total time → feeds back into estimating tool to replace the manual travel % guess with real data
- [ ] **Production rate accuracy report**: estimated hours (from bids) vs. actual hours (from time clock) per service per property — feeds back into estimating tool to improve future bids
- [ ] Contract renewal tracking and forecasting
- [ ] Payroll export (hours by crew member by pay period — CSV/PDF for payroll provider)

#### Exports
- [ ] Export reports to PDF and CSV
- [ ] Scheduled email reports (weekly summary to owner)
- [ ] **Monthly financial package**: auto-generated PDF with P&L, earned vs. invoiced, crew profitability, overhead breakdown — the kind of report the owner can hand to their accountant or bring to a bank meeting

**Deliverable:** The owner sees the COMPLETE financial picture in one place — not just job margin, but true profitability after every dollar of overhead. Which properties make real money, which crews carry their weight, where to cut costs, when to raise prices. This is the report that every landscape owner wants but no software gives them today.

### Phase 6: Multi-Tenant & Go to Market (Weeks 23-28)
**Goal: Other companies can sign up and use the platform**

- [ ] Tenant onboarding flow (company signup → setup wizard)
- [ ] Subscription billing (Stripe) — monthly plans based on crew count or feature tier
- [ ] Tenant-specific branding (company logo, colors on proposals and invoices)
- [ ] Custom domain support (optional — their-company.enduranceplatform.com)
- [ ] Admin superuser dashboard (you manage all tenants, monitor usage)
- [ ] Usage limits by plan tier
- [ ] Landing page / marketing site
- [ ] Documentation and onboarding guides
- [ ] Terms of service, privacy policy

**Deliverable:** A real SaaS product that other landscape companies can sign up for and start using.

### Phase 7: AI-Powered Features & Community Innovation (Weeks 29+)
**Goal: Embed AI into the platform and let users drive feature development — the Tesla OTA model**

#### AI Help Assistant
- [ ] Embed Claude (Anthropic API) as an in-app help chat across all screens
- [ ] System prompt loaded with full app documentation, field definitions, calculation logic, and workflow guides
- [ ] Users ask questions in natural language instead of reading docs or contacting support
- [ ] Context-aware — the assistant knows which screen the user is on and what data they're looking at
- [ ] Supports English and Spanish

#### Community Feature Sandbox
- [ ] Each user gets access to a sandboxed environment where they can describe a feature idea to Claude
- [ ] Claude builds the feature as a working prototype inside the sandbox
- [ ] The user can test it in isolation — their sandbox doesn't affect the main app or other users
- [ ] "Submit for Review" button sends the feature to the admin review queue

#### Admin Feature Review Pipeline
- [ ] Admin dashboard shows submitted feature ideas with: description, generated code, live preview, submitter info
- [ ] Admin can test, modify, approve, or reject each submission
- [ ] Approved features get packaged and pushed as platform updates to all tenants
- [ ] Users see a "What's New" notification when features they suggested go live
- [ ] Credit the submitter: builds community ownership

#### Technical Requirements
- Anthropic Claude API for the help assistant and sandbox code generation
- Sandboxed iframe or isolated React environment per user
- Feature submission queue stored in PostgreSQL
- Admin review UI with live preview rendering
- Feature flagging system to roll out approved features gradually
- Content security policies to prevent sandbox code from accessing main app data

**Deliverable:** A platform that gets smarter and better over time, powered by the community that uses it every day.

---

## Integration Architecture

Every external integration follows the same pattern: **Settings → Connect → Done.** One OAuth click (or one API key paste), and the integration works silently forever. No configuration pages with 40 options. No "mapping fields." No training required.

```
Your Platform (what you build — the operational core)
  │
  ├── HubSpot ─── CRM, customer data, communication history
  │                Connect: OAuth click in Settings → Integrations
  │                Sync: poll every 10-15 min, write-back summaries + timeline events
  │
  ├── Stripe ──── Payment processing (core Payments product, NOT Stripe Invoicing)
  │                Connect: Stripe account (single tenant) / Stripe Connect (multi-tenant Phase 6)
  │                Sync: Checkout Sessions created on demand, webhooks for payment confirmation
  │                Note: Platform never touches card/bank data — Stripe hosted page only (SAQ A)
  │
  ├── QuickBooks ─ Accounting, P&L, tax reporting (the accounting backbone)
  │                Connect: OAuth click in Settings → Integrations
  │                Push: invoices, payments, and direct labor expenses
  │                Read: invoice payment status, expense categories (optional)
  │
  ├── DocuSign ── E-signature (OPTIONAL tenant add-on)
  │                Connect: OAuth click in Settings → Integrations → toggle on
  │                Default off: built-in signature pad used instead
  │
  ├── Twilio ──── SMS notifications (platform-level, not per-tenant)
  │                Stateless: fire and forget, log to HubSpot timeline
  │
  └── SendGrid ── Email notifications (platform-level, not per-tenant)
                   Stateless: fire and forget, log to HubSpot timeline
```

**Three categories of integration:**

| Category | Examples | Connection | Sync Model |
|----------|----------|------------|------------|
| **Tenant-connected (required)** | HubSpot, Stripe, QuickBooks | Each tenant connects their own account via OAuth during onboarding. Stripe via Connect (Express accounts) for multi-tenant. | HubSpot: poll. Stripe: webhooks. QBO: push invoices/payments/expenses. |
| **Tenant-connected (optional)** | DocuSign | Tenant enables in Settings → Integrations when ready | Push on events |
| **Platform-level** | Twilio, SendGrid, Google Maps | Configured once by you, shared across all tenants | Stateless — fire and forget |

**The onboarding flow for a new tenant:**
1. Sign up → create company profile
2. "Connect HubSpot" → OAuth → customer data starts syncing immediately
3. "Connect Stripe" → Stripe Connect OAuth → ready to accept payments
4. That's it. They're operational. QuickBooks and DocuSign are available in Settings when they're ready, but never required.

**Integration settings UI (Settings → Integrations):**
Each integration gets a card with: service logo, connection status (connected / not connected), a "Connect" or "Disconnect" button, and one or two toggles for behavior (e.g., "Use DocuSign for signing" on/off). No configuration forms. No field mapping. If it's connected, it works.

---

## Smart Features

These are cross-cutting features that emerge from the data pipeline connecting estimates, schedules, time tracking, and customer requests.

| Feature | Trigger | Action |
|---------|---------|--------|
| **Request alert on arrival** | Crew taps "Start Job" on a property | Show open customer requests for that property in an action sheet |
| **Actual vs. estimated** | Job completed | Show time comparison inline ("1h 42m actual vs 1h 48m est — 6m under ✅") |
| **Running behind alert** | Day clock > sum of remaining estimates | "You're 45 min behind schedule" notification |
| **Auto-complete suggestion** | Job completed at a property with open requests | Prompt to also complete the related customer request |
| **Weather skip** | Manager marks a date as weather day | All tickets for that crew on that date → skipped, auto-rescheduled |
| **Production rate feedback** | Monthly aggregation | Compare estimated vs. actual hours by service type to refine production rates |
| **Route optimization** | Future enhancement | Suggest stop order based on GPS proximity |
| **Contract renewal alert** | 60 days before contract end date | Notification to manager with renewal/price increase options |
| **High indirect time alert** | Crew's daily direct % drops below threshold (e.g., 60%) | Notify manager: "Crew A at 54% direct time today — 2h 15m travel, 45m shop" |
| **Travel time auto-update** | Monthly aggregation | Calculate actual travel % from indirect time data → suggest updated travel % for estimating tool |
| **Late start alert** | Day clock in after threshold (e.g., 7:15 AM) | Flag to manager with pattern tracking (3+ late starts this week) |
| **Service offer suggestion** | Crew completes site report with photos showing bare mulch beds, overgrown hedges, faded seasonal color | Suggest adding a service offer for that category pre-populated with catalog pricing |
| **Offer follow-up** | Service offer pending for 7+ days with no response | Auto-send a follow-up reminder to the customer; expire at 30 days |
| **Offer conversion tracking** | Monthly aggregation | Report: offers sent, approved, declined, expired, revenue generated — by crew, property, service type |
| **Intelligent crew reassignment** | Crew member finishes assigned ticket/service | Data-driven recommendation on which remaining ticket to add the freed member to (see detailed design below) |

---

## Intelligent Crew Reassignment (Data-Driven "Where to Next?")

The existing "Where to Next?" wizard already shows time projections for adding freed crew to services *within the same ticket*. This feature extends that concept **across tickets on the day's route** and uses **historical production data** to rank which tickets benefit most from extra crew.

### The Problem

When a crew member finishes their assigned ticket, the crew leader has to decide: add them to Ticket A (leaf cleanup), Ticket B (mowing), or Ticket C (weed control)? Today this is gut instinct. But the data to make this decision well already exists in our time entries.

### Core Insight

Not all services benefit equally from additional crew:
- **Leaf cleanup** — highly scalable. Adding a crew member cuts remaining time significantly. More hands = more bags = faster.
- **Mowing** — scalable with diminishing returns. A second mower helps a lot; a fourth mower may not (limited by mower count, property layout, gate access).
- **Weed control / chemical application** — fixed duration. One person sprays the property in X minutes regardless of how many crew are present. Adding crew here is wasted labor.
- **Hedge trimming** — moderately scalable. Depends on hedge linear footage and how many can work simultaneously.

The system can learn these patterns from its own data rather than hardcoding them.

### Data Sources (Already Collected)

| Data | Source | What It Tells Us |
|------|--------|-----------------|
| Estimated man-hours per service | `estimatedHours` in ticket services | What we predicted |
| Actual man-hours per service | Time Entries with `serviceName`, `memberCount`, timestamps | What actually happened |
| Crew size per service entry | `memberCount` on each time entry | How many people were on the service |
| Service splits on crew change | `splitTimeEntry()` creates before/after entries | Exact productivity delta when adding/removing a crew member |
| Duration type | `durationType` on service (`scalable` / `fixed`) | Baseline classification |
| Production rate analysis | `getProductionAnalysis` endpoint | Service-level efficiency (est vs actual) with per-ticket detail |

### The Key Metric: **Crew Scalability Factor**

For each service type, calculate how much faster the service actually gets per additional crew member:

```
scalability_factor = Δ wall_time_reduction / Δ crew_added
```

Derived from historical time entry splits — every time `splitTimeEntry()` fires because a crew member was added, we have a natural A/B test: same service, same property, before and after adding crew. Over hundreds of entries, this builds a reliable per-service-type scalability curve.

A scalability factor near 1.0 means perfectly scalable (2 crew = half the time). Near 0.0 means fixed (extra crew doesn't help). Most services fall somewhere in between.

### How It Works in the App

**When a crew member is freed** (finishes a ticket or service), the reassignment wizard ranks the remaining day's tickets by **time savings impact**:

```
impact_score = remaining_est_minutes × scalability_factor(service_type) × (1 / current_crew_count)
```

This naturally prioritizes:
1. **Long tasks** with high scalability (leaf cleanup with 90 min remaining)
2. **Undermanned tasks** (1-person mowing job benefits more from +1 than a 3-person job)
3. **Scalable service types** over fixed-duration ones (weed control drops to the bottom)

The wizard shows each available ticket with:
- Remaining estimated time at current crew
- **Projected time with the freed member added** (using the learned scalability factor, not a naive division)
- A visual indicator of impact: high (green), moderate (yellow), low/none (gray)

### Data Collection Phase

Before the model has enough data, fall back to the existing `durationType` classification:
- `scalable` services: assume linear scaling (optimistic, but better than nothing)
- `fixed` services: show "Adding crew won't speed this up" (already implemented)

As split-entry data accumulates (target: 50+ splits per service type), transition to the learned scalability factors. The Production Rates view can show a "Crew Scalability" column alongside existing efficiency metrics.

### Backend Requirements

- **New aggregation**: group time entry splits by service type, compute average wall-time reduction per crew member added
- **Store scalability factors**: per service type in the Service Catalog (alongside production rates), updated monthly or on-demand
- **Expose in API**: `getCrewScalability` endpoint or include in `getProductionAnalysis` response

### Integration with Existing Systems

- **Reassignment wizard** (`renderReassignWizard()`): already shows time projections for within-ticket reassignment. Extend to show cross-ticket recommendations when a crew member finishes their last service and has no more services in the current ticket.
- **Production Rates view**: add a "Crew Scalability" tab or column showing the learned factors per service type, with data point counts and confidence indicators.
- **Day Summary**: track "reassignment savings" — how much time was saved by following the recommended reassignment vs. a naive assignment.

---

## Service Offers (Upsells in Reports)

Every time a report goes to a customer — weekly report or site report — it's an opportunity to offer additional services. The crew is already at the property. They can see what needs work. The report is already going to the customer's inbox. Embedding a service recommendation with one-tap approval turns routine communication into revenue.

### How It Works

**Crew side (creating offers):**

1. **In a Site Report:** After capturing photos and notes, crew sees an "Add Service Recommendation" button. They pick a service from the catalog (or type a custom one), enter quantity and price (pre-populated from catalog), optionally attach one of the photos they just took ("this is why we're recommending it"), and add a note. Multiple offers can be attached to one report.

2. **In a Weekly Report:** Manager or crew leader generates the weekly summary for a property. Before sending, they can attach service offers the same way — pick service, set price, add photo/notes. This is especially useful after seasonal inspections or when the crew notices something during regular maintenance.

The offer creation UI is fast — it should take under 30 seconds to add a recommendation. Pre-populated catalog pricing means the crew doesn't have to calculate anything. If the company has standard pricing for mulch refresh, hedge trimming, seasonal color, etc., one tap selects the service and the price fills in.

**Customer side (approving offers):**

The customer receives their report (email or SMS) with the normal content — visit summary, photos, notes. At the bottom, any attached service offers appear in a clean card layout:

```
┌─────────────────────────────────────────────────┐
│  ★ Recommended Service                          │
│                                                 │
│  Mulch Bed Refresh                              │
│  12 cubic yards of premium brown mulch           │
│  applied to all landscape beds.                  │
│                                                 │
│  [Photo of bare mulch beds]                      │
│                                                 │
│  $1,020.00                                       │
│                                                 │
│  [ Approve ]              [ No Thanks ]          │
└─────────────────────────────────────────────────┘
```

Tapping "Approve" opens a lightweight confirmation page (token-based, no login):
1. Customer sees the service details and price
2. Enters their name (pre-filled if known)
3. Taps "Confirm — Schedule This Service"
4. Platform records: approval timestamp, IP, name
5. Office gets notified: "John Smith approved Mulch Bed Refresh at 123 Oak Dr — $1,020"
6. Work gets scheduled

Tapping "No Thanks" records a decline (no follow-up for that specific offer). No response after 30 days = auto-expired.

**Office side (after approval):**

Approved offers appear in a queue (or as notifications). The office:
1. Sees the approved service, property, price, and customer name
2. Schedules the work — either creates a one-time ticket (for a one-off service like mulch) or adds a recurring service to the existing contract
3. The offer record links to the resulting ticket or contract service for tracking

### What This Replaces

Today this process is: crew notices something → tells the office → office calls the customer → customer says yes or no → office creates a work order manually. That's 4 handoffs with days of delay. The service offer system makes it: crew adds recommendation to report → customer approves in one tap → office schedules. One handoff, same day.

### Revenue Tracking

Every service offer has a clear revenue attribution chain:
- Which crew member recommended it
- Which report it was attached to
- Which property and customer
- Approval rate by service type
- Revenue generated from offers vs. original contract value

This becomes a powerful management tool: "Crew A generates $4,200/month in approved service offers. Crew B generates $800. What's Crew A doing differently?"

### Pricing Source

Service offers can be priced three ways:
1. **From catalog** — crew picks a service, price auto-fills from the service catalog (most common)
2. **From bid engine** — for more complex work, create a quick bid in the estimating tool linked to the property, then attach it as an offer
3. **Custom** — crew enters a flat price (for simple one-off work like "remove fallen branch — $150")

---

## Weekly Property Report Generator (AI-Powered)

Automated end-of-week customer-facing property reports, generated by Claude and reviewed by an account manager before sending.

### Architecture

```
Friday 2pm (scheduled job)
    │
    ▼
Query all activity per property this week
(site visits, photos, notes, categories, before/after reports)
    │
    ▼
Call Claude API with structured data + system prompt
    │
    ▼
Claude generates draft report
    │
    ▼
Draft saved to app with status: "pending_review"
    │
    ▼
Account manager gets notification
(push notification / email / in-app alert)
    │
    ▼
Account manager opens review screen
    ├── Edit text directly (inline editing)
    ├── Approve & Send
    ├── Reject with note (re-generates with feedback)
    └── Skip (no report this week)
    │
    ▼
Approved report sent to customer
(email with PDF attachment or inline HTML)
```

### System Prompt

```
You are a professional report writer for a property maintenance and inspection company. Your job is to write clear, friendly, end-of-week summary reports that get sent directly to property owners and customers.

AUDIENCE:
- Property owners, landlords, property managers, and commercial clients
- They are NOT contractors or tradespeople — avoid technical jargon
- They want to know: what happened, what was found, what's been fixed, and what's next
- They are busy — keep it scannable and concise

TONE:
- Professional but warm — like a trusted project manager giving a weekly update
- Confident and reassuring — the customer should feel their property is in good hands
- Direct — lead with the most important information
- Use plain language — say "fixed" not "remediated", say "roof" not "roofing substrate"

REPORT STRUCTURE:

1. **Opening line** — One sentence summarizing the week. Reference the property by street name, not full address. Example: "Here's your weekly update for the Elm Street property."

2. **Work completed** — What was done this week. Lead with finished items. If before/after photos exist, reference them naturally: "The gutter replacement is now complete — you'll find the before and after photos attached." Group related work together rather than listing visit-by-visit.

3. **New findings** — Anything new the inspectors flagged. Describe what was found in plain terms, why it matters, and what the recommended next step is. Don't alarm the customer — frame new findings as proactive, not urgent, unless the inspector's notes indicate urgency.

4. **Coming up next** — What's planned or recommended for the following week. If nothing specific is planned, say something like "We'll continue monitoring and will update you if anything needs attention."

5. **Closing** — One friendly line. Keep it simple: "As always, feel free to reach out if you have any questions."

FORMATTING RULES:
- Use short paragraphs, 2-3 sentences each
- No bullet points or numbered lists — write in natural prose
- Bold section headers: **Work Completed**, **New Findings**, **Looking Ahead**
- Keep the total report between 150-300 words — this is a summary, not a detailed log
- Never include inspector names, internal reference numbers, or timestamps
- Never include the full street address — use just the street name for privacy
- If no activity happened in a category, don't mention that category

DATA HANDLING:
- You will receive structured JSON with this week's activity
- Photos are referenced by filename — mention them as "attached photos" or "the photos included below", the system will handle actual attachment
- If a visit has no notes, skip it rather than saying "no notes were recorded"
- If the only activity was a routine check with no findings, keep the report very short — 2-3 sentences total is fine
- If before/after pairs exist, always highlight them — customers love seeing visible progress
- Category names from the inspection system (e.g., "exterior", "roofing", "plumbing") should be written naturally in the report, not as labels

THINGS TO NEVER DO:
- Never invent or assume work that isn't in the data
- Never make promises about timelines unless the data explicitly includes a scheduled date
- Never mention pricing, costs, or quotes
- Never reference other properties or other customers
- Never use phrases like "as per our records" or "please be advised" — these sound robotic
- Never start with "Dear" or "To whom it may concern" — start with the summary line directly
```

### API Call Structure

```python
import anthropic

def generate_weekly_report(property_data: dict) -> str:
    """
    property_data should include:
    {
        "property_name": "123 Elm Street",
        "customer_name": "Jane Smith",
        "week_ending": "2026-02-20",
        "visits": [
            {
                "date": "2026-02-16",
                "type": "site_report",
                "categories": ["roofing", "exterior"],
                "photos": [
                    {
                        "filename": "photo_0.jpg",
                        "category": "roofing",
                        "notes": "Missing shingles on north-facing slope, approx 3ft x 2ft area"
                    }
                ]
            }
        ],
        "before_after_reports": [
            {
                "date": "2026-02-18",
                "category": "exterior",
                "description": "Gutter replacement - east side",
                "before_notes": "Rusted through, pulling away from fascia",
                "after_notes": "New aluminum gutters installed, sealed and secured"
            }
        ],
        "previous_week_open_items": [
            "Gutter replacement scheduled for east side"
        ]
    }
    """

    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,  # The system prompt defined above
        messages=[
            {
                "role": "user",
                "content": f"""Generate the weekly property report for the week ending {property_data['week_ending']}.

Customer: {property_data['customer_name']}
Property: {property_data['property_name']}

Activity data:
{json.dumps(property_data, indent=2)}"""
            }
        ]
    )

    return message.content[0].text
```

### Human Review Screen

**Report Queue:**
- List of all generated reports for the week, grouped by status: **Pending Review**, **Approved**, **Sent**, **Skipped**
- Show property name, customer name, and a preview of the opening line
- Badge count on "Pending Review" so they can see at a glance how many need attention

**Review View:**
- Full report text displayed in an editable text area
- The raw activity data shown in a collapsible sidebar so the reviewer can cross-reference what Claude wrote against what actually happened
- Attached photos displayed as thumbnails below the report

**Actions:**
- **Approve & Send** — locks the report and queues it for delivery
- **Edit** — inline text editing with a save button, then approve
- **Regenerate** — text field for feedback (e.g., "Emphasize the urgency of the roof issue"), sends the original data + feedback back to Claude for a new draft
- **Skip** — no report sent this week, with an optional reason field

**Regenerate prompt pattern** — append reviewer feedback as a follow-up message:

```python
messages=[
    {
        "role": "user",
        "content": f"Generate the weekly property report...\n{json.dumps(property_data)}"
    },
    {
        "role": "assistant",
        "content": first_draft_text
    },
    {
        "role": "user",
        "content": f"Please revise this report with the following feedback from the account manager: {reviewer_feedback}"
    }
]
```

### Delivery

Once approved, the report can be delivered as:
- **Email** — HTML formatted body with photos embedded or attached
- **PDF** — Generated via the existing ReportLab Lambda function, styled as a branded customer report
- **Both** — PDF attached to the email, with a plain text summary in the email body

The customer-facing email should come from the account manager's name/email so it feels personal, not automated.

### Edge Cases

| Scenario | Handling |
|----------|----------|
| No activity this week | Generate a very short "no activity" report: "No visits were scheduled for Elm Street this week. Everything remains on track and we'll be back on-site next week." Reviewer can skip if preferred. |
| Only one brief visit with no findings | Short 2-3 sentence report. Don't pad it. |
| Urgent issue flagged by inspector | Claude should detect urgency language in notes ("immediate", "safety concern", "damage spreading") and adjust tone accordingly. Reviewer should pay extra attention to these. |
| Multiple properties for same customer | Generate separate reports per property. The reviewer can choose to combine them manually if desired. |
| Photos but no notes | Reference the photos but don't describe what's in them — say "photos from this week's visit are attached below" and let the images speak for themselves. |

---

## Prototype Implementation Order (Current Stack)

Before the full React/PostgreSQL migration, the ticket generation and schedule features can be built into the existing prototype to validate the workflow. This is the fastest path to crew-usable scheduling.

### Phase A: Contract + Ticket Generation (estimate.html) — ✅ Built
1. ✅ Contract creation endpoint (`createContract`) — saves to Contracts sheet
2. ✅ Contract update endpoint (`updateContract`) — updates existing contract row during revision
3. ✅ Ticket batch save endpoint (`saveTickets`) — saves to Scheduled Tickets sheet
4. ✅ Delete future tickets endpoint (`deleteFutureTickets`) — removes future scheduled tickets during revision
5. ✅ Ticket status update (`updateTicketStatus`) and reschedule (`rescheduleTicket`) endpoints
6. ✅ "Finalize Estimate" UI flow — locks estimate, opens modal for crew/day/dates, generates contract + tickets
7. ✅ **Estimate Revision workflow** — Finalized → Revision → Update Contract → re-Finalized. Updates existing contract, deletes/regenerates future tickets, preserves completed tickets, increments `revisionCount`
8. ✅ `generateSeasonalMowingDates()` — weekly Apr–Oct, biweekly Nov–Mar; fills dormant gaps for higher targets (e.g. 52), trims dormant dates for lower targets seasonal logic
9. ✅ `generateWeeklyDates()` — every week all year, trims to target visit count (50-54 visits)
10. ✅ `generateSimpleScheduleDates()` — evenly distributed dates for all other visit counts
11. ✅ **Item-level scheduling**: each line item can override the service visit count via `lineItem.itemVisits`
12. ✅ Ticket bundling — groups same-date services into one property visit, listing only items due that day
13. ✅ **Earned value** per ticket — proportionally distributed from bid rates/markups with penny reconciliation
14. ✅ `previewTickets()` — shows ticket count, item-level breakdown, and earned value before committing
15. ⬜ Optional: Google Calendar event creation via Apps Script `CalendarApp`

### Phase B: Schedule Tab (crew.html) — ✅ Built
1. ✅ Schedule tab as default home screen with 4-tab bottom navigation
2. ✅ Existing request dashboard relocated to Requests tab
3. ✅ Today's Route view — `getCrewSchedule` fetches tickets for today + assigned crew
4. ✅ **PIN-based crew check-in** — each member verifies with 4-digit PIN via `verifyPin` endpoint. Supports "Add Member" for subs from other crews. `checkedInMembers` stored as objects with backward compat.
5. ✅ Day clock UI (Start Day requires 1+ verified PIN → running HH:MM:SS timer → End Day)
6. ✅ Property stop cards with service list and estimated hours
7. ✅ **Multi-ticket simultaneous clocking** — Start button on ALL scheduled/partial tickets. `activeTickets` map tracks multiple concurrent timers.
8. ✅ **Member assignment overlay** — select crew subset per ticket, edit mid-ticket
9. ✅ Request alert: checks for open customer requests when starting a job at a property
10. ✅ Resume support: detects ALL open time entries and resumes multi-ticket timers after app restart

### Phase C: Time Clock (crew.html) — ✅ Built
1. ✅ Job clock: multi-ticket timers with HH:MM:SS elapsed + static target in stop cards
2. ✅ **GPS capture** at clock in/out — `captureGPS()` using `navigator.geolocation` with high accuracy. Called at 11 points: travel clock-in/out, day clock-in/out, ticket start, ticket complete. Coordinates sent as `latIn/lngIn/latOut/lngOut` on time entries
3. ✅ **Per-service clocking with crew assignment**: start/complete individual services within a ticket with per-service member selection from parent ticket's assigned crew. Saved as `service` entry type with `serviceName`, per-service `crewMembers`, and `memberCount`
4. ✅ **Clock-out decision modal**: est vs actual, service status, "Complete" or "Return Later" (partial)
5. ✅ **Partial ticket carry-over**: partial tickets show orange, carry completed services, "Start (Return)" resumes
6. ~~Active tickets panel~~: removed — redundant with property-grouped stop cards that auto-expand for active tickets
7. ✅ **Indirect time auto-capture**: day total minus job totals = indirect time
8. ✅ **Indirect category picker**: quick-tap to categorize (travel, shop, dump run, fuel, break, meeting, equipment, other)
9. ✅ Save time entries to Time Entries sheet (day_clock, job, indirect, service entries; `saveTimeEntry` + `updateTimeEntry`)
10. ✅ Actual vs. estimated comparison display in Clock-Out modal
11. ✅ **Day summary screen**: direct hours, indirect hours, total, direct %, crew members
12. ✅ Job completion flow (notes, service checklist, partial/complete decision)
13. ✅ **Before & After photo orientation matching** — Layer 1: real-time orientation hint banner in detail modal (`#ba-orientation-hint`) with green/red color via `window.resize` + `orientationchange`, detects before photo orientation via `naturalWidth`/`naturalHeight`. Layer 2: mismatch warning dialog in `baProcessAfterPhoto()` via `iosConfirm()` when after photo orientation doesn't match before. Layer 3 (ReportLab) not needed — existing fill-and-crop handles mixed orientations

### Phase D: Route Management (estimate.html / management view) — ✅ Built
1. ✅ **Schedule view** — day/week/month display modes with property stop cards, drag-drop stop reordering (`schedDrop()` + `saveRouteOrder()`), crew filter dropdown. Day view with earned value and margin per stop, week calendar grid with drag-to-reschedule, month calendar with ticket dots. Functions: `loadScheduleView()`, `renderSchedDay()`, `renderSchedWeek()`, `renderSchedMonth()`, `showSchedTicketDetail()`, `rescheduleFromDetail()`, `skipFromDetail()`
2. ✅ Reschedule endpoint exists (`rescheduleTicket`) — now also clears `needsReschedule` flag
3. ✅ Skip stop in crew app (`updateTicketStatus` with status = 'skipped') — now auto-sets `needsReschedule=TRUE`
4. ✅ **Bulk skip + Needs Reschedule queue** — "Skip Day (N)" button on crew headers in day view, `bulkSkipDay` batch endpoint, "Needs Reschedule" queue toggle with badge count, queue view grouped by crew with reschedule controls. All skips (crew field, office single, bulk) enter the queue. Functions: `bulkSkipCrewDay()`, `fetchRescheduleQueue()`, `renderRescheduleQueue()`, `rescheduleFromQueue()`, `toggleRescheduleQueue()`, `updateRescheduleQueueCount()`

### Phase E: Earned Revenue Dashboard (estimate.html / management view) — 🔶 Partially Built
1. ✅ **Monthly earned vs. collected bar chart** — side-by-side bars with pagination (`renderMonthlyChart()`, `calcMonthlyData()`)
2. ✅ **Contract-level earned vs. collected table** — per-contract breakdown with completion % (`renderContractTable()`)
3. ✅ **Deferred revenue** — collected minus earned, color-coded (orange if deferred/collected ahead, green if earned ahead of schedule). Summary cards: contract value, collected, earned, deferred revenue, completion %
4. ✅ **Contract completion percentage** — earned to date / total contract value, displayed per contract. Functions: `loadFinancials()`, `renderFinancials()`, `calcCollectedToDate()`
5. ⬜ Monthly P&L approximation — earned revenue minus internal costs from completed tickets

### Google Sheets (Consolidated "Estimating" Spreadsheet)

All sheets live in one spreadsheet with one Code.gs serving both estimate.html and crew.html:

**Existing Sheets:**
| Sheet | Purpose |
|-------|---------|
| Item Catalog | Production rates by item, unit, difficulty (Easy/Medium/Hard) |
| Service Catalog | Service definitions with line items, visits, billing tiers, duration type (scalable/fixed) |
| Settings | Key-value pairs for bid defaults |
| Bids | Saved estimates with financials (includes contractId, revisionCount, and status: Draft/Revision/Finalized) |
| Templates | Reusable estimate structures |
| Properties | Property addresses, crew assignments, customer PINs, crew phone |
| Requests | Customer requests and internal tickets |

**New Sheets (Built):**
| Sheet | Purpose |
|-------|---------|
| Contracts | contractId, bidId, propertyAddress, assignedCrew, preferredDay, startDate, endDate, contractMonths, monthlyPayment, status, createdDate, paymentTerms, contractValue, ccFeePercent, ccGrossUp, contactName, contactEmail, billingAddress, pdfUrl, pdfFileId (updatable via `updateContract` during revision; pdfUrl/pdfFileId saved after PDF upload) |
| Scheduled Tickets | ticketId, contractId, propertyAddress, assignedCrew, eventDate, servicesJson (each service has name, estimatedHours, items[]; each item has name, hours, and optionally quantities {easy,medium,hard}, unit, complexityFactor for production rate analysis), totalEstHours, travelHours, status, completedDate, notes, completedServices (JSON array of completed service names for partial tickets), createdDate, needsReschedule (boolean — auto-set TRUE when status=skipped, cleared when rescheduled) |
| Crew Members | name, phone, role (Leader/Member), crew (MNT Crew 1), pin (4-digit identity PIN), status (Active/Inactive) |
| Time Entries | entryId, crew, date, entryType (day_clock/job/indirect/service), ticketId, propertyAddress, serviceName, indirectCategory, clockIn, clockOut, durationMinutes, crewMembers (JSON), memberCount, notes, createdDate, durationType (scalable/fixed — auto-upgraded column), reopened ('true'/'' — auto-upgraded column, flags entries created by reopening a completed service), estimatedHours (auto-upgraded column — service-level estimated hours from ticket, passed by crew.html on service start/reopen/split) |

**Drive Folder Structure:**
```
Estimating Drive Folder (estimates JSON)
  └── [Street Address]/
      └── Estimates/
          └── BID-xxxxx.json

Text My Team Drive Folder (photos, reports)
  └── [Street Address]/
      ├── Photos/
      │   └── [Report Name]/
      └── Site Reports/
          ├── Report Data.json
          └── [Report Name]/
              └── Photo 1.jpg
```

---

## Project Structure (Monorepo)

```
endurance-platform/                  # Monorepo root (Turborepo or Nx)
├── packages/
│   ├── shared/                      # Shared TypeScript types, utils, constants
│   │   ├── src/
│   │   │   ├── types/               # Shared types used by both apps and API
│   │   │   │   ├── tenant.ts
│   │   │   │   ├── customer.ts
│   │   │   │   ├── property.ts
│   │   │   │   ├── bid.ts
│   │   │   │   ├── contract.ts
│   │   │   │   ├── schedule.ts
│   │   │   │   ├── timeclock.ts
│   │   │   │   └── invoice.ts
│   │   │   ├── utils/               # Shared helpers (formatCurrency, formatMinutes, etc.)
│   │   │   └── constants/           # Division codes, status enums, category lists
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   ├── ui/                          # Shared React component library
│   │   ├── src/
│   │   │   ├── Button/
│   │   │   ├── Card/
│   │   │   ├── Modal/
│   │   │   ├── DataTable/
│   │   │   ├── PropertySearch/
│   │   │   ├── TimeClock/
│   │   │   ├── SignaturePad/        # Canvas-based signature capture (touch, pen, mouse)
│   │   │   └── index.ts
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   ├── api-client/                  # Typed API client (used by both frontend apps)
│   │   ├── src/
│   │   │   ├── client.ts            # Base fetch wrapper with auth headers
│   │   │   ├── customers.ts
│   │   │   ├── properties.ts
│   │   │   ├── schedule.ts
│   │   │   ├── timeclock.ts
│   │   │   ├── bids.ts
│   │   │   └── invoices.ts
│   │   └── package.json
│   │
│   └── calculation-engine/          # Business logic extracted from estimate.html
│       ├── src/
│       │   ├── bidCalculator.ts     # Production rate → hours → cost → markup → price
│       │   ├── takeoffService.ts    # Takeoff pipeline (lawn, edge, mulch, hedge, etc.)
│       │   ├── scheduling.ts        # Season profiles, visit distribution, ticket bundling
│       │   ├── paymentSchedule.ts   # Penny distribution algorithm
│       │   └── earnedValue.ts       # Ticket earned value calculation
│       └── package.json
│
├── apps/
│   ├── platform/                    # Management Platform (Desktop-First)
│   │   ├── src/
│   │   │   ├── layout/              # Sidebar, topbar, multi-panel wrappers
│   │   │   ├── pages/
│   │   │   │   ├── Dashboard/
│   │   │   │   ├── Estimating/      # Desktop bid builder (spreadsheet-style table)
│   │   │   │   ├── Schedule/        # Schedule builder, calendar views
│   │   │   │   ├── Customers/       # CRM
│   │   │   │   ├── Properties/
│   │   │   │   ├── Invoices/
│   │   │   │   ├── Reports/
│   │   │   │   └── Admin/
│   │   │   │       ├── Contracts/
│   │   │   │       ├── Timesheets/
│   │   │   │       ├── CrewManagement/
│   │   │   │       └── CompanySettings/
│   │   │   └── PlatformApp.tsx
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.ts
│   │   └── package.json
│   │
│   ├── crew/                        # Crew App (Mobile-First)
│   │   ├── src/
│   │   │   ├── layout/              # Bottom tab bar (4 tabs), iOS-style navigation
│   │   │   ├── pages/
│   │   │   │   ├── Schedule/        # Today's route + day clock (default tab)
│   │   │   │   ├── Requests/        # Customer requests + internal tickets
│   │   │   │   ├── QuickPhotos/
│   │   │   │   └── Reports/
│   │   │   └── CrewApp.tsx
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.ts
│   │   └── package.json
│   │
│   └── customer/                    # Customer Portal (future)
│       └── CustomerApp.tsx
│
├── server/                          # Node.js + Express + TypeScript API
│   ├── src/
│   │   ├── middleware/
│   │   │   ├── auth.ts              # BetterAuth JWT verification
│   │   │   ├── tenant.ts            # RLS tenant context (SET app.current_tenant)
│   │   │   ├── roles.ts             # Role-based access control
│   │   │   └── errorHandler.ts
│   │   ├── routes/
│   │   │   ├── auth.ts
│   │   │   ├── customers.ts         # Read from local cache (synced from HubSpot)
│   │   │   ├── properties.ts
│   │   │   ├── bids.ts
│   │   │   ├── contracts.ts
│   │   │   ├── schedule.ts
│   │   │   ├── timeclock.ts
│   │   │   ├── invoices.ts
│   │   │   ├── reports.ts
│   │   │   ├── service-offers.ts      # CRUD for service offers, customer approval endpoint (token-based)
│   │   │   ├── hubspot.ts            # OAuth callback, manual sync trigger, webhook receiver
│   │   │   ├── docusign.ts           # OAuth callback, envelope creation, webhook receiver
│   │   │   ├── quickbooks.ts         # OAuth callback, invoice/payment push
│   │   │   └── admin.ts
│   │   ├── services/                # Business logic (imports from calculation-engine package)
│   │   │   ├── hubspotSync.ts       # Poll HubSpot contacts, upsert local cache, write-back summaries
│   │   │   ├── docusignService.ts   # Create envelopes, handle signing webhooks
│   │   │   ├── quickbooksSync.ts    # Push invoices and payments to QBO
│   │   │   ├── signingService.ts    # Built-in signature: generate signed PDFs with embedded signature
│   │   │   ├── serviceOffers.ts    # Offer lifecycle (create, send, approve, decline, expire, convert to ticket)
│   │   │   ├── calendar.ts          # Google Calendar API sync (optional)
│   │   │   ├── pdf.ts               # PDF generation
│   │   │   └── notifications.ts     # SMS/email sending + log to HubSpot timeline
│   │   ├── db/
│   │   │   ├── pool.ts              # PostgreSQL connection pool
│   │   │   ├── migrations/          # Database schema migrations
│   │   │   └── queries/             # Parameterized SQL queries
│   │   └── app.ts                   # Express app setup
│   ├── Dockerfile                   # For container deployment
│   ├── package.json
│   └── .env
│
├── database/
│   └── migrations/
│       ├── 001_initial_schema.sql
│       ├── 002_enable_rls.sql       # RLS policies for all tables
│       ├── 003_add_scheduling.sql
│       └── ...
│
├── turbo.json                       # Turborepo config (or nx.json)
├── package.json                     # Root workspace config
├── tsconfig.base.json               # Shared TypeScript config
└── docs/
    ├── architecture.md              # This document
    ├── pipeline-design.md
    ├── api-reference.md
    └── deployment.md
```

**Monorepo benefits:**
- `packages/shared` types are imported by both `apps/platform` and `apps/crew` and `server/` — change a type once, TypeScript catches mismatches everywhere
- `packages/ui` component library is shared but each app can compose different layouts
- `packages/calculation-engine` is the extracted business logic from estimate.html — used by both the API (for ticket generation, earned value) and the frontend (for live bid calculations)
- Each app can be built and deployed independently while sharing code

---

## Cost Estimates (Starting Out)

| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| Managed PostgreSQL | $50-75 | Cloud-managed instance; dev environments can be cheaper but budget for this range in production |
| Container hosting (API) | $0-15 | Serverless containers — free tier covers light usage, pay per request after |
| File storage (S3/Blob) | $0-5 | Photos and PDFs, pennies per GB |
| BetterAuth | $0 | Self-hosted, open source |
| HubSpot CRM | $0-20 | Free tier for up to 1M contacts; Starter at $20/seat if you need more custom properties |
| QuickBooks Online | $0 | Tenants use their own QBO subscription; your platform just pushes data via API |
| DocuSign | $0 | Optional — tenants who want it connect their own account; built-in signing is free |
| Frontend hosting | $0 | Static hosting free tiers are generous |
| Domain name | $12/year | Custom domain for the platform |
| **Total starting cost** | **~$55-120/month** | Scales with usage |

When you start charging other companies (Phase 6), even 2-3 customers at $99-199/month covers your infrastructure costs many times over.

### Build Estimate
The current prototype is ~26k lines across 3 HTML files. Production TypeScript/React will likely be **~100k lines** including the API, shared types, component library, tests, and migrations. With Claude Code on the premium tier ($200/month) and this architecture document as the spec, **a solo developer could realistically spin this up in under 2 weeks**. The business logic (calculation engine, takeoff pipeline, scheduling) is already proven in the prototype — the migration is infrastructure, not invention.

---

## Migration Strategy (Current → New)

You don't have to stop using the current app while you build the new one. Here's the transition:

1. **Build the pipeline in the prototype first**: Add contract acceptance + ticket generation to estimate.html, add the schedule tab + time clock to crew.html. Validate the workflow with your crew before migrating to the new stack.
2. **Phase 0**: Set up the monorepo + TypeScript + BetterAuth + PostgreSQL with RLS + container API alongside the old prototypes. Keep using the HTML prototypes daily.
3. **Extract the calculation engine first**: Port the bid calculator, takeoff pipeline, and scheduling logic into `packages/calculation-engine` as TypeScript. Test every function against the prototype outputs — the numbers must match exactly.
4. **When Phase 0 is done**: Switch the crew to the new React app. If something breaks, they can fall back to crew.html.
5. **Data migration**: Write a one-time script to move data from Google Sheets to PostgreSQL.
6. **Keep index.html running**: The customer service request form can stay on GitHub Pages and POST to the new API instead of Apps Script. Migrate it to the React customer portal later.
7. **Google Calendar**: Optional sync target. Use Apps Script `CalendarApp` for the prototype, migrate to the Calendar API on the new API later.
8. **Preserve business logic**: The calculation engine, takeoff pipeline, production rates, and billing logic from estimate.html extract directly into TypeScript service modules. Test new calculations against the prototype to ensure accuracy.

---

## Key Principles

1. **Tenant isolation is non-negotiable** — every query, every API route, every file access must be scoped to the tenant. PostgreSQL Row Level Security (RLS) enforces this at the database level — set `tenant_id` once per request and every query is automatically filtered. This is the foundation of trust for a multi-company platform. Implement it in the first migration, not as a retrofit.

2. **Desktop-first platform, mobile-first crew app** — the management platform (bidding, scheduling, invoicing, CRM, reports, admin) is desktop-first because that's where managers and owners work. A separate Crew App is mobile-first for field work: schedule/route, clocking in/out, customer requests, site reports, quick photos. The Crew App should feel native on iPhone — fast, offline-capable, and usable with one hand.

3. **Offline-capable where it matters** — time clock, today's schedule, and customer requests should work offline (cache in localStorage, sync when back online). Other features can require connectivity.

4. **Real-time feedback** — timers tick, calculations update as you type, schedules refresh. The app should feel alive.

5. **Data flows downhill** — Bid → Contract → Schedule → Time Entry → Invoice → Financial Report. Each step feeds the next. Build the pipeline so data moves through the system with minimal manual entry.

6. **Earned revenue is the source of truth** — invoiced revenue is cash flow; earned revenue is reality. Every completed ticket adds to earned revenue based on the actual work value. Monthly financials compare earned vs. invoiced to reveal deferred revenue, underwater properties, and true profitability. The contract total always equals the sum of all ticket earned values.

7. **Connect the channels** — customer requests (from index.html) surface to crew leaders when they arrive at a property. Customer data from HubSpot flows into bids and contracts. Platform events flow back to HubSpot timeline. Stripe handles payments. The systems talk to each other so no one has to enter the same data twice.

8. **Security from day one** — BetterAuth for authentication, HTTPS everywhere, parameterized SQL queries (no injection), RLS for tenant isolation, role-based access, API rate limiting. TypeScript catches type errors at compile time.

9. **AI as a teammate, not a gimmick** — Claude powers help, feature prototyping, and translation. It should feel like having a knowledgeable coworker available 24/7, not a chatbot bolted on.

10. **Community-driven evolution** — users shape the product through the feature sandbox. The best ideas come from people using the tool in the field every day. Build the pipeline to capture, review, and ship those ideas.

11. **Integrate, don't build — and make it seamless** — use best-in-class tools for what they do best: HubSpot for CRM, Stripe for payments, Twilio for SMS, SendGrid for email. Your platform owns what's unique to landscape operations: property measurements, production rates, bid calculations, scheduling, time tracking, earned revenue. Never build what you can integrate. But every integration must be **effortless to connect and invisible in daily use**. The goal: a landscape company owner connects HubSpot in 30 seconds, connects Stripe in 30 seconds, and never thinks about the integrations again. Eliminate all friction. Leave people wondering why they didn't use this platform sooner. It must change their life for the better.

12. **Validate in the prototype, then migrate** — the HTML prototypes are the proving ground. Build new features there first, validate with real crew usage, then migrate to the React/PostgreSQL stack. Don't rebuild infrastructure before confirming the workflow is right.

---

## What to Do Right Now

1. **Download this document** — it's your north star.
2. **Keep using crew.html, estimate.html, and index.html** — they work. Don't break what's working while you build new features.
3. **Finish the prototype pipeline**:
   - ✅ Combined Apps Script (Estimating + Text My Team in one spreadsheet)
   - ✅ Crew Members sheet with crew naming (MNT Crew 1)
   - ✅ Schedule tab with day clock, multi-ticket job clocks, stop cards, request alerts, day summary
   - ✅ **PIN-based crew check-in** with `verifyPin` endpoint, sub member support, object-based `checkedInMembers`
   - ✅ **Multi-ticket simultaneous clocking** with per-service tracking, partial carry-over, elapsed timers in stop cards
   - ✅ **Clock-out decision modal** with Complete/Return Later, per-service audit trail
   - ✅ Time Entries sheet with saveTimeEntry + updateTimeEntry (day_clock, job, indirect, service)
   - ✅ Crew-hours display (man-hours ÷ crew size) + budgeted indirect time from travelHours
   - ✅ **Contract finalization UI in estimate.html** — "Finalize Estimate" flow that generates tickets from bid services
   - ✅ **Estimate Revision & Re-Finalize workflow** — three-status lifecycle (Draft/Revision/Finalized), contract update instead of duplicate, future ticket regeneration, revision count tracking
   - ✅ **Ticket generation logic** — three date distribution strategies: `generateSeasonalMowingDates()` (weekly Apr–Oct, biweekly Nov–Mar; fills dormant gaps for higher targets (e.g. 52), trims dormant dates for lower targets), `generateWeeklyDates()` (every week, 50-54 visits), `generateSimpleScheduleDates()` (even distribution). Item-level `itemVisits` override, ticket bundling by date, earned value with penny reconciliation, `previewTickets()` breakdown
   - ✅ **GPS capture** at clock in/out — `captureGPS()` with high accuracy at 11 capture points (travel, day, ticket start/complete). Coordinates as `latIn/lngIn/latOut/lngOut`
   - ✅ **Route management view** — day/week/month views with drag-drop reordering, crew filter, bulk skip day for weather/holidays, "Needs Reschedule" queue with badge count and per-ticket reschedule controls
   - 🔶 **Earned revenue dashboard** — monthly earned vs collected chart, contract table, deferred revenue, completion % all built; **remaining: monthly P&L approximation**
4. **Decide on cloud provider** — AWS or Azure. The architecture works on either. Pick based on your comfort level or your dev's experience.
5. **Add IRR/CON/ENH division catalogs** — extend the item and service catalogs for irrigation, construction, and enhancement divisions
6. **Then start Phase 0 with a code agent** — give it this document plus your existing code. Recommended: **Claude Code on the premium tier ($200/month)**. OpenAI's Codex is also strong. Given the level of project detail in this document and the proven business logic in the prototype, **a solo developer with Claude Code could realistically build the full production stack in under 2 weeks**. ~29k lines of prototype → ~100k lines of production TypeScript is very doable when the spec is this detailed.
7. **Set up the monorepo first** — `packages/shared` types + `packages/ui` components + `packages/calculation-engine` (extracted from estimate.html) + `apps/platform` + `apps/crew` + `server/`
8. **Enable RLS early** — it's simple to implement at project start and prevents data leaks from day one. Retrofitting is harder.
9. **The iOS design system you already have** — apply those design principles to the new React crew app from the start.
10. **The calculation engine you already have** — the business logic is the hard part and it's done. Extract it into `packages/calculation-engine` as TypeScript and test against the prototype outputs. The infrastructure is the part Claude Code handles step by step.

All the work you've done designing features is not wasted. The features are the hard part. The infrastructure is the part that gets migrated.
