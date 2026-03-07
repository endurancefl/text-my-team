# Time Review, Payroll Export & Day Clock Alert — Implementation Prompt

## Overview

Add three connected features to `estimate.html` — the desktop management platform for Endurance Services (a landscape company in Orlando, FL):

1. **Time Review view** — managers review, edit, add, and delete crew time entries logged from the mobile crew app (`crew.html`)
2. **Payroll Export** — generate CSV files formatted for Inova Payroll upload (weekly, Mon–Sun pay period, submitted Wed, processed Fri)
3. **Day Clock Alert** — email the crew leader automatically when they forget to end the day after X hours

Both `estimate.html` and `crew.html` share the same Google Apps Script backend (`GOOGLE_SHEETS_URL`).

---

## Architecture Context

### How estimate.html works
- **Single-file app**: ~21,500 lines. HTML from lines 1–2737, one `<script>` block from line 2738–21513.
- **External CSS**: `css/estimate.css` (loaded in `<head>` at line 15)
- **Backend**: All API calls go to the `GOOGLE_SHEETS_URL` constant (Google Apps Script web app), already defined at line 2742.
- **View system**: Sidebar nav items have `data-view="viewId"`. Clicking calls `showView(viewId)` (line 11893) which:
  1. Toggles `.active` on sidebar nav items
  2. Shows `#view-{viewId}` and hides all other `.view` divs
  3. Sets the header title from a titles map at line 11932
  4. Calls view-specific init/load functions starting at line 11967
- **Settings system**: `bidSettings` object (line 2829) holds all settings. Settings inputs map to `bidSettings` keys via `settingsMap` (line 18849). Changes fire on `input` events and update `bidSettings` in real time. Clicking "Save Settings" calls `saveBidSettings()` (line 10534) which POSTs `{ updateBidSettings: true, ...settings }`. Settings are loaded on init via `getInitData` (line 8026) and merged with: `bidSettings = { ...bidSettings, ...data.bidSettings.settings }`. The form is populated by `renderSettingsForm()` (line 12381).
- **Toast notifications**: `showToast(message, type)` where type = 'success' | 'error' | 'info'
- **UI patterns**: `sched-toolbar` + `sched-filters` for toolbar bars. `btn btn-primary` / `btn btn-secondary` for buttons. `form-input` / `form-select` for inputs. `modal-overlay` > `modal` > `modal-header` / `modal-body` / `modal-footer` for modals. `settings-card` > `settings-card-header` + `settings-card-body` > `settings-row` for settings cards.

### Time Entry Data Structure (from the Google Sheets backend)
Each time entry row has these columns:
```
Entry ID           — unique string (e.g., "ENT-abc123")
Crew               — crew name (e.g., "Crew A", "Gio's Crew")
Date               — "YYYY-MM-DD"
Entry Type         — "day_clock" | "job" | "service" | "indirect"
Ticket ID          — ticket reference (or "SHOP" for shop time)
Property Address   — full address string
Service Name       — service name (only for entryType "service")
Duration Type      — "fixed" | null (see note below)
Clock In           — "8:00 AM" (12-hour with AM/PM)
Clock Out          — "8:45 AM" (or empty string if still open)
Duration Minutes   — integer
Crew Members       — JSON array string: '["Juan","Carlos","Mike"]'
Member Count       — integer
Notes              — free text
Lat In / Lng In    — GPS coordinates at clock-in
Lat Out / Lng Out  — GPS coordinates at clock-out
```

### Entry Types
- **day_clock**: One per crew per day. Marks the crew's overall day start/end. The `Crew Members` array = everyone checked in that day. NOT billable time — skip these in payroll calculations.
- **job**: Clock in/out for a stop at a property (ticket-level). Contains assigned members for that stop.
- **service**: Clock in/out for a specific service within a ticket (e.g., "Shrub Pruning" on ticket TKT-456). Contains members assigned to that specific service.
- **indirect**: Auto-generated travel time between stops.

### Duration Type "fixed"
Some service entries have `durationType: "fixed"`. In crew.html, fixed-duration services have a pre-set time budget that doesn't scale with crew size — adding more crew members doesn't speed them up (e.g., irrigation inspections). When editing time entries in the Time Review:
- Fixed-duration entries should display a small "Fixed" badge next to the type badge
- **Editing clock in/out times is still allowed** (the actual time spent may differ from budget), but the UI should show a subtle note like "Fixed-duration service" so managers understand the context

### Time Entry Splitting
crew.html uses a `splitTimeEntry()` function that closes one entry and opens a new one when crew members change mid-service (e.g., a member gets reassigned to a different service). This means a single ticket can have **multiple sequential entries with different member arrays**. These will appear as separate rows in the Time Review, which is correct, but consider adding a visual indicator (e.g., a subtle "split" icon or a connecting line) when consecutive entries for the same ticket/service have adjacent clock-out/clock-in times (within 1 minute), so managers understand these are continuations rather than separate work.

### Shop Ticket Identification
In crew.html, shop tickets use `ticketId: 'SHOP'` (strict equality). However, for defensive coding, **use `ticketId === 'SHOP' || (ticketId && ticketId.startsWith('SHOP'))` when classifying Shop entries**, in case future changes append suffixes.

### Critical: Per-Member Hour Expansion
A single time entry with `memberCount: 3` and `durationMinutes: 60` means 3 people each worked 60 minutes. For the **display table**, expand each entry to one row per member, each showing the full wall-clock duration. For **payroll**, each member gets `durationMinutes / 60` hours credited. This is NOT divided by member count — each person present worked the full duration.

### Existing Backend Actions (verified in crew.html)
- **`saveTimeEntry`** — creates a new time entry (POST with `{ saveTimeEntry: true, crew, date, entryType, ticketId, propertyAddress, clockIn, crewMembers, memberCount, notes, ... }`). Used extensively.
- **`updateTimeEntry`** — updates fields on an existing entry (POST with `{ updateTimeEntry: true, entryId, clockOut, durationMinutes, ... }`). Used extensively.
- **`deleteTimeEntry`** — deletes an entry (POST with `{ deleteTimeEntry: true, entryId }`). Used in `cancelStartedTicket()` at lines 3660, 3669 in crew.html. Confirmed to exist in backend.
- **`getCrews`** — returns crew name list (GET `?action=getCrews`, returns `{ success: true, crews: ["Crew A", "Crew B"] }`). Used by Production view at line 20824.
- **`getCrewSchedule`** — returns crew roster, but **requires the crew leader's phone number** as a parameter (GET `?action=getCrewSchedule&phone=PHONE&date=DATE`). crew.html has the phone from login, but estimate.html does not, and `getCrews` only returns crew names — not leader phones. **This means you cannot use `getCrewSchedule` directly from the Time Review.** You need a new endpoint (see `getCrewMembers` below).

---

## FEATURE 1: Time Review View

### 1A. Sidebar Nav Item
**Insert after line 86** (closing `</div>` of Financials nav item) and **before line 87** (`<!-- CONFIGURATION -->`):
```html
<div class="nav-item" data-view="timeReview" id="time-review-nav">
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
    <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
  </svg>
  <span>Time Review</span>
</div>
```

### 1B. View HTML
**Insert after line 1578** (closing `</div>` of `view-financials`) and **before line 1580** (`<!-- CONTACTS VIEW -->`).

The view contains:

**Toolbar** (`sched-toolbar` class):
- Week navigator: `← Prev` button, week label (e.g. "Mon Mar 2 — Sun Mar 8, 2026"), `Next →` button
- Crew filter dropdown (populated from `getCrews`)
- Member filter dropdown — populated from BOTH the crew roster AND unique names in loaded entries (see Member Filter note below). Default: "All Members"
- Refresh button
- Payroll status badge — contextual: "Submit by Wed" (orange) if reviewing current or upcoming week, "✓ Ready to Export" (green) if all entries have clock outs, etc.
- Two export buttons: "Export Payroll" (primary, generates Inova CSV) and "Export Detail" (secondary, granular CSV)

**Member Filter Behavior**: The member dropdown should show all roster members for the selected crew(s), not just members who have entries that week. Members with zero hours should appear in the dropdown with "(0h)" appended so managers can spot who's missing. Use `getCrewMembers` (new endpoint) to fetch the full roster. If a crew filter is set, only show that crew's roster; if "All Crews", show all rosters.

**Open Day Clock Warning Banner** — if any `day_clock` entries in the selected week have no `Clock Out`, show a prominent yellow warning banner listing which crews still have open day clocks with elapsed time. Include a "Close Clock" button that prompts for a clock-out time.

**Summary cards row** (`tr-summary-cards`):
- Total Hours (all billable types)
- Direct Hours (job + service, excluding SHOP)
- Travel Hours (indirect)
- Shop Hours (job entries where SHOP — see Shop identification rule)
- Members (unique count)

**Time entries table**:
| Column | Notes |
|--------|-------|
| Date | Day of week + short date (e.g., "Mon 3/2") |
| Crew | Crew name |
| Member | Individual person name (one row per person) |
| Type | Color badge: Direct (green), Travel (orange), Shop (blue). Add small "Fixed" sub-badge for durationType === 'fixed' |
| Property | Shortened — text before first comma |
| Service | Only populated for `entryType === 'service'`. Show split indicator (e.g., ↔ icon) when consecutive entries for the same ticket+service have adjacent times |
| Clock In | Editable when in edit mode |
| Clock Out | Editable when in edit mode |
| Hours | Calculated to 2 decimal places |
| Notes | Truncated with hover/title for full text |
| Actions | Edit pencil icon, Delete trash icon |

**Day separator rows**: Between each day's entries, a header row with the day name and a subtotal row with total hours.

**Add Entry button**: At the top-right of the table area.

### 1C. Add Entry Modal
Place next to other modals. Use the standard modal pattern. Fields:
- Crew (dropdown, populated from `getCrews`)
- Date (date picker, constrained to current week)
- Type (Direct / Travel / Shop)
- Property (text input)
- Clock In (time input)
- Clock Out (time input)
- Members (multi-select checkboxes — **populated from `trCrewRoster[selectedCrew]`** via the `getCrewMembers` endpoint, showing the full roster with names and roles)
- Notes (textarea)

### 1D. showView Integration
**Line 11932 — titles map**: Add `'timeReview': 'Time Review'`

**After line 11997** (production trigger block): Add:
```javascript
if (viewId === 'timeReview') {
  initTimeReview();
}
```

### 1E. JavaScript
Add a new section **before line 20789** (before the `// PRODUCTION RATES VIEW` section):

```javascript
// ═══════════════════════════════════════════════════════════════
//  TIME REVIEW & PAYROLL EXPORT
// ═══════════════════════════════════════════════════════════════
```

#### State Variables
```javascript
let trData = null;              // Raw entries array from backend
let trWeekStart = null;         // Monday of selected week (Date)
let trCrewFilter = 'all';
let trMemberFilter = 'all';
let trEditingEntryId = null;    // Entry being inline-edited
let trCrewRoster = {};          // crewName → [{ name, role }] from getCrewMembers
```

#### Core Functions

**`initTimeReview()`**
- Calculate the default payroll week: if today is Monday or Tuesday, default to the **previous** week (Mon–Sun), since that's the week being reviewed for Wednesday submission. Otherwise show the current week.
- Populate crew filter (fetch `?action=getCrews`)
- Fetch crew roster via `getCrewMembers` (new endpoint — see spec in comment block) — store in `trCrewRoster`
- Call `loadTimeReview()`

**`trSetWeek(offset)`** — shift `trWeekStart` by `offset * 7` days, update the week label, call `loadTimeReview()`

**`loadTimeReview()`**
- Fetch: `GOOGLE_SHEETS_URL + '?action=getTimeEntries&startDate=' + startDate + '&endDate=' + endDate + '&crew=' + encodeURIComponent(crew)`
- **This backend endpoint may not exist yet.** Include a detailed comment block documenting the expected request/response contract (see below). Handle the error case gracefully — if the response isn't valid JSON or returns `success: false`, show a message: "The getTimeEntries backend endpoint needs to be added. See the developer notes in the source for the expected API format."
- Expected response format:
```javascript
/*
 * ──────────────────────────────────────────────────────────────
 * BACKEND ENDPOINT NEEDED: getTimeEntries
 * ──────────────────────────────────────────────────────────────
 * Add this handler to the doGet() router in your Apps Script:
 *
 * Request:
 *   GET ?action=getTimeEntries
 *       &startDate=2026-03-02
 *       &endDate=2026-03-08
 *       &crew=all           (or specific crew name)
 *
 * Response:
 * {
 *   success: true,
 *   entries: [
 *     {
 *       entryId: "ENT-abc123",
 *       crew: "Crew A",
 *       date: "2026-03-02",
 *       entryType: "job",
 *       ticketId: "TKT-456",
 *       propertyAddress: "123 Oak St, Orlando, FL",
 *       serviceName: "",
 *       durationType: "",
 *       clockIn: "8:00 AM",
 *       clockOut: "8:45 AM",
 *       durationMinutes: 45,
 *       crewMembers: '["Juan","Carlos"]',
 *       memberCount: 2,
 *       notes: ""
 *     }
 *   ]
 * }
 *
 * Implementation: Read from the TimeEntries sheet, filter by
 * date range and crew, return all matching rows as JSON.
 * Include ALL entry types (day_clock, job, service, indirect)
 * — the frontend handles filtering.
 * ──────────────────────────────────────────────────────────────
 */

/*
 * ──────────────────────────────────────────────────────────────
 * BACKEND ENDPOINT NEEDED: getCrewMembers
 * ──────────────────────────────────────────────────────────────
 * The existing getCrewSchedule endpoint requires a crew leader's
 * phone number (used by crew.html after login), but estimate.html
 * doesn't have crew leader phones — getCrews only returns names.
 *
 * Add this handler to the doGet() router:
 *
 * Request:
 *   GET ?action=getCrewMembers
 *       &crew=all           (or specific crew name)
 *
 * Response:
 * {
 *   success: true,
 *   crews: {
 *     "Crew A": [
 *       { name: "Juan Rodriguez", role: "Leader" },
 *       { name: "Carlos Mendez", role: "Member" },
 *       { name: "Mike Johnson", role: "Member" }
 *     ],
 *     "Crew B": [
 *       { name: "Sam Thompson", role: "Leader" },
 *       { name: "Dani Brooks", role: "Member" }
 *     ]
 *   }
 * }
 *
 * Implementation: Read from the Crew Members sheet, group by
 * "Default Crew" column, return name and role for each member.
 * If crew param is not "all", filter to that crew only.
 * Do NOT include PINs or emails in the response — those are
 * sensitive and not needed by the frontend.
 * ──────────────────────────────────────────────────────────────
 */
```
- After loading, populate the member filter: combine names from loaded entries WITH names from `trCrewRoster` (fetched via `getCrewMembers`). Roster members with no entries that week show "(0h)" in the dropdown.
- Call `renderTimeReview()`

**`renderTimeReview()`**
- Filter by `trCrewFilter` and `trMemberFilter`
- **Skip `day_clock` entries** for the main table — BUT check for open day_clocks (no `clockOut`) and render the warning banner if found
- Expand remaining entries to per-member rows: parse `JSON.parse(entry.crewMembers || '[]')`. **Normalize member names with `.trim()`** before display and grouping to avoid mismatches from inconsistent spacing.
- Each member row shows hours = `durationMinutes / 60` (full wall-clock time)
- Group rows by date, render day header rows and day subtotal rows
- Detect **split entries**: when consecutive entries share the same `ticketId` (or `ticketId` + `serviceName`) and the previous entry's `clockOut` matches the current entry's `clockIn` (within 1 minute tolerance), add a visual split indicator (↔ icon or connecting line)
- Show "Fixed" sub-badge on entries where `durationType === 'fixed'`
- Calculate and render summary cards
- Classify types: `entryType === 'indirect'` → Travel; SHOP identification (see rule above) → Shop; everything else → Direct

**`trEditEntry(entryId)`** — toggle inline editing: replace clock-in/out text with `<input type="text">` fields. Show Save/Cancel in Actions column. If `durationType === 'fixed'`, show a subtle note "Fixed-duration service" below the inputs. Note: inline editing covers clock times only. **Editing crew members on an existing entry is out of scope for v1** — if a manager notices the wrong person listed, they should delete and re-add. This can be revisited later.

**`trSaveEntry(entryId)`** — validate times (clock out must be after clock in), calculate new duration, POST:
```javascript
{ updateTimeEntry: true, entryId, clockIn, clockOut, durationMinutes }
```
Show toast on success, reload data.

**`trDeleteEntry(entryId)`** — show a confirmation dialog that includes the entry's details so managers don't accidentally delete the wrong row: date, crew, member name(s), hours, property, and type. Example: "Delete entry?\n\nMon 3/2 · Crew A · Juan Rodriguez\n8:00 AM – 9:15 AM (1.25h)\n123 Oak St · Direct". On confirm, POST:
```javascript
{ deleteTimeEntry: true, entryId }
```
Show toast on success, reload data.

**`trCloseDayClock(entryId)`** — for the warning banner. Prompt for a clock-out time (default "5:00 PM"). **Validate that the entered time is after the entry's clock-in time** — reject with an error if not. Calculate duration, then POST `updateTimeEntry`, reload.

**`openTrAddModal()` / `closeTrAddModal()`** — show/hide the add entry modal. Populate crew dropdown from `getCrews`, member checkboxes from `trCrewRoster[selectedCrew]`. When the crew dropdown changes, re-populate the member checkboxes.

**`trSaveNewEntry()`** — gather form values, validate, POST:
```javascript
{
  saveTimeEntry: true,
  crew: selectedCrew,
  date: "YYYY-MM-DD",
  entryType: type === 'Travel' ? 'indirect' : 'job',
  ticketId: type === 'Shop' ? 'SHOP' : (type === 'Travel' ? 'TRAVEL' : 'MANUAL'),
  propertyAddress: address || '',
  clockIn: "8:00 AM",
  clockOut: "5:00 PM",
  durationMinutes: calculated,
  crewMembers: selectedMemberNames,
  memberCount: selectedMemberNames.length,
  notes: "Manual entry - " + notes
}
```
Note: Manual entries are always ticket-level (`entryType: 'job'`), not service-level. The Add Entry modal does not have a Service Name field — service-level granularity is only captured by the crew app in real time. If a manager needs to attribute time to a specific service, they should add a note explaining the context.

#### Time Parsing Helpers
```javascript
function trParseTime12(str) {
  // "8:00 AM" → minutes since midnight (480)
  // "1:30 PM" → 810
  // Handle edge cases: 12:00 AM = 0, 12:30 PM = 750
}
function trCalcDurationMinutes(clockInStr, clockOutStr) {
  // Returns integer minutes between two "H:MM AM/PM" strings
  // Handles overnight (clockOut < clockIn) by adding 24h
}
function trFormatTime12(minutesSinceMidnight) {
  // 810 → "1:30 PM"
}
```

---

## FEATURE 2: Payroll Export (Inova CSV)

### `trExportPayroll()`
Generates a CSV formatted for Inova Payroll's hours import.

**Steps:**
1. Use only entries from the selected week (Mon–Sun)
2. Skip `day_clock` entries
3. **Skip `indirect` (travel) entries for payroll** — travel time is operational overhead, not directly payable per-member hours. It's already captured in the total day clock. If the business wants travel time included in payroll, they should manually add entries via the Add Entry modal. (The Detail Export includes travel for internal records.)
4. Expand remaining entries (job + service) to per-member rows
5. **Normalize member names with `.trim()`** before grouping to prevent duplicates from spacing inconsistencies
6. **Group by member name + crew name** — a member may work with multiple crews in one week (e.g., borrowed for a day). Each member+crew combination gets its own rows so the Department column stays accurate.
7. **Calculate OT across the member's combined total** (all crews): sum ALL hours for that member across all crews. If total > 40, the overtime hours spill into OT rows. Attribute OT to the crew where the last hours were worked (chronologically). Example: Juan works 32h with Crew A and 10h with Crew B → Crew A gets 32h REG, Crew B gets 8h REG + 2h OT.
8. Pay Date = Friday of the selected week (payroll processing day)

**CSV columns:**
```
Employee Name,Employee ID,Pay Date,Hours Worked,Earnings Code,Department,Notes
```

**Example output:**
```csv
Employee Name,Employee ID,Pay Date,Hours Worked,Earnings Code,Department,Notes
Juan Rodriguez,,03/06/2026,32.00,REG,Crew A,
Juan Rodriguez,,03/06/2026,8.00,REG,Crew B,
Juan Rodriguez,,03/06/2026,2.00,OT,Crew B,
Carlos Mendez,,03/06/2026,38.50,REG,Crew A,
Mike Johnson,,03/06/2026,40.00,REG,Crew B,
Mike Johnson,,03/06/2026,1.75,OT,Crew B,
```

**Notes:**
- `Employee ID` left blank (Inova matches by name, or user can add IDs later). This is a generic format — the actual Inova template may differ per account. The user can adjust columns later.
- `Earnings Code`: "REG" for regular, "OT" for overtime
- `Department`: crew name
- File downloads as `Endurance-Payroll-YYYY-MM-DD-to-YYYY-MM-DD.csv`
- Use browser download: Blob → object URL → temporary `<a>` click

### `trExportDetail()`
Granular internal-records CSV — one row per entry per member:

```
Date,Day,Crew,Member,Type,Property,Service,Clock In,Clock Out,Hours,Notes
2026-03-02,Monday,Crew A,Juan Rodriguez,Direct,123 Oak St,Shrub Pruning,8:00 AM,9:15 AM,1.25,
2026-03-02,Monday,Crew A,Juan Rodriguez,Travel,,,9:15 AM,9:30 AM,0.25,
```

File: `Endurance-TimeDetail-YYYY-MM-DD-to-YYYY-MM-DD.csv`

---

## FEATURE 3: Day Clock Alert (Email)

When a crew leader forgets to end the day, an email fires after X hours. This is **server-side** — must work even if the app is closed.

### 3A. Settings UI (estimate.html)

**Add a new settings card** in `view-settings`. Insert after the MARVIN Knowledge Base card (after line 1207, before the "Save Settings" button div at line 1208):

```html
<div class="settings-card">
  <div class="settings-card-header">Day Clock Alerts</div>
  <div class="settings-card-body">
    <div class="settings-row">
      <span class="settings-row-label">Alert after hours</span>
      <input type="number" class="settings-input" id="setting-dayclock-alert-hours" step="0.5" min="0" max="24" placeholder="e.g., 10">
    </div>
    <p style="font-size: 11px; color: var(--gw-text-secondary, #5f6368); margin: 8px 0 0; line-height: 1.5;">
      When a crew's day clock has been running longer than this without being ended, an email alert is sent to the crew leader. Set to 0 to disable. Requires an Email column in the Crew Members sheet.
    </p>
  </div>
</div>
```

**Wire up the input** — add to `settingsMap` (line 18849):
```javascript
'setting-dayclock-alert-hours': 'dayClockAlertHours'
```

**Add default** to `bidSettings` (line 2829):
```javascript
dayClockAlertHours: 10
```

**Add to `renderSettingsForm()`** (line 12381):
```javascript
const alertEl = document.getElementById('setting-dayclock-alert-hours');
if (alertEl) alertEl.value = bidSettings.dayClockAlertHours || 10;
```

**Add to save payload** in the save-settings-btn handler (line 18886):
```javascript
dayClockAlertHours: bidSettings.dayClockAlertHours || 10
```

### 3B. Open Clock Detection in Time Review (frontend)

In `renderTimeReview()`, scan for `day_clock` entries with empty `clockOut`. Render warning banner with "Close Clock" button per crew.

### 3C. Backend — Google Apps Script Trigger

Include as a **ready-to-paste comment block** in the JavaScript section:

```javascript
/*
 * ══════════════════════════════════════════════════════════════
 *  BACKEND: Day Clock Alert — Google Apps Script
 * ══════════════════════════════════════════════════════════════
 *
 * SETUP:
 * 1. Open the Apps Script editor for your project
 * 2. Paste the checkOpenDayClocks function below
 * 3. Go to Triggers (clock icon) → Add Trigger:
 *    - Function: checkOpenDayClocks
 *    - Event source: Time-driven
 *    - Type: Minutes timer
 *    - Interval: Every 30 minutes
 * 4. Add an "Email" column to the Crew Members sheet.
 *    Crew leaders need email addresses at minimum.
 *
 * TIMEZONE NOTE: This function uses America/New_York for
 * formatting dates. When constructing Date objects from sheet
 * values, be aware that Apps Script's Date constructor may
 * interpret Sheet Date values in the spreadsheet's timezone.
 * If your spreadsheet timezone is not Eastern, adjust the
 * Utilities.formatDate calls OR normalize dates consistently.
 *
 * REQUIRED SHEETS:
 * - "TimeEntries" — Entry ID, Crew, Date, Entry Type,
 *   Clock In, Clock Out
 * - "Crew Members" — Name, Email, Role, Default Crew
 * - "BidSettings" — must store dayClockAlertHours
 *
 * ─────────────────────────────────────────────────────────────
 *
 * function checkOpenDayClocks() {
 *   var ss = SpreadsheetApp.getActiveSpreadsheet();
 *   var tz = ss.getSpreadsheetTimeZone(); // Use sheet's tz
 *
 *   // 1. Read threshold from settings
 *   var settingsSheet = ss.getSheetByName('BidSettings');
 *   var threshold = 10;
 *   if (settingsSheet) {
 *     var sData = settingsSheet.getDataRange().getValues();
 *     for (var i = 0; i < sData.length; i++) {
 *       if (sData[i][0] === 'dayClockAlertHours') {
 *         threshold = parseFloat(sData[i][1]) || 10;
 *         break;
 *       }
 *     }
 *   }
 *   if (threshold <= 0) return; // Disabled
 *
 *   // 2. Find open day_clock entries for today
 *   var teSheet = ss.getSheetByName('TimeEntries');
 *   if (!teSheet) return;
 *   var teData = teSheet.getDataRange().getValues();
 *   var headers = teData[0];
 *   var col = {};
 *   headers.forEach(function(h, i) { col[h] = i; });
 *
 *   var now = new Date();
 *   var today = Utilities.formatDate(now, tz, 'yyyy-MM-dd');
 *
 *   var openClocks = [];
 *   for (var r = 1; r < teData.length; r++) {
 *     var row = teData[r];
 *     if (row[col['Entry Type']] !== 'day_clock') continue;
 *     if (row[col['Clock Out']]) continue;
 *
 *     // Normalize date comparison using sheet timezone
 *     var rowDate = row[col['Date']];
 *     if (rowDate instanceof Date) {
 *       rowDate = Utilities.formatDate(rowDate, tz,
 *         'yyyy-MM-dd');
 *     }
 *     if (String(rowDate) !== today) continue;
 *
 *     var clockIn = parseClockTime_(
 *       row[col['Clock In']], row[col['Date']], tz);
 *     if (!clockIn) continue;
 *
 *     var elapsed = (now - clockIn) / 3600000;
 *     if (elapsed >= threshold) {
 *       openClocks.push({
 *         entryId: row[col['Entry ID']],
 *         crew: row[col['Crew']],
 *         clockIn: row[col['Clock In']],
 *         hours: Math.round(elapsed * 10) / 10
 *       });
 *     }
 *   }
 *
 *   if (openClocks.length === 0) return;
 *
 *   // 3. Look up crew leader emails
 *   var cmSheet = ss.getSheetByName('Crew Members');
 *   if (!cmSheet) return;
 *   var cmData = cmSheet.getDataRange().getValues();
 *   var cmH = cmData[0];
 *   var cmC = {};
 *   cmH.forEach(function(h, i) { cmC[h] = i; });
 *
 *   var leaderEmails = {};
 *   for (var c = 1; c < cmData.length; c++) {
 *     var m = cmData[c];
 *     if (m[cmC['Role']] === 'Leader' && m[cmC['Email']]) {
 *       leaderEmails[m[cmC['Default Crew']]] = m[cmC['Email']];
 *     }
 *   }
 *
 *   // 4. Dedup via PropertiesService
 *   var props = PropertiesService.getScriptProperties();
 *   var log = JSON.parse(
 *     props.getProperty('dayClockAlerts') || '{}');
 *
 *   // 5. Send emails
 *   openClocks.forEach(function(oc) {
 *     if (log[oc.entryId]) return;
 *     var email = leaderEmails[oc.crew];
 *     if (!email) return;
 *
 *     MailApp.sendEmail({
 *       to: email,
 *       subject: 'Endurance — Day clock still running ('
 *         + oc.crew + ')',
 *       htmlBody:
 *         '<p>Hi,</p>' +
 *         '<p>The day clock for <strong>' + oc.crew +
 *         '</strong> has been running for <strong>' +
 *         oc.hours + ' hours</strong> (started at ' +
 *         oc.clockIn + ').</p>' +
 *         '<p>If the day is over, please open the Crew ' +
 *         'app and tap "End Day" to clock everyone out.' +
 *         '</p>' +
 *         '<p style="color:#888;font-size:12px;">' +
 *         '— Endurance Services</p>'
 *     });
 *
 *     log[oc.entryId] = now.getTime(); // Unix ms timestamp
 *   });
 *
 *   // 6. Clean up old log entries (>48h)
 *   var cutoff = now.getTime() - 172800000;
 *   Object.keys(log).forEach(function(k) {
 *     if (log[k] < cutoff) delete log[k];
 *   });
 *   props.setProperty('dayClockAlerts',
 *     JSON.stringify(log));
 * }
 *
 * // Helper: parse "8:00 AM" + date → Date object
 * // Uses spreadsheet timezone for consistency
 * function parseClockTime_(timeStr, dateVal, tz) {
 *   if (!timeStr) return null;
 *   var m = timeStr.match(/(\d+):(\d+)\s*(AM|PM)/i);
 *   if (!m) return null;
 *   var h = parseInt(m[1]), min = parseInt(m[2]);
 *   var ap = m[3].toUpperCase();
 *   if (ap === 'PM' && h !== 12) h += 12;
 *   if (ap === 'AM' && h === 12) h = 0;
 *   // Build date in the sheet's timezone
 *   var d;
 *   if (dateVal instanceof Date) {
 *     d = new Date(dateVal);
 *   } else {
 *     // "YYYY-MM-DD" string
 *     var parts = String(dateVal).split('-');
 *     d = new Date(parts[0], parts[1] - 1, parts[2]);
 *   }
 *   d.setHours(h, min, 0, 0);
 *   return d;
 * }
 */
```

---

## Insertion Points Summary

**Note:** Line numbers are from the version analyzed and may drift as the file changes. **Always search for the referenced content** (e.g., search for `<!-- CONFIGURATION -->` or `'financials': 'Financials'`) rather than trusting line numbers blindly.

| What | Where | Reference |
|------|-------|-----------|
| Nav item HTML | After line 86 (closing Financials nav), before line 87 (`<!-- CONFIGURATION -->`) | Sidebar |
| View HTML (`view-timeReview`) | After line 1578 (closing `view-financials`), before line 1580 (`<!-- CONTACTS VIEW -->`) | Main body |
| Add entry modal HTML | Near other modals, e.g., after terms modal ~line 348 | Modal overlays |
| Day Clock Alert settings card | After line 1207 (MARVIN KB card), before line 1208 (Save button div) | Settings view |
| Title in `showView()` | Line 11932 titles map — add `'timeReview': 'Time Review'` | showView() |
| View trigger in `showView()` | After line 11997 — add `if (viewId === 'timeReview') { initTimeReview(); }` | showView() |
| `dayClockAlertHours` default | Line 2829 `bidSettings` — add `dayClockAlertHours: 10` | State |
| Settings input wiring | Line 18849 `settingsMap` — add `'setting-dayclock-alert-hours': 'dayClockAlertHours'` | Events |
| Settings form render | Line 12381 `renderSettingsForm()` — add alert hours line | Render |
| Settings save payload | Line 18886 save handler — add `dayClockAlertHours` | Save |
| JavaScript section | Before line 20789 (`// PRODUCTION RATES VIEW`) | Script |
| CSS | In `css/estimate.css` or inline `<style>` in `view-timeReview` | Styles |

---

## CSS Classes (all prefixed `tr-`)

```css
/* Table */
.tr-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.tr-table th { text-align: left; padding: 8px 12px; background: var(--gw-bg-secondary, #f8f9fa); font-weight: 500; color: var(--gw-text-secondary, #5f6368); border-bottom: 2px solid #e0e0e0; position: sticky; top: 0; z-index: 1; }
.tr-table td { padding: 6px 12px; border-bottom: 1px solid #eee; vertical-align: middle; }
.tr-table tr:hover { background: #f5f7ff; }

/* Type badges */
.tr-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }
.tr-badge-direct { background: #e6f4ea; color: #1e7e34; }
.tr-badge-travel { background: #fff3e0; color: #e65100; }
.tr-badge-shop { background: #e3f2fd; color: #1565c0; }
.tr-badge-fixed { background: #f3e5f5; color: #7b1fa2; font-size: 10px; padding: 1px 5px; margin-left: 4px; }

/* Split entry indicator */
.tr-split-icon { color: #9e9e9e; font-size: 11px; margin-left: 4px; cursor: help; }

/* Day rows */
.tr-day-header td { background: #f0f2f5; font-weight: 600; font-size: 13px; color: #333; }
.tr-day-subtotal td { background: #fafafa; font-weight: 500; font-style: italic; color: #555; }

/* Summary cards — fixed 5 columns since card count is known */
.tr-summary-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px; }
.tr-summary-card { background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; text-align: center; }
.tr-summary-card .tr-card-value { font-size: 24px; font-weight: 700; color: var(--gw-text-primary, #202124); }
.tr-summary-card .tr-card-label { font-size: 12px; color: var(--gw-text-secondary, #5f6368); margin-top: 4px; }

/* Inline editing */
.tr-edit-input { width: 85px; padding: 3px 6px; font-size: 12px; border: 1px solid #1A73E8; border-radius: 4px; }
.tr-fixed-note { font-size: 10px; color: #7b1fa2; font-style: italic; margin-top: 2px; }

/* Payroll badge */
.tr-payroll-badge { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }
.tr-payroll-pending { background: #fff3e0; color: #e65100; }
.tr-payroll-ready { background: #e6f4ea; color: #1e7e34; }

/* Open day clock warning */
.tr-open-clock-banner { display: flex; align-items: flex-start; gap: 12px; padding: 12px 16px; background: #fff8e1; border: 1px solid #ffe082; border-radius: 8px; margin-bottom: 16px; font-size: 13px; }
.tr-open-clock-banner strong { display: block; margin-bottom: 4px; }
.tr-close-clock-btn { background: none; border: 1px solid #e65100; color: #e65100; border-radius: 4px; padding: 2px 8px; font-size: 11px; cursor: pointer; margin-left: 8px; }
.tr-close-clock-btn:hover { background: #fff3e0; }

/* Action buttons */
.tr-action-btn { background: none; border: none; cursor: pointer; padding: 4px; color: var(--gw-text-secondary, #5f6368); border-radius: 4px; }
.tr-action-btn:hover { background: #f0f0f0; color: #202124; }
.tr-action-btn.delete:hover { color: #d93025; background: #fce8e6; }
```

---

## Implementation Notes

1. **Don't break existing functionality.** Only add code at specified insertion points. Never modify existing functions except the specific lines listed.

2. **Match code style.** `let`/`const`, template literals, arrow functions + `function` declarations, `async`/`await` for fetch, `showToast()` for feedback.

3. **`getTimeEntries` endpoint probably doesn't exist yet.** Document the API contract in a comment block and fail gracefully with a setup message.

4. **`saveTimeEntry`, `updateTimeEntry`, `deleteTimeEntry` all exist** in the backend — crew.html uses them. Use the same POST body shapes.

5. **`getCrewSchedule` won't work for roster fetching** — it requires a crew leader's phone number (from crew.html login), which estimate.html doesn't have. `getCrews` only returns crew names, not phones. A **new `getCrewMembers` endpoint is needed** (spec included in the comment block). This reads the Crew Members sheet and returns `{ crews: { "Crew A": [{ name, role }], ... } }` grouped by crew name. Use it for the Add Entry modal's member checkboxes and the member filter dropdown.

6. **Clock times** are "8:00 AM" format. Parse carefully for math.

7. **Crew Members** is a JSON string: always `JSON.parse(entry.crewMembers || '[]')`.

8. **Normalize member names** with `.trim()` everywhere — during display row expansion, payroll aggregation, and member filter population. Inconsistent spacing will break payroll grouping.

9. **Payroll week = Monday–Sunday.** Default to previous week on Mon/Tue. Friday = pay date.

10. **Overtime = weekly only** (Florida FLSA). OT after 40 hours/week. **Calculate OT across all crews** for a member, then attribute OT hours to the crew where the last hours were worked chronologically. Group by member+crew in the CSV so Department stays accurate.

11. **Travel time excluded from payroll export.** Indirect/travel entries often lack clear per-member attribution and are operational overhead captured by the day clock. The payroll CSV only includes direct (job + service) and shop time. Travel is included in the Detail Export for internal records. If a manager wants travel time on payroll, they add a manual entry.

12. **Handle empty data** with a meaningful empty state.

13. **Apps Script timezone**: The trigger function uses `ss.getSpreadsheetTimeZone()` for consistent date handling. The dedup log stores Unix timestamps (not formatted strings) for reliable comparison in Apps Script's V8 runtime.

14. **Crew Members sheet needs an Email column** for leaders. Noted in settings description and Apps Script comment.

15. **Shop identification**: Use `ticketId === 'SHOP' || (ticketId && ticketId.startsWith('SHOP'))` for defensive matching.

16. **Split entry detection**: When consecutive entries share the same ticketId+serviceName and have adjacent clock times (within 1 min), show a split indicator so managers understand these are crew-change continuations, not separate work.

17. **Fixed-duration entries**: Show a "Fixed" badge and contextual note during editing. Editing is still allowed (actual time can differ from budget).

18. **Manual entries are ticket-level only.** The Add Entry modal does not support service-level granularity — that's only captured by the crew app in real time.

19. **Validate clock-out > clock-in** everywhere: in `trSaveEntry()`, `trCloseDayClock()`, and `trSaveNewEntry()`.
