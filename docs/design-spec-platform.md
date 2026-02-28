# Endurance Management Platform — Design Specification

> **Aesthetic:** Google Workspace + Microsoft Excel, with the typographic discipline of Massimo Vignelli
> **Principle:** Dense, functional, professional. Every pixel earns its place. Structure creates clarity.
> **Anti-principle:** This is NOT a marketing dashboard, NOT a SaaS landing page, NOT a trendy dev tool.

---

## Design Philosophy

Claude Code defaults to "modern SaaS" aesthetics: large padding, airy cards, oversized fonts, decorative elements. That's wrong for this app. This is a business operations tool — the people using it stare at it for hours. It should feel like Google Sheets, Gmail, and Excel had a baby. Dense. Functional. Zero decoration.

The design language borrows from Massimo Vignelli's principles:
- **The grid is the underwear of the layout.** Every element aligns to a strict spatial grid. Nothing floats arbitrarily. Columns, rows, and gutters create the skeleton — you shouldn't see them, but you should feel the order.
- **Discipline over decoration.** Hierarchy comes from type scale and weight contrast, not from color, icons, or ornament. If you need a decorative element to make something clear, the layout is wrong.
- **Reduce, then reduce again.** If a label can be removed because the data is self-evident, remove it. If two borders can become one, merge them. If an icon duplicates what the text already says, delete the icon.
- **Color is information, not decoration.** Red means overdue, over budget, or destructive. Green means complete or positive. Blue means interactive or selected. Black and white are the foundation. Color is used like punctuation — sparingly, and only when it carries meaning.
- **One typeface, used with intention.** Hierarchy through scale and weight, not through switching typefaces. A 22px medium heading and a 13px regular table cell create all the contrast you need.

**When building any component for the management platform, reference this file first.**

---

## Color Palette (Exact Google Workspace Colors)

```css
:root {
  /* Backgrounds */
  --bg-page: #F8F9FA;            /* Google Workspace page background */
  --bg-surface: #FFFFFF;          /* Cards, modals, panels */
  --bg-sidebar: #F1F3F4;         /* Left sidebar background */
  --bg-sidebar-hover: #E8EAED;   /* Sidebar item hover */
  --bg-sidebar-active: #D2E3FC;  /* Sidebar item selected (blue tint) */
  --bg-header: #FFFFFF;          /* Top header bar */
  --bg-table-header: #F8F9FA;   /* Table column headers */
  --bg-table-row-hover: #F1F3F4; /* Table row hover */
  --bg-table-row-alt: #F8F9FA;  /* Alternating row (optional, subtle) */
  --bg-input: #FFFFFF;           /* Input fields */
  --bg-input-focus: #FFFFFF;     /* Input fields when focused */

  /* Borders */
  --border-default: #DADCE0;     /* Google Workspace standard border */
  --border-light: #E8EAED;       /* Lighter dividers */
  --border-input: #DADCE0;       /* Input field borders */
  --border-input-focus: #1A73E8; /* Input focus ring — Google blue */
  --border-table: #E0E0E0;       /* Table grid lines (closer to Excel) */

  /* Text */
  --text-primary: #202124;       /* Main text — near-black, not pure black */
  --text-secondary: #5F6368;     /* Secondary labels, descriptions */
  --text-tertiary: #80868B;      /* Disabled, placeholder text */
  --text-link: #1A73E8;          /* Links — Google blue */
  --text-on-primary: #FFFFFF;    /* White text on blue buttons */

  /* Brand / Action Colors */
  --blue-primary: #1A73E8;       /* Primary actions, links, selected states */
  --blue-hover: #1765CC;         /* Button hover */
  --blue-light: #D2E3FC;         /* Selected sidebar item, light badges */
  --blue-lighter: #E8F0FE;       /* Subtle blue backgrounds */
  --green: #188038;              /* Success, completed, positive values */
  --green-light: #E6F4EA;        /* Success backgrounds */
  --red: #D93025;                /* Error, destructive, negative values */
  --red-light: #FCE8E6;          /* Error backgrounds */
  --yellow: #F9AB00;             /* Warning, pending */
  --yellow-light: #FEF7E0;      /* Warning backgrounds */
  --orange: #E8710A;             /* Attention, overdue */

  /* Shadows — Google's exact two-layer shadow system */
  --shadow-1: 0 1px 2px 0 rgba(60, 64, 67, 0.3), 0 1px 3px 1px rgba(60, 64, 67, 0.15);
  --shadow-2: 0 1px 2px 0 rgba(60, 64, 67, 0.3), 0 2px 6px 2px rgba(60, 64, 67, 0.15);
  --shadow-3: 0 1px 3px 0 rgba(60, 64, 67, 0.3), 0 4px 8px 3px rgba(60, 64, 67, 0.15);

  /* Elevation usage:
     shadow-1: cards, dropdowns
     shadow-2: modals, popovers
     shadow-3: dialogs, floating panels
     Most elements use NO shadow — just borders */
}
```

### Color Rules
- **The foundation is black on white.** `--text-primary` (#202124) on `--bg-surface` (#FFFFFF). This is 90% of the interface.
- **Color is only used when it carries meaning.** A green badge means "complete." A red number means "over budget." A blue link means "interactive." If color is not communicating status, state, or interactivity, it shouldn't be there.
- **Red is the power accent** (Vignelli's signature). Overdue invoices, negative margins, destructive actions, and "attention needed" states use `--red` (#D93025). Use it sparingly — when red appears, the eye goes there immediately. That's the point.
- **Sidebar items do NOT have shadows.** They use background color changes on hover/active.
- **Table rows do NOT have shadows.** They use bottom borders and hover background.
- **Cards use borders, not shadows**, unless they are floating/overlaid (modals, dropdowns).
- **Status badges** use the light background variant + darker text: green-light bg with green text, red-light bg with red text, etc.
- **Never use gradients.** Flat colors only.
- **Never use color for decoration.** No colored section backgrounds, no tinted cards, no colored sidebar. The sidebar is gray (#F1F3F4) because it's recessed, not because gray is decorative.

---

## Structural Elements (The Vignelli Layer)

These are the elements that give the interface its sense of order. Most AI-generated UI is missing all of them.

### The Grid
Every view follows a strict column grid. Content doesn't float — it snaps to columns.
- **Sidebar + content area** is the primary split: 256px fixed sidebar, fluid content area.
- **Content area** uses a 12-column grid at 16px gutters for form layouts, summary cards, and mixed content. Tables span full width (all 12 columns).
- **Form fields** sit on the grid: single fields span 4 or 6 columns, never full width unless they're a textarea. Two fields side-by-side in a row is the default, not one field per row.
- **Summary stat cards** align to the same grid: 3 across = 4 columns each, 4 across = 3 columns each.

### Heavy Horizontal Rules
Vignelli used thick horizontal lines as structural dividers — not decorative, but architectural. They tell your eye "this is a new section."
```css
/* Section divider — the heavy rule */
--rule-heavy: 2px solid #202124;    /* Black, 2px — used between major sections */
--rule-standard: 1px solid #DADCE0; /* Google standard — used between rows, fields */
```
- **Heavy rule (2px, near-black)** appears: below the page title, between major content sections (e.g., between the summary stats row and the data table below it), and at the bottom of modal headers.
- **Standard rule (1px, --border-default)** appears: between table rows, between form fields in a group, between sidebar sections.
- The heavy rule is used **2-3 times per view maximum**. It's a structural punctuation mark, not a separator you sprinkle everywhere.
- This is the single most Vignelli element in the design. It gives the interface a printed, editorial quality that no amount of shadows or gradients can achieve.

### Alignment Discipline
- **Left-align everything** except numbers (right-aligned) and centered content in status columns.
- **Labels align with their content.** If a form label is above an input, they share the same left edge. No indenting inputs relative to their labels.
- **Consistent left edge.** In a view, the page title, the summary cards below it, and the table below that all share the same left margin. Nothing jogs left or right between sections.
- **Column headers align with cell content.** If dollar amounts are right-aligned in cells, the "Amount" header is also right-aligned.

---

## Typography

Vignelli built entire identity systems with a single typeface. We use Roboto as our workhorse — it's already native to Google Workspace and reads cleanly at small sizes. Google Sans appears only in the top-level page title to mark "you've changed views." Everything else is Roboto at different sizes and weights. The hierarchy comes from the contrast between large and small, medium and regular — not from switching typefaces.

```css
:root {
  /* One family, used with discipline */
  --font-display: 'Google Sans', 'Segoe UI', Roboto, sans-serif; /* Page titles ONLY */
  --font-body: Roboto, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; /* Everything else */
  --font-mono: 'Roboto Mono', 'Consolas', 'Courier New', monospace;

  /* Type scale — note how SMALL these are compared to typical SaaS */
  --text-xxl: 500 22px/28px var(--font-display);   /* Page titles only (Bids, Contracts, Schedule) */
  --text-xl: 500 18px/24px var(--font-body);       /* Section headings — Roboto, not Google Sans */
  --text-lg: 500 16px/24px var(--font-body);       /* Card titles, modal titles */
  --text-md: 400 14px/20px var(--font-body);       /* DEFAULT body text */
  --text-sm: 400 13px/18px var(--font-body);       /* Table cells, secondary info */
  --text-xs: 400 12px/16px var(--font-body);       /* Captions, timestamps */
  --text-xxs: 500 11px/14px var(--font-body);      /* Badges, tiny labels */

  /* Structural labels — Vignelli's signature: small, uppercase, letterspaced */
  --text-overline: 500 11px/16px var(--font-body);
  --overline-tracking: 0.08em;  /* letter-spacing for overline labels */
  --overline-transform: uppercase;

  /* CRITICAL: The default body text is 14px, NOT 16px.
     Table cells are 13px.
     This is what makes Google Workspace feel dense.
     Claude Code will try to use 16px as body — override this every time. */
}
```

### Typography Rules
- **Google Sans appears exactly once per view**: the page title at the top ("Bids", "Contracts", "Schedule"). Nowhere else. This is the Vignelli approach — one moment of typographic emphasis, everything else is the workhorse.
- **Roboto** for all body text, table content, form labels, input values, sidebar items, button labels, modal content, and section headings.
- **14px is the default.** Not 16px. This single difference accounts for half of the "too airy" feeling.
- **Table cell text is 13px.** This is non-negotiable for spreadsheet density.
- **Font weight 500 (medium)** for headings. Not 600 or 700. Google Workspace headings are subtly heavier, not bold.
- **Font weight 400 (regular)** for all body text. Bold should be rare — used for emphasis, not decoration.
- **Line height is tight.** 20px for 14px body text. Not 24px or 28px.
- **Never use font sizes larger than 22px** anywhere in the management platform. There are no hero sections.
- **Numbers in tables use `font-variant-numeric: tabular-nums`** so columns align perfectly.
- **Overline labels** (11px, uppercase, letter-spaced 0.08em) are used for category headings, section dividers in sidebars, and above stat groups. This is a Vignelli structural element — it organizes without decorating. Example: `OVERVIEW` above a summary stats row, `BILLING` above the invoicing section of a sidebar. Overlines use `--text-tertiary` color — they're quiet structural markers, not shouts.

---

## Spacing & Density

This is where most AI-generated UI fails. These values are based on actual Google Workspace measurements.

```css
:root {
  /* Page layout */
  --sidebar-width: 256px;           /* Gmail sidebar width */
  --header-height: 48px;            /* Google Workspace compact header, NOT 56-64px */
  --content-padding: 16px;          /* Page content area padding — NOT 24px or 32px */

  /* Card / panel padding */
  --card-padding: 12px 16px;        /* Inside cards — tight */
  --card-padding-compact: 8px 12px; /* Compact variant for dense areas */
  --section-gap: 16px;              /* Gap between cards/sections */

  /* Table spacing (the most important values in this file) */
  --table-row-height: 32px;         /* Excel-like row height */
  --table-row-height-compact: 28px; /* For very dense tables like bid line items */
  --table-cell-padding: 4px 8px;    /* Cell padding — this is TIGHT, like Excel */
  --table-header-padding: 4px 8px;  /* Same as cells — headers aren't special */
  --table-header-height: 32px;      /* Same height as rows */

  /* Form spacing */
  --input-height: 32px;             /* Google Workspace input height */
  --input-padding: 0 8px;           /* Inside inputs */
  --label-margin-bottom: 4px;       /* Gap between label and input — NOT 8px */
  --field-gap: 12px;                /* Gap between form fields */

  /* Button spacing */
  --button-height: 32px;            /* Standard button height */
  --button-height-sm: 28px;         /* Small/compact buttons */
  --button-padding: 0 16px;         /* Horizontal button padding */
  --button-padding-sm: 0 12px;      /* Small button padding */
  --button-gap: 8px;                /* Gap between adjacent buttons */

  /* Sidebar */
  --sidebar-item-height: 32px;      /* Gmail sidebar row height */
  --sidebar-item-padding: 0 12px 0 24px; /* Left indent + right padding */
  --sidebar-section-gap: 8px;       /* Between sidebar sections */
  --sidebar-icon-size: 20px;        /* Sidebar icons — small */
  --sidebar-icon-gap: 12px;         /* Gap between icon and label */

  /* Structural elements — Vignelli */
  --rule-heavy: 2px solid #202124;  /* Major section dividers — near-black, deliberate */
  --rule-standard: 1px solid #DADCE0; /* Table rows, form groups, sidebar separators */
  --rule-heavy-margin: 16px 0;      /* Vertical breathing room around heavy rules */
}
```

### Spacing Rules
- **The #1 rule: when Claude Code generates something and it looks too airy, the padding is wrong.** Halve it. If it used `padding: 24px`, change to `padding: 12px 16px`. If it used `gap: 24px`, change to `gap: 12px`.
- **Table rows are 32px tall.** This is the single most important measurement. Google Sheets default is 21px. Excel default is 20px. 32px gives slightly more breathing room while staying dense. Claude Code will try to use 48-56px — reject this immediately.
- **Table cell padding is `4px 8px`.** Not `8px 16px`. Not `12px`. This is what makes a table feel like a spreadsheet rather than a card list.
- **Input fields are 32px tall.** Not 40px. Not 44px.
- **Buttons are 32px tall.** Google Workspace buttons are compact.
- **The sidebar is 256px wide.** Not 280px, not 300px.
- **Content padding is 16px.** Not 24px, not 32px.
- **Labels sit 4px above their inputs.** Not 8px. Not 12px.

---

## Component Patterns

### Sidebar (Gmail-style + Vignelli Section Labels)
```
┌─────────────────────────────┐
│ [Logo] Endurance         ≡  │  ← 48px header, logo + hamburger
├─────────────────────────────┤
│                             │
│  OPERATIONS                 │  ← 11px overline, uppercase, --text-tertiary, letter-spacing 0.08em
│  📊  Dashboard              │  ← 32px rows, 20px icons, 14px text
│  📋  Bids                   │
│  📄  Contracts              │
│  👥  Contacts               │  ← --text-secondary when inactive
│  🏠  Properties             │  ← --bg-sidebar-active (blue) when selected
│  📅  Schedule               │  ← --text-primary when active
│                             │
│  FINANCIALS                 │  ← another overline section
│  💰  Invoices               │
│  📈  Revenue                │
│                             │
│  CONFIGURATION              │  ← third overline section
│  ⚙️  Settings               │
│  📦  Item Catalog           │
│  📋  Service Catalog        │
│  📐  Production Rates       │
└─────────────────────────────┘
```
- Background: `--bg-sidebar` (#F1F3F4)
- No shadows on items. Background color change on hover (--bg-sidebar-hover) and active (--bg-sidebar-active).
- Active item has `border-radius: 0 16px 16px 0` (Google's pill shape, only right side rounded)
- Icons are 20px, muted (--text-secondary), become --blue-primary when active
- Text is 14px Roboto, --text-secondary, becomes --text-primary when active
- **Section overlines** (OPERATIONS, FINANCIALS, CONFIGURATION): 11px uppercase, letter-spacing 0.08em, --text-tertiary, padding-left matches item text indent. 16px margin-top above each section except the first.
- Overlines are quiet — they organize the sidebar without competing with the items. If they feel too prominent, they're too dark or too large.

### Header Bar
```
┌────────────────────────────────────────────────────────────────────┐
│  Bids                                    [+ New Bid]  [🔍] [⚙️]  │
┝━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┥
```
- Height: 48px
- Background: --bg-header (#FFFFFF)
- **Bottom border: 2px solid #202124 (heavy rule)** — this is the Vignelli signature. The page title sits above a strong black line that anchors the entire view. Not a subtle gray 1px line — a deliberate 2px near-black rule.
- Title: --text-xxl (22px Google Sans medium) — the ONE place Google Sans appears
- Action buttons right-aligned, 32px height
- NO shadow on the header bar. The heavy rule does the work.

### Data Tables (The Most Important Component)
```
┌──────────┬──────────┬────────┬──────────┬────────┬─────────┐
│ Property │ Status   │ Crew   │ Monthly  │ Start  │ Actions │  ← 32px, --bg-table-header, 13px, --text-secondary, font-weight 500
├──────────┼──────────┼────────┼──────────┼────────┼─────────┤
│ 123 Main │ ● Active │ Crew 1 │ $1,200   │ 04/01  │ ⋮       │  ← 32px, 13px, --text-primary
│ 456 Oak  │ ● Draft  │ Crew 2 │ $2,450   │ 05/01  │ ⋮       │  ← alternate: --bg-table-row-alt (optional)
│ 789 Elm  │ ● Signed │ Crew 1 │ $980     │ 04/15  │ ⋮       │  ← hover: --bg-table-row-hover
└──────────┴──────────┴────────┴──────────┴────────┴─────────┘
```
- Row height: 32px (--table-row-height). This is LAW.
- Cell padding: `4px 8px` (--table-cell-padding)
- Header: same height as rows, --bg-table-header, 13px font, font-weight 500, --text-secondary
- Body: 13px font, --text-primary
- Grid lines: 1px solid --border-table on bottom of each row. Vertical lines optional (Excel has them, Google Sheets has them, pick one and be consistent).
- Hover: --bg-table-row-hover on the full row
- Dollar amounts: right-aligned, `font-variant-numeric: tabular-nums`
- Status dots: 8px circles with color (green=active, yellow=draft, blue=signed)
- Actions column: "⋮" three-dot menu, 32px hit target, opens dropdown
- **NO rounded corners on the table.** Tables are rectangular.
- **NO card wrapping the table.** The table IS the content. It can have a 1px border around it, but no card padding around a table.

### Bid Builder Table (Spreadsheet-Style)
This is the densest component. It should feel like editing a spreadsheet.
```
┌──────┬─────────────────────┬─────┬───────┬──────┬───────┬──────┬───────┬────────┬───────┬──────┐
│      │ Item                │ OCC │ QTY   │ Unit │ P/H   │ AH   │ TH    │ P/P    │ TP    │ GM%  │
├──────┼─────────────────────┼─────┼───────┼──────┼───────┼──────┼───────┼────────┼───────┼──────┤
│  1   │ 48" Mower Ride      │  42 │ 8,500 │ SF   │ 4,250 │ 0.00 │ 84.00 │ $38.50 │$1,617 │ 52%  │
│  2   │ 21" Mower Walk      │  42 │ 2,100 │ SF   │ 1,050 │ 0.00 │ 84.00 │ $38.50 │$3,234 │ 52%  │
│  3   │ String Trimmer      │  42 │   650 │ LF   │   325 │ 0.25 │ 94.50 │ $43.31 │$1,819 │ 52%  │
└──────┴─────────────────────┴─────┴───────┴──────┴───────┴──────┴───────┴────────┴───────┴──────┘
```
- Row height: 28px (--table-row-height-compact) — even tighter than normal tables
- Cell padding: `2px 6px` — absolute minimum
- Font: 13px Roboto, tabular-nums for all number columns
- Editable cells: light blue background (#E8F0FE) or subtle blue border to indicate editability, like Excel
- Number alignment: right-aligned in every number column
- Header row: sticky (position: sticky, top: 0), --bg-table-header, same font size as body
- The table should be horizontally scrollable if needed — never wrap or truncate column headers
- Cell editing: click to edit, blue outline like Google Sheets cell selection (`2px solid --blue-primary`)

### Cards (When Appropriate — Rarely)
Cards are for summary stats and detail panels. NOT for list items.
```
  OVERVIEW                          ← 11px overline, uppercase, --text-tertiary, 0.08em tracking
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│ Outstanding          │ │ Collected            │ │ Overdue             │
│ $14,250              │ │ $48,900              │ │ $3,200              │  ← --red for negative
│ 12 invoices          │ │ this month           │ │ 4 invoices          │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ← 2px heavy rule
┌──────────────────────────────────────────────────────────────────────┐
│  Table starts here...                                                │
```
- Padding: 12px 16px (--card-padding)
- Border: 1px solid --border-default
- Border-radius: 8px (the ONLY place that gets rounded corners)
- Background: --bg-surface (#FFFFFF)
- Shadow: --shadow-1 only if the card is floating. Otherwise, border only.
- **Overline label** ("OVERVIEW", "BILLING SUMMARY") sits above the card row — not inside any card. 11px, uppercase, --text-tertiary, letter-spacing 0.08em. 8px margin below.
- **Summary stat cards** appear in a row of 3-5 at the top of a view. They are small and compact.
- **The heavy rule appears below the summary cards** and above the main data table. This visually separates "summary" from "detail" — the architectural division of the page.
- **Dollar values that are negative or represent problems (overdue, over budget) use --red.** Color is information.
- **Do NOT wrap tables in cards.** Do NOT wrap lists in cards. Cards are for isolated blocks of summary info.

### Buttons
```
[+ New Bid]     ← Primary: --blue-primary bg, white text, 32px height, 8px padding, 4px radius
[Cancel]        ← Secondary: white bg, --border-default border, --text-primary text
[Delete]        ← Destructive: white bg, --red text, --red border on hover
[⋮]             ← Icon-only: 32x32px, transparent bg, --text-secondary, hover: --bg-sidebar-hover
```
- Height: 32px standard, 28px small
- Border-radius: 4px (Google Workspace uses subtle rounding on buttons, NOT 8px or pill-shaped)
- Font: 14px Roboto medium (500)
- Primary buttons are rare — one per view. Most buttons are secondary.
- **No shadows on buttons.** Ever.
- **No gradient backgrounds.** Flat color.

### Form Fields
```
Property Address                ← 12px --text-secondary label
┌─────────────────────────────┐
│ 123 Main Street             │ ← 32px tall, 14px text, 8px horizontal padding
└─────────────────────────────┘
                               ← 4px gap between label and input

Assigned Crew                   ← 12px --text-secondary label
┌──────────────────────────┬──┐
│ MNT Crew 1               │▾│ ← dropdown, same 32px height
└──────────────────────────┴──┘
```
- Input height: 32px
- Border: 1px solid --border-input
- Border-radius: 4px
- Focus: 2px solid --blue-primary (replaces border, like Google)
- Label: 12px --text-secondary, 4px below
- Padding inside input: 0 8px
- **No floating labels.** Labels above inputs. Always.
- **No oversized inputs.** 32px. Not 40px. Not 44px.

### Status Badges
```
● Active      ← green dot (8px) + "Active" text
● Draft       ← yellow dot + text
● Finalized   ← blue dot + text
● Overdue     ← red dot + text

[Signed]      ← pill badge: --green-light bg, --green text, 11px font, 2px 8px padding
[Revision]    ← pill badge: --yellow-light bg, --yellow text
[Sent]        ← pill badge: --blue-lighter bg, --blue-primary text
```
- Dot style: 8px circle + 13px text label. Used in tables.
- Pill style: colored background + text, 4px radius, 11px font. Used in cards and headers.
- **No icons inside badges.** Just color + text.

### Modals / Dialogs
- Max-width: 560px for standard modals, 800px for complex ones (bid detail, contract preview)
- Padding: 24px (modals are the ONE place that gets more padding)
- Title: 18px Google Sans medium
- Backdrop: rgba(0, 0, 0, 0.4)
- Border-radius: 8px
- Shadow: --shadow-3
- Close button: top-right, "✕", 32x32px
- Action buttons: bottom-right, 8px gap between them

---

## Anti-Patterns (Things Claude Code Will Try To Do — Reject Immediately)

| Claude Code will try to... | Instead, do this... |
|----------------------------|---------------------|
| Use 16px as body font size | Use 14px body, 13px in tables |
| Add 24-32px padding inside cards | Use 12px 16px padding |
| Make buttons 40-44px tall | Use 32px buttons |
| Make input fields 40-44px tall | Use 32px inputs |
| Make table rows 48-56px tall | Use 32px rows (28px in bid tables) |
| Add shadows to everything | Use 1px borders. Shadows only on floating elements |
| Round corners to 12-16px | Use 4px on buttons/inputs, 8px on cards, 0px on tables |
| Wrap tables inside cards with padding | Table IS the content. No wrapper padding |
| Use a purple/indigo color palette | Use Google blue (#1A73E8) as the only accent, red (#D93025) for alerts |
| Add decorative icons next to labels | Icons in sidebar only. No decorative icons in content |
| Use `gap: 24px` between elements | Use `gap: 12px` or `gap: 8px` |
| Make the sidebar 280-320px wide | Sidebar is 256px |
| Add gradients on backgrounds or buttons | Flat colors only |
| Generate a hero section or banner | This is a tool, not a website |
| Use Inter, Poppins, or other trendy fonts | Use Roboto body + Google Sans for page title only |
| Add animated transitions on everything | No animations except dropdown open/close |
| Create "card grid" layouts for lists | Use tables for lists. Cards for summaries only |
| Use lots of bold text for emphasis | Bold is rare. Use color or secondary text instead |
| Add empty states with illustrations | Simple text: "No bids yet" — no illustrations |
| Use multiple accent colors | One blue, one red, one green. That's it. Color = meaning |
| Put section titles in large bold text | Use 11px uppercase overline labels for sections |
| Use a subtle 1px gray line under headers | Use a 2px near-black heavy rule — it's structural, not decorative |
| Use Google Sans / display font for everything | Google Sans appears ONCE per view (page title). Everything else is Roboto |
| Float elements outside the column grid | Everything aligns. Left edges match. Columns are sacred |
| Add colored backgrounds to sections | White content, gray sidebar. No colored section backgrounds |

---

## Quick Reference: Key Measurements

| Element | Height/Size | Padding | Font |
|---------|-------------|---------|------|
| Header bar | 48px | 0 16px | 22px Google Sans 500 |
| Header bottom rule | 2px | — | — |
| Sidebar item | 32px | 0 12px 0 24px | 14px Roboto 400 |
| Sidebar overline | 16px | 0 0 8px 24px | 11px Roboto 500 uppercase, 0.08em tracking |
| Table row | 32px | 4px 8px per cell | 13px Roboto 400 |
| Bid table row | 28px | 2px 6px per cell | 13px Roboto 400 |
| Table header | 32px | 4px 8px per cell | 13px Roboto 500 |
| Button (standard) | 32px | 0 16px | 14px Roboto 500 |
| Button (small) | 28px | 0 12px | 13px Roboto 500 |
| Input field | 32px | 0 8px | 14px Roboto 400 |
| Form label | — | 0 0 4px 0 (margin-bottom) | 12px Roboto 400 |
| Summary card | auto | 12px 16px | varies |
| Section overline | — | 0 0 8px 0 (margin-bottom) | 11px Roboto 500 uppercase, 0.08em tracking |
| Heavy rule | 2px | 16px 0 (margin top/bottom) | — |
| Modal | auto | 24px | varies |
| Badge (pill) | 20px | 2px 8px | 11px Roboto 500 |
| Status dot | 8px | — | — |
| Icon (sidebar) | 20px | — | — |
| Page content area | — | 16px | — |
| Section gap | — | 16px (as margin/gap) | — |

---

## How to Use This File with Claude Code

Add this to your `CLAUDE.md`:

```markdown
## Management Platform Design
See `docs/design-spec-platform.md` for exact measurements, colors, spacing, and structural rules.
This is the AUTHORITATIVE source for all visual decisions in the management platform.
When any measurement in generated code conflicts with this spec, the spec wins.
The platform should look like Google Workspace + Microsoft Excel with Massimo Vignelli's
typographic discipline — dense, functional, structurally organized, zero decoration.
Key Vignelli elements: 2px heavy rules between major sections, 11px uppercase overline labels
for section categories, one display font (Google Sans) used only for the page title,
strict grid alignment, and color used exclusively to convey meaning.
```

When asking Claude Code to build a component:
```
Build a contracts table view. Follow docs/design-spec-platform.md exactly —
32px rows, 13px font, 4px 8px cell padding, no card wrapper around the table.
Use a 2px heavy rule between the summary stats and the table.
Section overline "ACTIVE CONTRACTS" above the table in 11px uppercase.
```

When Claude Code generates something that looks wrong:
```
This doesn't match the spec. The rows are too tall (should be 32px),
the padding is too large (should be 4px 8px), and there's a shadow that
shouldn't be there. Fix per docs/design-spec-platform.md.
```
