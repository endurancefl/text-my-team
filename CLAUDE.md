# Endurance Services - Estimating Platform

## Project Structure
- Single-file HTML app: estimate.html
- Hosted on GitHub Pages at endurancefl.github.io
- Layout: sidebar + main-content with multiple .view panels toggled via showView()

## Critical Rules
- NEVER break existing functionality when making changes
- This is a production app — test all 14 sidebar pages after any layout change
- The app uses a single HTML file with ~18,000 lines. Be careful with closing tags.
- **Always update `cloud-function/marvin-knowledge.md`** when adding features, changing calculations, adding items/services, or modifying business rules. This file is MARVIN's brain — it gets loaded into the AI system prompt at runtime. Redeploy Lambda after changes.

## CSS/Layout Bug Debugging Rules
1. **Always check the actual DOM first** — run `parentElement.children.length` and log each child's className and clientHeight. The browser's HTML parser may restructure your DOM due to mismatched tags.
2. **Never blindly adjust CSS for scroll/layout issues.** Before changing any CSS, add a diagnostic that logs the full height chain (clientHeight, scrollHeight, overflow, display) for every container from the root to the broken element.
3. **Count `<div>` opens vs `</div>` closes** when something breaks. Use a script to trace nesting depth from a known parent. A single stray `</div>` can cascade and restructure the entire page.
4. **Check for duplicate function names.** In a large single-file app, a function defined twice means only the LAST definition runs. `document.querySelector` finds the FIRST matching element. Both can silently target the wrong thing.
5. **Verify your changes actually deployed.** Add a visible marker (e.g., `document.title = 'DEBUG BUILD vX'`) to confirm the browser is loading fresh code before debugging further.
6. **When grid/flex layout gives unexpected sizes**, check how many children the container actually has. Implicit grid rows from unexpected children can steal all the space from `1fr` tracks.

## Known Issues / Lessons Learned
- **Feb 2026 — `let` temporal dead zone**: Declaring a `let` variable after its first use silently kills the entire `<script>` block. No errors in console, buttons just disappear. Always declare state variables near the top of the script.
- **Feb 2026 — Infinite recursion in updateHeaderActions()**: The Draft case called `showView('builder')` which called `updateHeaderActions()` again. Fixed by inlining the header HTML instead of calling showView.
- **Feb 2026 — Stray `</div>` fixed**: A stray `</div>` in property-card-body (line ~311) was removed. The `.main-body` CSS was restored from `display: contents` to a proper flex container, and `.view.active` no longer uses absolute positioning.

---

# Text My Team — Project Instructions for Claude Code

## File Overview

| File | Purpose | Lines |
|------|---------|-------|
| `crew.html` | Crew leader mobile app (HTML + JS) | ~8,440 |
| `crew.css` | All CSS for crew.html (extracted) | ~4,210 |
| `index.html` | Customer service request portal | ~3,100 |
| `estimate.html` | Bidding & estimating tool (MNT + ENH divisions) | ~23,700 |
| `css/estimate.css` | All CSS for estimate.html | ~8,050 |
| `sign.html` | Standalone contract e-signature page | ~686 |
| `backend/combined-apps-script.js` | Google Apps Script backend | ~6,112 |
| `docs/platform-architecture.md` | Living architecture doc (MUST update on every change) |

## crew.html Structure Map

CSS lives in `crew.css` (separate file). crew.html contains only HTML + JS.

### HTML Body (lines 18-852)
```
18-37     Offline banner, undo toast, iOS toast alert
38-49     Login screen (phone input, lang toggle)
50-170    Dashboard (header, day controls, stop cards container, stats bar, requests list)
143-170   Bottom tab bar (Schedule, Requests, Report Issue, Reports)
173-235   Sheets: Reports selection, Settings
236-290   Overlays: Crew Check-In (push), PIN Entry (bottom sheet), Member Assignment (bottom sheet)
304-340   Clock-Out modal (push), Edit Crew modal
340-377   Reassignment wizard, Complete Job modal, Day Summary modal
377-475   Request Detail modal
476-570   Submit Ticket (Report Issue) modal
573-720   Site Report Wizard (multi-step)
721-852   Before & After Wizard
```

### JavaScript (lines 853-8437)

#### Config & State (853-906)
```
853       <script> tag
878       GOOGLE_SHEETS_URL
896       DEMO_MODE flag
897-906   State variables (currentCrewPhone, currentCrewName, checkedInMembers, todayTickets, activeTickets, etc.)
```

#### Translation System (907-1250)
```
907       currentLang (from localStorage 'preferredLang')
908-1203  translations object (en + es, ~150 keys)
1204      t(key) function
1208      updateLanguage() — traverses data-i18n, rebuilds UI
1237      handleLangToggle()
```

#### Utilities (1250-1510)
```
1252      queueableFetch() — offline-aware fetch wrapper
1289      updateOfflineBanner()
1316      splitTimeEntry() — closes old entry, opens new on crew change
1371      haptic() — vibration feedback
1395      iosAlert() — toast notification
1399      iosConfirm() — action sheet
1443      iosPrompt() — alert dialog with input
1504      timerTargetFired tracking
```

#### Demo Mode (1507-1635)
```
1507-1635 Mock fetch, demo data (5 crew, 5 tickets), auto-login
```

#### Tab Switching & Pull-to-Refresh (1637-1780)
```
1637      switchTab()
1695      Pull-to-refresh touch handlers
```

#### Schedule & Rendering (1780-2140)
```
1669      loadSchedule() — fetches crew schedule, processes tickets
1787      renderStopCards() — builds entire schedule tab
1877      renderPropertyGroupCard() — property group with tickets
1982      renderTicketSubRow() — individual ticket in collapsed view
2047      renderActiveTicketExpanded() — active ticket with service controls, progress bars, time labels
2140      togglePropertyGroup()
```

#### Check-In Flow (2237-2540)
```
2237      showCrewCheckIn()
2330      showPinEntry() / showPinEntryForAdd() / showPinEntryForNext()
2450      submitPin() / verifyMemberPin()
2500      addMemberMidDay()
2520      updateStartDayButton()
```

#### Edit Crew & Crew Management (2538-2930)
```
2538      showEditCrewModal()
2650      removeCrewMember()
```

#### Request Alerts at Property (2927-2985)
```
2927      checkPropertyRequests() — yellow banner with Handle It / Office buttons
```

#### Complete Job & Day End (2988-3500)
```
2988      showCompleteJob()
3100      skipStop()
3140      cancelStartedTicket()
3182      skipProperty()
3209      endDay()
3305      showDaySummaryModal()
3440      updateScheduleDaySummary()
```

#### Start Ticket & Assignment (3543-3935)
```
3543      startTicket() — sequential property enforcement
3583      autoStartTicket()
3600      formatMinutes() — H:MM format
3617      getServiceEstHours()
3630      getServiceProgress()
3679      formatEstMin() / formatRemainingMin() / getServiceRemainingMin() / getServiceRemainingWithExtra()
3652      showMemberAssignment() — ticket-level crew picker
3710      confirmStartTicket()
3870      confirmEditCrew()
```

#### Per-Service Clocking & Reassignment Wizard (3935-4600)
```
3935      showServiceMemberAssignment()
4009      confirmStartService()
4100      completeService()
4300      confirmEditServiceCrew()
4370      showServiceReassignmentModal()
4398      renderReassignWizard() — time-aware "Where to Next?" with projections
4477      assignMemberToService() — haptic + success animation
4560      updateServiceProgressBars() — progress bars + remaining time labels
```

#### Clock-Out Flow (4591-4810)
```
4591      clockOutTicket()
4626      showClockOutModal()
4672      confirmClockOut()
```

#### Crew Reassignment - Ticket Level (4808-4920)
```
4809      getFreedMembers()
4824      showReassignmentModal()
4835      refreshReassignmentContent()
4890      refreshReassignmentModal()
4903      refreshServiceReassignmentContent()
```

#### Login & Dashboard Init (5006-5090)
```
5006      Login button handler
5037      showDashboard()
5045      loadRequests()
```

#### Requests Tab (5088-5400)
```
5088      renderRequests() — filtered list with empty states
5145      updateStats()
5160      Filter handler (open/all/completed)
5178      openRequestModal()
5300      Request status updates, SMS deep-linking
```

#### Report Issue / Submit Ticket (5798-6070)
```
5798      Submit Ticket flow
```

#### Quick Photos / Inspection (6072-6400)
```
6072      Inspection photo upload flow
```

#### Site Report Wizard (6415-7600)
```
6415      Full site report: property search, photo capture, categories, PDF generation
```

#### Before & After Reports (7606-8437)
```
7606      Before & After: pulls prior photos, pairs with new, generates comparison PDF
```

## Common Code Patterns

### Service name extraction (used 10+ places)
```javascript
typeof s === 'string' ? s : (s.serviceName || s.proposalName || s.sectionName || s.name || s.service || '')
```

### Member name extraction (used everywhere)
```javascript
typeof m === 'string' ? m : m.name
```

### Key runtime state objects
```javascript
activeTickets[ticketId] = {
  startTime,          // Date — effective start (offset for partial resume)
  interval,           // timer interval ID
  assignedMembers,    // [{name, pin, role, defaultCrew}, ...]
  serviceClocks,      // {serviceName: {startTime, endTime, assignedMembers, manHoursConsumed, entryId}}
  completedServices,  // [serviceName, ...]
  manHoursConsumed,   // accumulated man-minutes from prior crew segments
  phaseStartTime,     // Date — when current crew segment started
  entryId             // backend time entry ID for this ticket
}

checkedInMembers = [{name, pin, role, defaultCrew}, ...]

todayTickets = [{
  ticketId, propertyAddress, services, totalEstHours,
  status,              // 'scheduled' | 'partial' | 'completed' | 'skipped'
  isShopTicket,        // true for synthetic Shop ticket
  completedServices,   // carried over for partial tickets
  elapsedBeforePause,  // seconds — for timer resume on partial
  stopOrder
}, ...]
```

### Translation pattern
```javascript
t('key')                                    // simple lookup
t('removeFromCrew').replace('{name}', name) // template replacement
```
Always add keys to BOTH `en` and `es` in the translations object.

### Time entry splitting pattern
When crew changes on a running service/ticket:
1. Calculate `segmentMinutes = (splitNow - svcClock.startTime) / 60000`
2. Accumulate: `svcClock.manHoursConsumed += segmentMinutes * oldCrewCount`
3. Call `splitTimeEntry()` to close old entry + open new one
4. Update `entryId` and `startTime` to the split point

### Rendering triggers
- `renderStopCards()` — rebuilds entire schedule tab. Call after any state change.
- `renderRequests()` — rebuilds requests tab.
- `updateLanguage()` — calls both + updates all static `data-i18n` elements.
- `updateServiceProgressBars(ticketId)` — called every second by ticket timer, updates progress bars + time labels.

### Time format
All times use H:MM format via `formatMinutes()` and `formatEstMin()`:
- 22 minutes = `0:22`
- 75 minutes = `1:15`
- Remaining: `0:22 left` or `0:12 over`

## crew.css Structure (~4,210 lines)

```
1-150     CSS variables (:root), dark mode overrides
150-500   Base layout, safe areas, login screen
500-800   Dashboard header, day controls, day clock banner
800-1200  Stop cards, property groups, ticket rows
1200-1500 Service rows, progress bars, remaining time labels
1500-1800 Buttons (ios-btn variants), inputs, textareas
1800-2100 Overlays (check-in, PIN entry, assignment, clock-out)
2100-2400 Edit crew, reassignment wizard (grouped list, tap feedback, success animation)
2400-2800 Modals (complete job, day summary, request detail)
2800-3200 Requests tab, filter buttons, empty states, stats bar
3200-3600 Tab bar, settings sheet, reports sheet
3600-4000 Site Report wizard, Before & After wizard
4000-4210 Pull-to-refresh, miscellaneous
```

## Testing

- `crew.html?demo=true` — full demo mode with mock data, no backend needed
- `crew.html?demo=true&lang=es` — test Spanish translations in demo mode (NOT YET IMPLEMENTED — use toggle)
- Toggle language via pill button on login screen or dashboard header
- Demo crew: Jake Miller/1111, Carlos Rivera/2222, Sam Thompson/3333, Dani Brooks/4444, Tyler Nguyen/5555

---

# Supplemental Instructions

## Prompt Archiving
When executing a feature implementation prompt, save the final version of the prompt to the `prompts/` folder before beginning work. Only archive prompts that are actually being implemented — not drafts reviewed for feedback. Create the `prompts/` directory if it doesn't already exist. Use a descriptive filename with the date, e.g., `prompts/2026-03-07-time-review.md`. This applies to any substantial prompt that drives a feature build — not quick one-off questions.

## Architecture Rules
- Both apps are single-file HTML with inline `<script>` blocks. No build step, no framework.
- All new CSS classes should be namespaced with a short prefix to avoid collisions (e.g., `tr-` for time review, `fin-` for financials).
- Views use `data-view="viewId"` on sidebar nav items. `showView(viewId)` handles switching. New views need: nav HTML, view HTML, title in the titles map, and a trigger block in `showView()`.
- Settings persist via `bidSettings` object → `settingsMap` → `saveBidSettings()` → Google Sheets.
- Backend actions use POST with `{ actionName: true, ...params }` for writes and GET with `?action=actionName&param=value` for reads.
- `showToast(message, type)` for notifications. Type = 'success' | 'error' | 'info'.
- Time entries use 12-hour clock strings ("8:00 AM"). Crew members stored as JSON string arrays.

## Code Style
- `let`/`const`, template literals, arrow functions mixed with `function` declarations
- `async`/`await` for fetch calls
- Section headers use: `// ═══════════════════════════════════════`
- No modifications to existing functions unless explicitly required by the task

## Apps Script Deployment
When the backend (`backend/combined-apps-script.js`) needs changes, always make edits to the local file, then copy the **entire file** to the user's clipboard (`pbcopy`) so they can paste it into Google Apps Script. The user manually replaces the script in the Google Sheets editor — there is no automated deploy.
