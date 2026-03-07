# Marvin File Upload & Smart Import — Implementation Prompt

## Overview

Add document upload capability to MARVIN (the AI assistant panel in `estimate.html`) so users can attach CSV, Excel (.xlsx/.xls), and PDF files directly in the chat. Marvin parses the file client-side, previews the data, helps map columns to the correct system fields, and imports on confirmation.

**Supported import targets:** Plant Catalog, Contacts, Item Catalog, Service Catalog, and Properties.

**Key insight:** SheetJS is already loaded on the page (line 12) and the existing plant CSV import flow (`parsePlantImportCSV`, `confirmPlantImport`) proves the pattern works. This feature generalizes it across all import targets and puts Marvin in control of the column mapping intelligence.

---

## Architecture Context

### Marvin's Current System
- **Panel**: A slide-out chat panel on the right side of estimate.html (lines 1968–2019)
- **Backend**: Two AWS Lambda endpoints:
  - `MARVIN_CHAT_URL` — synchronous JSON request/response (line 5551)
  - `MARVIN_STREAM_URL` — SSE streaming via Lambda Function URL (line 5552)
- **Context**: `buildMarvinContext()` (starts at line 5956) builds a rich JSON payload sent with every message. It has two parts: (1) active estimate data if one is open — property info, measurements, takeoffs, services, totals (lines 5962–6103), and (2) platform-wide data always included — all saved estimates/bids, contracts, properties, contacts, reminders, service catalog, bid settings, and knowledge base (lines 6105–6204). The full context object is sent with every Marvin request.
- **Actions**: Marvin returns structured `action` objects that render as clickable cards. Existing action types: `setField`, `createSection`, `navigate`, `updateKnowledgeBase`
- **Chat history**: `marvinChatHistory` array (line 5544) of `{role, content}` objects
- **Input area**: Textarea + send button (lines 2013–2018)

### Existing Libraries Already Loaded
- **SheetJS** (line 12): `XLSX` global — parses .xlsx, .xls, .csv files client-side
- **No PDF library loaded** — will need to add pdf.js from CDN for PDF text extraction

### Existing Import Functions (these already work in the backend)
- **Plant Catalog**: `savePlantEntry` POST — `{ savePlantEntry: true, plantId, commonName, botanicalName, category, sizes: [...], notes }`
- **Contacts**: `saveContact` POST — `{ saveContact: true, firstName, lastName, displayName, email, phone, company, billingAddress, propertyAddress, stage, source, notes }`
- **Item Catalog**: `addItem` POST — `{ addItem: true, item, type, unit, category, division, easy, medium, hard, purchaseUnit, costPerUnit, coveragePerUnit, defaultDepth }`
- **Service Catalog**: `saveServiceCatalog` POST — `{ saveServiceCatalog: true, serviceName, defaultVisits, billingTier, category, mapColor, description, durationType, ... }`
- **Properties**: `saveProperty` POST — `{ saveProperty: true, address, city, state, zip, propertyType, pin, gateCode, crew, crewPhone, lotSizeSF, lawnRawSF, lawnPerimeterLF, hardEdgeLF, softEdgeLF, mulchBedSF, mulchBedPerimeterLF, hedgeSF, hedgeLF, drivewayPavementSF, sidewalkSF, treeCount, irrigationZones, notes }`

### Current Marvin Input HTML (lines 2013–2018)
```html
<div class="marvin-panel-input">
  <textarea id="marvin-chat-input" placeholder="Ask MARVIN anything..." rows="1"
    onkeydown="handleMarvinKeydown(event)" oninput="autoGrowMarvinInput(this)"></textarea>
  <button class="marvin-send-btn" id="marvin-send-btn" onclick="sendMarvinMessage()">
    <span class="material-icons-outlined">send</span>
  </button>
</div>
```

---

## What to Build

### 1. File Attachment Button + Drag-and-Drop

Modify the Marvin panel HTML. Add a drop zone overlay inside the panel (inside `<aside class="marvin-panel">`, before the messages div), a file chip, and the attachment button:

**Drop zone overlay** (add inside the `marvin-panel` `<aside>`, before `marvin-panel-messages`):
```html
<div class="marvin-drop-overlay" id="marvin-drop-overlay">
  <div class="marvin-drop-content">
    <span class="material-icons-outlined" style="font-size:48px;">upload_file</span>
    <div>Drop file here</div>
    <div class="marvin-drop-hint">CSV, Excel, or PDF</div>
  </div>
</div>
```

**File chip + sheet picker** (add just before the `marvin-panel-input` div):
```html
<div class="marvin-file-chip" id="marvin-file-chip" style="display:none;">
  <span class="material-icons-outlined" style="font-size:14px;">description</span>
  <span id="marvin-file-chip-text"></span>
  <select id="marvin-sheet-picker" class="marvin-sheet-picker" style="display:none;" onchange="handleMarvinSheetChange(this.value)"></select>
  <button onclick="clearMarvinFile()" class="marvin-file-chip-remove">&times;</button>
</div>
```

**Modified input bar** (replace lines 2013–2018):
```html
<div class="marvin-panel-input">
  <button class="marvin-attach-btn" id="marvin-attach-btn" onclick="document.getElementById('marvin-file-input').click()" title="Attach file">
    <span class="material-icons-outlined">attach_file</span>
  </button>
  <input type="file" id="marvin-file-input" accept=".csv,.xlsx,.xls,.pdf" style="display:none;" onchange="handleMarvinFileSelect(this)">
  <textarea id="marvin-chat-input" placeholder="Ask MARVIN anything..." rows="1"
    onkeydown="handleMarvinKeydown(event)" oninput="autoGrowMarvinInput(this)"></textarea>
  <button class="marvin-send-btn" id="marvin-send-btn" onclick="sendMarvinMessage()">
    <span class="material-icons-outlined">send</span>
  </button>
</div>
```

### 2. PDF.js Library

Add to `<head>` after the SheetJS script tag (after line 12):
```html
<script src="https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.min.js"></script>
```

Set the worker source at the top of the `<script>` block (after the constants around line 2745):
```javascript
if (window.pdfjsLib) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js';
}
```

### 3. JavaScript — File Handling

Add to the MARVIN section (after the existing Marvin functions, before the Unified Takeoff Grid section at line 6821):

#### State
```javascript
let marvinAttachedFile = null;    // { name, type, rows, headers, rawData, summary, ... }
let marvinWorkbook = null;        // SheetJS workbook for multi-sheet files
let marvinLastImportIds = null;   // { target, ids: [...] } for undo
let marvinUndoTimer = null;       // 60-second undo window timer
const MARVIN_MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
```

#### Drag-and-Drop Setup

Call this once on init (e.g., in the DOMContentLoaded handler or after the Marvin panel HTML is in the DOM):

```javascript
function initMarvinDragDrop() {
  const panel = document.getElementById('marvin-panel');
  const overlay = document.getElementById('marvin-drop-overlay');
  if (!panel || !overlay) return;

  let dragCounter = 0; // track enter/leave to handle child elements

  panel.addEventListener('dragenter', (e) => {
    e.preventDefault();
    dragCounter++;
    overlay.classList.add('active');
  });

  panel.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dragCounter--;
    if (dragCounter <= 0) {
      dragCounter = 0;
      overlay.classList.remove('active');
    }
  });

  panel.addEventListener('dragover', (e) => {
    e.preventDefault(); // required to allow drop
  });

  panel.addEventListener('drop', (e) => {
    e.preventDefault();
    dragCounter = 0;
    overlay.classList.remove('active');

    const file = e.dataTransfer.files[0];
    if (!file) return;

    // Validate extension
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['csv', 'xlsx', 'xls', 'pdf'].includes(ext)) {
      showToast('Unsupported file type. Use CSV, Excel, or PDF.', 'error');
      return;
    }

    processMarvinFile(file);
  });
}
```

#### `handleMarvinFileSelect(input)`
When a file is selected via the paperclip button:
```javascript
function handleMarvinFileSelect(input) {
  const file = input.files[0];
  if (!file) return;
  processMarvinFile(file);
}
```

#### `processMarvinFile(file)`
Central file processing — called by both the file input and drag-drop:

```javascript
async function processMarvinFile(file) {
  // 1. File size guardrail
  if (file.size > MARVIN_MAX_FILE_SIZE) {
    showToast('File is too large (max 10MB). Trim it or split into smaller files.', 'error');
    return;
  }

  const ext = file.name.split('.').pop().toLowerCase();

  try {
    if (ext === 'pdf') {
      await processMarvinPDF(file);
    } else {
      await processMarvinSpreadsheet(file);
    }
  } catch (err) {
    console.error('File processing error:', err);
    showToast('Could not read this file: ' + err.message, 'error');
  }
}
```

#### `processMarvinSpreadsheet(file)`
Handles CSV, XLSX, XLS:

```javascript
async function processMarvinSpreadsheet(file) {
  const data = await file.arrayBuffer();
  const workbook = XLSX.read(data);
  marvinWorkbook = workbook; // keep for sheet switching

  // Multi-sheet handling
  const sheetNames = workbook.SheetNames;
  if (sheetNames.length > 1) {
    // Show sheet picker in the file chip
    const picker = document.getElementById('marvin-sheet-picker');
    picker.innerHTML = sheetNames.map((name, i) =>
      `<option value="${i}">${name}</option>`
    ).join('');
    picker.style.display = 'inline-block';
  } else {
    document.getElementById('marvin-sheet-picker').style.display = 'none';
  }

  // Parse the first sheet by default
  parseMarvinSheet(workbook, 0, file.name);
}

function parseMarvinSheet(workbook, sheetIndex, fileName) {
  const sheetName = workbook.SheetNames[sheetIndex];
  const sheet = workbook.Sheets[sheetName];
  const raw = XLSX.utils.sheet_to_json(sheet, { header: 1 });

  if (raw.length < 2) {
    showToast('Sheet "' + sheetName + '" needs a header row and at least one data row.', 'error');
    return;
  }

  const headers = raw[0].map(h => String(h || '').trim());
  const allDataRows = raw.slice(1);

  // Filter out empty/malformed rows (where most columns are empty)
  const threshold = Math.ceil(headers.length * 0.3); // at least 30% of columns must have data
  const cleanRows = [];
  const skippedRows = [];
  allDataRows.forEach((row, idx) => {
    const filledCols = row.filter(cell => cell !== undefined && cell !== null && String(cell).trim() !== '').length;
    if (filledCols >= threshold) {
      cleanRows.push(row);
    } else if (filledCols > 0) {
      skippedRows.push({ rowNum: idx + 2, row }); // +2 for 1-indexed + header
    }
    // Completely empty rows are silently dropped
  });

  const sheetLabel = workbook.SheetNames.length > 1 ? ` (sheet: ${sheetName})` : '';
  const skippedNote = skippedRows.length > 0 ? ` · ${skippedRows.length} rows skipped` : '';

  marvinAttachedFile = {
    name: fileName,
    type: 'spreadsheet',
    sheetName,
    headers,
    rowCount: cleanRows.length,
    sampleRows: cleanRows.slice(0, 5),
    allRows: cleanRows,
    skippedRows,
    summary: `${fileName}${sheetLabel} — ${cleanRows.length} rows, ${headers.length} columns${skippedNote}`
  };

  // Show file chip
  document.getElementById('marvin-file-chip').style.display = 'flex';
  document.getElementById('marvin-file-chip-text').textContent = marvinAttachedFile.summary;

  // Pre-fill prompt if input is empty
  const input = document.getElementById('marvin-chat-input');
  if (!input.value.trim()) {
    input.value = `I've attached ${fileName} with ${cleanRows.length} rows. What should I do with this data?`;
  }
}

function handleMarvinSheetChange(sheetIndex) {
  if (!marvinWorkbook) return;
  parseMarvinSheet(marvinWorkbook, parseInt(sheetIndex), marvinAttachedFile.name);
}
```

#### `processMarvinPDF(file)`
```javascript
async function processMarvinPDF(file) {
  if (!window.pdfjsLib) {
    showToast('PDF support requires pdf.js. CSV and Excel still work.', 'error');
    return;
  }

  const data = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data }).promise;
  const pageCount = pdf.numPages;
  let fullText = '';

  for (let i = 1; i <= pageCount; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    const pageText = content.items.map(item => item.str).join(' ');
    fullText += pageText + '\n';
  }

  // Check for scanned/empty PDFs
  if (fullText.trim().length < 50) {
    showToast('This PDF appears to be scanned. I can only read PDFs with embedded text. Try re-saving with OCR or using a spreadsheet instead.', 'error');
    return;
  }

  marvinAttachedFile = {
    name: file.name,
    type: 'pdf',
    pageCount,
    pdfText: fullText,
    summary: `${file.name} — ${pageCount} pages`
  };

  document.getElementById('marvin-file-chip').style.display = 'flex';
  document.getElementById('marvin-file-chip-text').textContent = marvinAttachedFile.summary;

  const input = document.getElementById('marvin-chat-input');
  if (!input.value.trim()) {
    input.value = `I've attached ${file.name} (${pageCount} pages). Can you pull any data from this for import?`;
  }
}
```

#### `clearMarvinFile()`
```javascript
function clearMarvinFile() {
  marvinAttachedFile = null;
  marvinWorkbook = null;
  document.getElementById('marvin-file-chip').style.display = 'none';
  document.getElementById('marvin-file-input').value = '';
  document.getElementById('marvin-sheet-picker').style.display = 'none';
}
```

#### Integration with `sendMarvinMessage()`
Modify the existing `sendMarvinMessage()` function (line 6251). In the section where `buildMarvinContext()` is called, add the file data to the context:

```javascript
const context = buildMarvinContext();

// Attach file data if present
if (marvinAttachedFile) {
  if (marvinAttachedFile.type === 'spreadsheet') {
    context.attachedFile = {
      name: marvinAttachedFile.name,
      type: 'spreadsheet',
      sheetName: marvinAttachedFile.sheetName,
      headers: marvinAttachedFile.headers,
      rowCount: marvinAttachedFile.rowCount,
      sampleRows: marvinAttachedFile.sampleRows.slice(0, 8),
      skippedRowCount: (marvinAttachedFile.skippedRows || []).length,
      // Don't send all rows to Lambda — just headers + sample for analysis
    };
  } else if (marvinAttachedFile.type === 'pdf') {
    context.attachedFile = {
      name: marvinAttachedFile.name,
      type: 'pdf',
      // Send enough text for Marvin to extract structured data
      // Truncate to ~8000 chars to stay within Lambda payload limits
      textContent: marvinAttachedFile.pdfText.slice(0, 8000),
      totalChars: marvinAttachedFile.pdfText.length,
      truncated: marvinAttachedFile.pdfText.length > 8000
    };
  }
}
```

Also append the user's message in the chat to show the file chip visually:
```javascript
// When rendering the user message bubble, if a file is attached, show it
// Note: appendMarvinMessage() returns null for role='user' (only returns refs for 'assistant')
if (marvinAttachedFile) {
  appendMarvinMessage('user', '📎 ' + marvinAttachedFile.name + '\n' + text);
} else {
  appendMarvinMessage('user', text);
}
```

After sending, clear the file attachment (but keep `marvinAttachedFile` in memory until import is complete or a new file is attached):
```javascript
// Hide the chip after sending, but keep the data for import
document.getElementById('marvin-file-chip').style.display = 'none';
document.getElementById('marvin-file-input').value = '';
```

### 4. New Action Type: `importData`

Marvin's Lambda backend will return an `importData` action when it identifies the data and suggests a mapping. The action payload:

```javascript
{
  type: 'importData',
  data: {
    target: 'plantCatalog',     // 'plantCatalog' | 'contacts' | 'itemCatalog' | 'serviceCatalog' | 'properties'
    targetLabel: 'Plant Catalog',
    mappings: {
      // sourceColumn → targetField
      'Common Name': 'commonName',
      'Size': 'size',
      'Unit Cost': 'unitCost',
      'Supplier': 'supplier'
    },
    unmappedColumns: ['Internal SKU', 'Notes'],  // columns Marvin couldn't map
    rowCount: 47,
    preview: [                   // first 3 mapped rows as preview
      { commonName: 'Knockout Rose', size: '3 gal', unitCost: 12.50, supplier: 'GreatScapes' },
      { commonName: 'Dwarf Ixora', size: '1 gal', unitCost: 6.75, supplier: 'GreatScapes' },
      { commonName: 'Muhly Grass', size: '3 gal', unitCost: 14.00, supplier: 'Sunscapes' }
    ]
  }
}
```

#### `renderMarvinActionCard()` Enhancement

Add a new case in the existing `renderMarvinActionCard()` function (line 6868) for `importData`:

```javascript
case 'importData':
  iconName = 'upload_file';
  iconClass = 'import-data';
  btnText = 'Import ' + action.data.rowCount + ' rows';
  btnClass = 'apply';
  break;
```

For the detail section, render a preview table with **editable column mappings** — each mapping row has a dropdown so the user can change where a source column maps to:

```javascript
} else if (action.type === 'importData' && action.data) {
  const d = action.data;
  let previewHtml = `<div class="marvin-import-meta">
    <strong>${d.rowCount} rows</strong> → ${d.targetLabel}
    ${d.skippedRowCount ? `<span class="marvin-import-skipped">(${d.skippedRowCount} empty rows skipped)</span>` : ''}
  </div>`;
  
  // Build list of available target fields for the dropdown
  const targetFieldsByType = {
    plantCatalog: ['commonName','botanicalName','category','size','unitCost','supplier','notes','(skip)'],
    contacts: ['firstName','lastName','name','displayName','email','phone','company','billingAddress','propertyAddress','stage','source','notes','(skip)'],
    itemCatalog: ['item','type','unit','category','division','easy','medium','hard','purchaseUnit','costPerUnit','coveragePerUnit','defaultDepth','(skip)'],
    serviceCatalog: ['serviceName','defaultVisits','billingTier','category','mapColor','description','durationType','(skip)'],
    properties: ['address','city','state','zip','propertyType','pin','gateCode','crew','crewPhone','lotSizeSF','lawnRawSF','hardEdgeLF','softEdgeLF','mulchBedSF','hedgeSF','drivewayPavementSF','treeCount','irrigationZones','notes','(skip)']
  };
  const availableFields = targetFieldsByType[d.target] || ['(skip)'];
  
  // Column mapping display with editable dropdowns
  previewHtml += `<div class="marvin-import-mappings" id="marvin-mappings-${actionId}">`;
  const allSrcCols = [...Object.keys(d.mappings), ...(d.unmappedColumns || [])];
  allSrcCols.forEach((src, colIndex) => {
    const currentDst = d.mappings[src] || '(skip)';
    const options = availableFields.map(f =>
      `<option value="${f}" ${f === currentDst ? 'selected' : ''}>${f}</option>`
    ).join('');
    previewHtml += `<div class="marvin-mapping-row">
      <span class="marvin-mapping-src">${escapeHtml(src)}</span>
      <span class="marvin-mapping-arrow">→</span>
      <select class="marvin-mapping-select" data-action-id="${actionId}" data-col-index="${colIndex}" onchange="updateMarvinMapping(this)">
        ${options}
      </select>
    </div>`;
  });
  previewHtml += '</div>';
  
  // Sample data preview (will be re-rendered on mapping changes)
  previewHtml += `<div class="marvin-import-preview-wrap" id="marvin-preview-${actionId}">`;
  previewHtml += renderMarvinImportPreview(d);
  previewHtml += '</div>';
  
  detail = previewHtml;
  detailIsHtml = true;
}
```

#### `renderMarvinImportPreview(data)`
Extracted helper so the preview can be re-rendered when mappings change:
```javascript
function renderMarvinImportPreview(d) {
  if (!d.preview || !d.preview.length) return '';
  const cols = Object.values(d.mappings);
  if (cols.length === 0) return '';
  let html = '<div class="marvin-import-preview-table">';
  html += '<div class="marvin-import-row header">' +
    cols.map(c => `<span>${escapeHtml(c)}</span>`).join('') + '</div>';
  d.preview.forEach(row => {
    html += '<div class="marvin-import-row">' +
      cols.map(c => `<span>${escapeHtml(String(row[c] || ''))}</span>`).join('') + '</div>';
  });
  html += '</div>';
  return html;
}
```

#### `updateMarvinMapping(selectEl)`

When the user changes a mapping dropdown — uses column index (not name) to avoid escapeHtml corruption:
```javascript
function updateMarvinMapping(selectEl) {
  const actionId = selectEl.getAttribute('data-action-id');
  const colIndex = parseInt(selectEl.getAttribute('data-col-index'));
  const newDst = selectEl.value;
  const action = _marvinPendingActions[actionId];
  if (!action || !action.data) return;

  // Reconstruct the source column name from the ordered list
  const allSrcCols = [...Object.keys(action.data.mappings), ...(action.data.unmappedColumns || [])];
  const srcCol = allSrcCols[colIndex];
  if (!srcCol) return;

  if (newDst === '(skip)') {
    delete action.data.mappings[srcCol];
    if (!action.data.unmappedColumns) action.data.unmappedColumns = [];
    if (!action.data.unmappedColumns.includes(srcCol)) action.data.unmappedColumns.push(srcCol);
  } else {
    action.data.mappings[srcCol] = newDst;
    if (action.data.unmappedColumns) {
      action.data.unmappedColumns = action.data.unmappedColumns.filter(c => c !== srcCol);
    }
  }

  // Re-render the preview table to reflect the new mappings
  const previewWrap = document.getElementById('marvin-preview-' + actionId);
  if (previewWrap) {
    previewWrap.innerHTML = renderMarvinImportPreview(action.data);
  }
}
```

Add to the `labelMap` const inside `renderMarvinActionCard()` (it's a local const in that function, not a standalone object):
```javascript
importData: 'Import Data'
```

#### `applyMarvinAction()` Enhancement

Add a new case in `applyMarvinAction()` (line 6678):
```javascript
case 'importData':
  applyMarvinImport(action.data);
  break;
```

#### Rendered Action Card — PDF CSV Download

The existing `renderMarvinActionCard()` function builds the action card HTML and returns it as a string. At the end of that template (after the main action button), add a conditional CSV download link for PDF-sourced imports. Modify the final return template in `renderMarvinActionCard()` so that when `action.type === 'importData' && action.data?.source === 'pdf'`, a secondary link appears below the import button:

```javascript
// After the main action button in the returned HTML:
${action.type === 'importData' && action.data?.source === 'pdf' ? `
  <button class="marvin-csv-download-btn" onclick="downloadExtractedCSV('${actionId}')">
    <span class="material-icons-outlined" style="font-size:14px;">download</span>
    Download as CSV to review first
  </button>
` : ''}
```

This only shows on PDF imports — spreadsheet imports don't need it since the user already has the original file.

#### `downloadExtractedCSV(actionId)`

Converts Marvin's extracted rows into a CSV and triggers a browser download:

```javascript
function downloadExtractedCSV(actionId) {
  const action = _marvinPendingActions[actionId];
  if (!action || !action.data || !action.data.extractedRows) {
    showToast('No extracted data available.', 'error');
    return;
  }

  const rows = action.data.extractedRows;
  if (rows.length === 0) return;

  // Use the target field names as CSV headers
  const headers = Object.keys(rows[0]);
  const csvLines = [headers.join(',')];

  rows.forEach(row => {
    const line = headers.map(h => {
      let val = String(row[h] || '');
      // Escape commas and quotes in values
      if (val.includes(',') || val.includes('"') || val.includes('\n')) {
        val = '"' + val.replace(/"/g, '""') + '"';
      }
      return val;
    }).join(',');
    csvLines.push(line);
  });

  const csvContent = csvLines.join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  // Name the file based on the original PDF name
  const baseName = (marvinAttachedFile ? marvinAttachedFile.name : 'extracted')
    .replace(/\.pdf$/i, '');
  a.download = baseName + '-extracted.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast('CSV downloaded. Review it, then import here or re-upload with edits.', 'info');
}
```

### 5. Import Execution Functions

#### `applyMarvinImport(data)`

This is the main import function. It uses `marvinAttachedFile.allRows` (the full data still in memory from when the file was parsed) and applies the column mappings to import into the target system.

```javascript
async function applyMarvinImport(data) {
  const { target, mappings, source } = data;

  // For PDFs, Marvin extracts the rows server-side and returns them in the action
  // For spreadsheets, rows come from the client-side parsed file
  let importRows;

  if (source === 'pdf' && data.extractedRows) {
    importRows = data.extractedRows;
  } else if (marvinAttachedFile && marvinAttachedFile.allRows) {
    const headers = marvinAttachedFile.headers;
    importRows = marvinAttachedFile.allRows.map(row => {
      const mapped = {};
      Object.entries(mappings).forEach(([srcCol, dstField]) => {
        if (dstField === '(skip)') return; // user chose to skip this column
        const colIdx = headers.indexOf(srcCol);
        if (colIdx >= 0 && row[colIdx] !== undefined) {
          mapped[dstField] = row[colIdx];
        }
      });
      return mapped;
    });
  } else {
    showToast('File data no longer available. Please re-attach the file.', 'error');
    return;
  }

  const total = importRows.length;
  let imported = 0;
  let updated = 0;
  let skipped = 0;
  let errors = 0;
  const createdIds = []; // for undo

  // Find the action button and convert it to a progress indicator
  const actionCards = document.querySelectorAll('.marvin-action-btn.apply');
  const btn = actionCards[actionCards.length - 1]; // most recent
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="material-icons-outlined">hourglass_top</span> Importing 0/${total}...`;
  }

  for (let i = 0; i < importRows.length; i++) {
    const mapped = importRows[i];
    try {
      const result = await importRowByTarget(target, mapped);
      if (result.action === 'created') {
        imported++;
        if (result.id) createdIds.push(result.id);
      } else if (result.action === 'updated') {
        updated++;
      } else if (result.action === 'skipped') {
        skipped++;
      }
    } catch (err) {
      console.error('Import row failed:', err, mapped);
      errors++;
    }

    // Update progress every 5 rows or on last row
    if (btn && (i % 5 === 0 || i === importRows.length - 1)) {
      const done = imported + updated + skipped + errors;
      btn.innerHTML = `<span class="material-icons-outlined">hourglass_top</span> Importing ${done}/${total}...`;
    }

    // Rate limiting: delay every 5 rows to avoid hitting Apps Script execution limits
    // Each row is a separate POST — for large imports (200+), this is slow but reliable.
    // A future optimization would be a batch endpoint (e.g., bulkSavePlantEntries) on the backend.
    if (i > 0 && i % 5 === 0) {
      await new Promise(r => setTimeout(r, 100));
    }
  }

  // Refresh the relevant data + build nav target
  let navViewId = null;
  let navLabel = null;
  switch (target) {
    case 'plantCatalog':
      if (typeof loadAndRenderPlantCatalog === 'function') await loadAndRenderPlantCatalog();
      navViewId = 'plant-catalog';
      navLabel = 'Plant Catalog';
      break;
    case 'contacts':
      if (typeof loadContacts === 'function') await loadContacts();
      if (currentView === 'contacts') renderContactsList();
      navViewId = 'contacts';
      navLabel = 'Contacts';
      break;
    case 'itemCatalog':
      if (typeof loadItemCatalog === 'function') await loadItemCatalog();
      if (typeof renderCatalog === 'function') renderCatalog();
      navViewId = 'catalog';
      navLabel = 'Item Catalog';
      break;
    case 'serviceCatalog':
      if (typeof loadServiceCatalog === 'function') await loadServiceCatalog();
      if (typeof renderServiceCatalog === 'function') renderServiceCatalog();
      navViewId = 'services';
      navLabel = 'Service Catalog';
      break;
    case 'properties':
      if (typeof loadPropertiesFromBackend === 'function') await loadPropertiesFromBackend();
      if (currentView === 'properties' && typeof renderPropertiesList === 'function') renderPropertiesList();
      navViewId = 'properties';
      navLabel = 'Properties';
      break;
  }

  // Update button to completed state with nav link
  if (btn) {
    btn.disabled = true;
    btn.className = 'marvin-action-btn applied';
    btn.innerHTML = `<span class="material-icons-outlined">check_circle</span> Done`;
    btn.onclick = null;
  }

  // Build summary message
  const parts = [];
  if (imported > 0) parts.push(`${imported} created`);
  if (updated > 0) parts.push(`${updated} updated`);
  if (skipped > 0) parts.push(`${skipped} skipped (duplicates)`);
  if (errors > 0) parts.push(`${errors} failed`);
  const summary = parts.join(', ');

  // Post a follow-up message from Marvin with results + navigation
  const refs = appendMarvinMessage('assistant', '', null);
  let resultHtml = `Import complete: ${summary}.`;
  if (navViewId) {
    resultHtml += ` <a href="#" onclick="showView('${navViewId}'); return false;" style="color:#1A73E8;text-decoration:underline;">View ${navLabel} →</a>`;
  }
  refs.bubble.innerHTML = formatMarvinText(resultHtml);
  refs.bubble.style.cssText = 'font-size:13px;';
  refs.messagesEl.scrollTop = refs.messagesEl.scrollHeight;
  marvinChatHistory.push({ role: 'assistant', content: `Import complete: ${summary}` });

  // Undo support (only for newly created items, not updates)
  // Item catalog undo is NOT supported — deleteItem requires rowIndex, which addItem doesn't return
  if (createdIds.length > 0 && target !== 'itemCatalog') {
    marvinLastImportIds = { target, ids: createdIds };
    showMarvinUndoImport(createdIds.length);
  }

  // Clear the file data
  marvinAttachedFile = null;
  marvinWorkbook = null;

  showToast(summary, errors > 0 ? 'error' : 'success');
}
```

#### `importRowByTarget(target, mapped)` — Routing with Duplicate Detection

```javascript
async function importRowByTarget(target, mapped) {
  switch (target) {
    case 'plantCatalog': return await importPlantRow(mapped);
    case 'contacts': return await importContactRow(mapped);
    case 'itemCatalog': return await importItemCatalogRow(mapped);
    case 'serviceCatalog': return await importServiceCatalogRow(mapped);
    case 'properties': return await importPropertyRow(mapped);
    default: throw new Error('Unknown target: ' + target);
  }
}
```

#### Per-Target Import Functions (with duplicate detection)

Each function returns `{ action: 'created' | 'updated' | 'skipped', id?: string }`.

```javascript
async function importPlantRow(mapped) {
  const name = (mapped.commonName || '').trim();
  if (!name) return { action: 'skipped' };

  const existing = (typeof plantCatalog !== 'undefined' ? plantCatalog : [])
    .find(p => (p.commonName || '').toLowerCase() === name.toLowerCase());

  let sizes = existing ? [...(existing.sizes || [])] : [];
  const size = (mapped.size || '').trim();
  const cost = parseFloat(mapped.unitCost || mapped.costPerUnit || 0);
  const supplier = (mapped.supplier || '').trim();

  if (size) {
    const idx = sizes.findIndex(s => s.size.toLowerCase() === size.toLowerCase());
    if (idx >= 0) {
      sizes[idx].supplierCost = cost;
      if (supplier) sizes[idx].supplier = supplier;
    } else {
      sizes.push({ size, supplierCost: cost, defaultMarkup: 0.20, supplier, sku: '' });
    }
  }

  const resp = await fetch(GOOGLE_SHEETS_URL, {
    method: 'POST',
    body: JSON.stringify({
      savePlantEntry: true,
      plantId: existing ? existing.plantId : null,
      commonName: name,
      botanicalName: mapped.botanicalName || (existing ? existing.botanicalName : '') || '',
      category: mapped.category || (existing ? existing.category : '') || 'Shrub',
      sizes,
      photoFileId: existing ? existing.photoFileId : '',
      notes: mapped.notes || ''
    })
  });
  const result = await resp.json();
  return {
    action: existing ? 'updated' : 'created',
    id: result.plantId || result.id || null
  };
}

async function importContactRow(mapped) {
  let firstName = (mapped.firstName || '').trim();
  let lastName = (mapped.lastName || '').trim();
  if (!firstName && !lastName && mapped.name) {
    const parts = mapped.name.trim().split(/\s+/);
    firstName = parts[0] || '';
    lastName = parts.slice(1).join(' ') || '';
  }
  if (!firstName && !lastName) return { action: 'skipped' };

  // Duplicate detection — match by name or email
  const email = (mapped.email || '').trim().toLowerCase();
  const fullName = (firstName + ' ' + lastName).trim().toLowerCase();
  const existing = (typeof contacts !== 'undefined' ? contacts : []).find(c => {
    if (email && (c.email || '').toLowerCase() === email) return true;
    const cName = ((c.firstName || '') + ' ' + (c.lastName || '') || c.name || '').trim().toLowerCase();
    return cName === fullName;
  });

  if (existing) {
    // Skip exact duplicates rather than creating double entries
    return { action: 'skipped' };
  }

  const resp = await fetch(GOOGLE_SHEETS_URL, {
    method: 'POST',
    body: JSON.stringify({
      saveContact: true,
      firstName, lastName,
      displayName: mapped.displayName || '',
      email: mapped.email || '',
      phone: mapped.phone || '',
      company: mapped.company || '',
      billingAddress: mapped.billingAddress || '',
      propertyAddress: mapped.propertyAddress || mapped.address || '',
      stage: mapped.stage || 'Lead',
      source: mapped.source || 'Import',
      notes: mapped.notes || ''
    })
  });
  const result = await resp.json();
  return { action: 'created', id: result.contactId || result.id || null };
}

async function importItemCatalogRow(mapped) {
  const itemName = (mapped.item || mapped.itemName || mapped.name || '').trim();
  if (!itemName) return { action: 'skipped' };

  // Duplicate detection — match by item name + division
  const division = mapped.division || 'MNT';
  const existing = (typeof itemCatalog !== 'undefined' ? itemCatalog : []).find(i =>
    (i.item || '').toLowerCase() === itemName.toLowerCase() &&
    (i.division || 'MNT') === division
  );

  if (existing) {
    return { action: 'skipped' };
  }

  const resp = await fetch(GOOGLE_SHEETS_URL, {
    method: 'POST',
    body: JSON.stringify({
      addItem: true,
      item: itemName,
      type: mapped.type || 'Labor',
      unit: mapped.unit || 'SF/Hour',
      category: mapped.category || 'General',
      division,
      easy: parseInt(mapped.easy || 0),
      medium: parseInt(mapped.medium || 0),
      hard: parseInt(mapped.hard || 0),
      purchaseUnit: mapped.purchaseUnit || '',
      costPerUnit: parseFloat(mapped.costPerUnit || 0),
      coveragePerUnit: parseInt(mapped.coveragePerUnit || 0),
      defaultDepth: parseFloat(mapped.defaultDepth || 0)
    })
  });
  const result = await resp.json();
  return { action: 'created', id: result.id || null };
}

async function importServiceCatalogRow(mapped) {
  const name = (mapped.serviceName || mapped.name || '').trim();
  if (!name) return { action: 'skipped' };

  // Duplicate detection
  const existing = (typeof serviceCatalog !== 'undefined' ? serviceCatalog : []).find(s =>
    (s.serviceName || s.name || '').toLowerCase() === name.toLowerCase()
  );

  if (existing) {
    return { action: 'skipped' };
  }

  await saveServiceCatalogItem({
    serviceName: name,
    defaultVisits: parseInt(mapped.defaultVisits || mapped.visits || 0),
    billingTier: mapped.billingTier || 'fixed',
    category: mapped.category || 'Maintenance',
    mapColor: mapped.mapColor || 'green',
    description: mapped.description || '',
    durationType: mapped.durationType || 'scalable'
  });
  return { action: 'created' };
}

async function importPropertyRow(mapped) {
  // Address is required — try multiple common column names
  const address = (mapped.address || mapped.streetAddress || mapped.street || mapped.propertyAddress || '').trim();
  if (!address) return { action: 'skipped' };

  // Duplicate detection — match by address (normalized)
  const normalizedAddr = address.toLowerCase().replace(/[.,#]/g, '').replace(/\s+/g, ' ');
  const existing = (typeof properties !== 'undefined' ? properties : []).find(p => {
    const pAddr = (p.propertyAddress || p.address || '').toLowerCase().replace(/[.,#]/g, '').replace(/\s+/g, ' ');
    return pAddr === normalizedAddr || pAddr.startsWith(normalizedAddr) || normalizedAddr.startsWith(pAddr);
  });

  if (existing) {
    return { action: 'skipped' };
  }

  // Parse city/state/zip from a full address if individual fields not provided
  let city = (mapped.city || '').trim();
  let state = (mapped.state || '').trim().toUpperCase();
  let zip = (mapped.zip || mapped.zipCode || mapped.postalCode || '').trim();

  // If no separate city/state/zip but the address contains them (e.g. "123 Oak St, Orlando, FL 32801")
  if (!city && !state && address.includes(',')) {
    const parts = address.split(',').map(p => p.trim());
    if (parts.length >= 2) {
      // Last part might be "FL 32801" or "32801"
      const lastPart = parts[parts.length - 1];
      const stateZipMatch = lastPart.match(/([A-Z]{2})\s*(\d{5})/i);
      if (stateZipMatch) {
        state = stateZipMatch[1].toUpperCase();
        zip = stateZipMatch[2];
      }
      if (parts.length >= 3) city = parts[1];
      else if (parts.length === 2 && !stateZipMatch) city = parts[1];
    }
  }

  const resp = await fetch(GOOGLE_SHEETS_URL, {
    method: 'POST',
    body: JSON.stringify({
      saveProperty: true,
      address: address.split(',')[0].trim(), // street only
      city,
      state,
      zip,
      propertyType: mapped.propertyType || mapped.type || 'Residential',
      pin: mapped.pin || mapped.accessCode || '',
      gateCode: mapped.gateCode || '',
      crew: mapped.crew || '',
      crewPhone: mapped.crewPhone || '',
      lotSizeSF: parseFloat(mapped.lotSizeSF || mapped.lotSize || 0),
      lawnRawSF: parseFloat(mapped.lawnRawSF || mapped.lawnSF || 0),
      hardEdgeLF: parseFloat(mapped.hardEdgeLF || 0),
      softEdgeLF: parseFloat(mapped.softEdgeLF || 0),
      mulchBedSF: parseFloat(mapped.mulchBedSF || mapped.mulchSF || 0),
      hedgeSF: parseFloat(mapped.hedgeSF || 0),
      drivewayPavementSF: parseFloat(mapped.drivewayPavementSF || mapped.drivewaySF || 0),
      treeCount: parseInt(mapped.treeCount || mapped.trees || 0),
      irrigationZones: parseInt(mapped.irrigationZones || mapped.zones || 0),
      notes: mapped.notes || ''
    })
  });
  const result = await resp.json();
  return { action: 'created', id: result.propertyId || result.id || null };
}
```

#### Undo Import

Show a timed undo button in the chat after a successful import. Undo only works for newly created items (not updates/skips).

```javascript
function showMarvinUndoImport(count) {
  // Clear any existing undo timer
  if (marvinUndoTimer) clearTimeout(marvinUndoTimer);

  const refs = appendMarvinMessage('assistant', '', null);
  refs.bubble.innerHTML = `<div class="marvin-undo-banner">
    <span>Undo import? (${count} new items)</span>
    <button class="marvin-undo-btn" onclick="executeMarvinUndo(this)">Undo</button>
    <span class="marvin-undo-countdown" id="marvin-undo-countdown">60s</span>
  </div>`;
  refs.messagesEl.scrollTop = refs.messagesEl.scrollHeight;

  // Countdown timer — undo expires after 60 seconds
  let remaining = 60;
  marvinUndoTimer = setInterval(() => {
    remaining--;
    const el = document.getElementById('marvin-undo-countdown');
    if (el) el.textContent = remaining + 's';
    if (remaining <= 0) {
      clearInterval(marvinUndoTimer);
      marvinUndoTimer = null;
      marvinLastImportIds = null;
      if (el) el.parentElement.innerHTML = '<span style="color:#80868b;font-size:12px;">Undo expired</span>';
    }
  }, 1000);
}

async function executeMarvinUndo(btn) {
  if (!marvinLastImportIds || !marvinLastImportIds.ids.length) {
    showToast('Nothing to undo.', 'error');
    return;
  }

  if (marvinUndoTimer) clearTimeout(marvinUndoTimer);
  marvinUndoTimer = null;

  const { target, ids } = marvinLastImportIds;
  btn.disabled = true;
  btn.textContent = 'Undoing...';

  let deleted = 0;
  for (const id of ids) {
    try {
      // Each target uses a different delete action name
      // VERIFIED against codebase:
      //   Plant: deletePlantEntry (line 10952) — uses plantId ✓
      //   Contact: deleteContact (line 8609) — uses contactId ✓
      //   Item Catalog: deleteItem (line 18272) — uses rowIndex, NOT itemId ✗
      //     → Undo is NOT supported for item catalog (we don't get rowIndex from addItem response)
      //   Service Catalog: deleteServiceCatalog (line 10673) — uses serviceId ✓
      //   Property: deleteProperty (line 9163) — uses propertyId ✓
      let payload;
      switch (target) {
        case 'plantCatalog':
          payload = { deletePlantEntry: true, plantId: id };
          break;
        case 'contacts':
          payload = { deleteContact: true, contactId: id };
          break;
        // itemCatalog: undo NOT supported — deleteItem requires rowIndex, not the ID returned by addItem
        case 'serviceCatalog':
          payload = { deleteServiceCatalog: true, serviceId: id };
          break;
        case 'properties':
          payload = { deleteProperty: true, propertyId: id };
          break;
      }
      if (payload) {
        await fetch(GOOGLE_SHEETS_URL, { method: 'POST', body: JSON.stringify(payload) });
        deleted++;
      }
    } catch (err) {
      console.error('Undo delete failed:', err);
    }
  }

  marvinLastImportIds = null;
  btn.parentElement.innerHTML = `<span style="color:#2e7d32;font-size:12px;">✓ ${deleted} items removed</span>`;

  // Refresh data
  switch (target) {
    case 'plantCatalog':
      if (typeof loadAndRenderPlantCatalog === 'function') await loadAndRenderPlantCatalog();
      break;
    case 'contacts':
      if (typeof loadContacts === 'function') await loadContacts();
      if (currentView === 'contacts') renderContactsList();
      break;
    case 'itemCatalog':
      if (typeof loadItemCatalog === 'function') await loadItemCatalog();
      if (typeof renderCatalog === 'function') renderCatalog();
      break;
    case 'serviceCatalog':
      if (typeof loadServiceCatalog === 'function') await loadServiceCatalog();
      if (typeof renderServiceCatalog === 'function') renderServiceCatalog();
      break;
    case 'properties':
      if (typeof loadPropertiesFromBackend === 'function') await loadPropertiesFromBackend();
      if (currentView === 'properties' && typeof renderPropertiesList === 'function') renderPropertiesList();
      break;
  }

  showToast(`Undo complete: ${deleted} items removed.`, 'success');
}
```

### 6. Lambda Backend Enhancement

Marvin's Lambda backend needs to know about the import targets and their field schemas so it can suggest accurate column mappings. Include this as documentation in a comment block:

```javascript
/*
 * ══════════════════════════════════════════════════════════════
 *  LAMBDA BACKEND: Marvin File Import Support
 * ══════════════════════════════════════════════════════════════
 *
 * When context.attachedFile is present in Marvin's request,
 * the Lambda system prompt should include instructions for
 * handling file data. Add this to the system prompt:
 *
 * ---
 * FILE IMPORT CAPABILITIES:
 * When the user attaches a file, you receive its headers and
 * sample rows in context.attachedFile. Your job is to:
 *
 * 1. Identify what kind of data it is
 * 2. Suggest the best import target
 * 3. Map source columns to target fields
 * 4. Return an importData action
 *
 * Available import targets and their fields:
 *
 * plantCatalog:
 *   commonName (required), botanicalName, category
 *   (Shrub|Tree|Annual|Perennial|Ornamental Grass|Ground Cover),
 *   size, unitCost, supplier, notes
 *
 * contacts:
 *   firstName, lastName, name (full — will be split),
 *   displayName, email, phone, company, billingAddress,
 *   propertyAddress, stage (Lead|Prospect|Customer),
 *   source, notes
 *
 * itemCatalog:
 *   item/itemName/name (required), type (Labor|Material),
 *   unit (SF/Hour, LF/Hour, etc.), category, division (MNT|ENH),
 *   easy, medium, hard (production rates),
 *   purchaseUnit, costPerUnit, coveragePerUnit, defaultDepth
 *
 * serviceCatalog:
 *   serviceName/name (required), defaultVisits,
 *   billingTier (fixed|billed|recommended), category,
 *   mapColor, description, durationType (scalable|fixed)
 *
 * properties:
 *   address/streetAddress/street (required), city, state, zip,
 *   propertyType (Residential|Commercial), pin, gateCode,
 *   crew, crewPhone, lotSizeSF, lawnRawSF, hardEdgeLF,
 *   softEdgeLF, mulchBedSF, hedgeSF, drivewayPavementSF,
 *   treeCount, irrigationZones, notes
 *   NOTE: If the source has a full address in one column
 *   (e.g. "123 Oak St, Orlando, FL 32801"), map it to
 *   "address" — the import function will parse city/state/zip
 *   from it automatically.
 *
 * When returning the importData action, use this format:
 * {
 *   type: "importData",
 *   data: {
 *     target: "plantCatalog",
 *     targetLabel: "Plant Catalog",
 *     mappings: { "Source Column": "targetField", ... },
 *     unmappedColumns: ["Col1", "Col2"],
 *     rowCount: 47,
 *     preview: [first 3 rows as mapped objects]
 *   }
 * }
 *
 * If the data doesn't clearly match any target, ask the user
 * which system they want to import into.
 *
 * PDF HANDLING:
 * When the file type is 'pdf', you receive extracted text in
 * context.attachedFile.textContent. Your job is the same as
 * with spreadsheets — identify structured data in the text
 * (tables, price lists, line items, contact lists, etc.),
 * extract it into rows, and return an importData action with
 * the same format. PDFs from nurseries, suppliers, and vendors
 * often contain plant lists, pricing tables, or material specs
 * that can be parsed into structured rows.
 *
 * For the importData action from a PDF, include an additional
 * field `extractedRows` in the action data — this is the
 * structured data you pulled from the text, since the client
 * doesn't have pre-parsed rows like it does for spreadsheets:
 *
 * {
 *   type: "importData",
 *   data: {
 *     target: "plantCatalog",
 *     targetLabel: "Plant Catalog",
 *     source: "pdf",
 *     mappings: { "Plant": "commonName", "Price": "unitCost" },
 *     rowCount: 23,
 *     extractedRows: [
 *       { commonName: "Knockout Rose", unitCost: 12.50, size: "3 gal" },
 *       { commonName: "Dwarf Ixora", unitCost: 6.75, size: "1 gal" },
 *       ...all rows
 *     ],
 *     preview: [first 3 rows]
 *   }
 * }
 *
 * If the PDF is scanned (no text) or the content is too
 * unstructured to extract data from, tell the user and suggest
 * they paste the data into a spreadsheet instead.
 *
 * If the PDF is long and got truncated (truncated: true), let
 * the user know you only saw part of it and ask if they want
 * to proceed with what you found so far.
 *
 * IMPORTANT: Column matching should be fuzzy. "Common Name",
 * "Plant Name", "Name", "plant" should all map to commonName.
 * "Cost", "Price", "Unit Cost", "Unit Price" should all map
 * to unitCost. Use your judgment.
 * ---
 */
```

### 7. `clearMarvinChat()` Enhancement

Modify the existing `clearMarvinChat()` function (line 5607) to also clear file state:
```javascript
// Add to clearMarvinChat():
marvinAttachedFile = null;
marvinWorkbook = null;
marvinLastImportIds = null;
if (marvinUndoTimer) { clearTimeout(marvinUndoTimer); marvinUndoTimer = null; }
document.getElementById('marvin-file-chip').style.display = 'none';
document.getElementById('marvin-file-input').value = '';
document.getElementById('marvin-sheet-picker').style.display = 'none';
```

### 8. Drag-Drop Initialization

Call `initMarvinDragDrop()` in the DOMContentLoaded handler (or at the end of the script where other init calls happen, around line 19115):
```javascript
initMarvinDragDrop();
```

---

## Insertion Points

**Note:** Always search for the referenced content rather than trusting line numbers.

| What | Where | Reference |
|------|-------|-----------|
| pdf.js `<script>` tag | After line 12 (SheetJS script), in `<head>` | Head scripts |
| Drop zone overlay HTML | Inside `marvin-panel` aside, before `marvin-panel-messages` | Marvin panel |
| File chip + sheet picker HTML | Before `marvin-panel-input` div | Marvin panel |
| Modified input bar HTML | Replace lines 2013–2018 (existing `marvin-panel-input`) | Marvin panel |
| State variables | Line 5548 area, with other Marvin state vars | Marvin state |
| `initMarvinDragDrop()` | After existing Marvin utility functions | Marvin JS |
| `processMarvinFile()`, `processMarvinSpreadsheet()`, `processMarvinPDF()`, `handleMarvinSheetChange()` | Before `buildMarvinContext()` (~line 5956) | Marvin JS |
| `clearMarvinFile()` | Adjacent to above | Marvin JS |
| Context injection in `sendMarvinMessage()` | Line 6271, after `buildMarvinContext()` is called | sendMarvinMessage |
| File indicator in user message | Line 6258, in the `appendMarvinMessage('user', text)` call | sendMarvinMessage |
| Clear file chip in `clearMarvinChat()` | Line 5607, inside existing function | clearMarvinChat |
| `importData` case in `renderMarvinActionCard()` | Line 6874, in the switch statement | Action rendering |
| `importData` detail rendering (with editable mappings) | After line 5929, in the detail-building section | Action rendering |
| `updateMarvinMapping()` | Adjacent to action card functions | Marvin JS |
| `importData` in `labelMap` | Line 5933 | Action rendering |
| `importData` case in `applyMarvinAction()` | Line 6685, in the switch statement | Action execution |
| `applyMarvinImport()` + per-target functions | After `applyMarvinKBUpdate()` (line 6818), before the Takeoff Grid section | Marvin JS |
| `downloadExtractedCSV()` | Adjacent to `applyMarvinImport()` | Marvin JS |
| `showMarvinUndoImport()` + `executeMarvinUndo()` | Adjacent to `applyMarvinImport()` | Marvin JS |
| `initMarvinDragDrop()` call | DOMContentLoaded handler (~line 19115) | Init |
| `pdfjsLib` worker setup | At the top of the `<script>` block (~line 2745), after constants | Configuration |
| CSS | In `css/estimate.css` | Styles |
| Lambda system prompt documentation | As a comment block in the Marvin JS section | Documentation |

---

## CSS

```css
/* ─── Marvin File Attachment ─── */
.marvin-attach-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  color: var(--gw-text-secondary, #5f6368);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.marvin-attach-btn:hover {
  background: rgba(0,0,0,0.06);
  color: var(--gw-text-primary, #202124);
}

.marvin-file-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  margin: 0 12px 4px;
  background: #e8f0fe;
  border-radius: 8px;
  font-size: 12px;
  color: #1967d2;
}
.marvin-file-chip-remove {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  color: #5f6368;
  padding: 0 2px;
  line-height: 1;
}
.marvin-file-chip-remove:hover {
  color: #d93025;
}

/* Sheet picker dropdown (multi-sheet Excel) */
.marvin-sheet-picker {
  font-size: 11px;
  padding: 1px 4px;
  border: 1px solid #a8c7fa;
  border-radius: 4px;
  background: white;
  color: #1967d2;
  cursor: pointer;
  max-width: 120px;
}

/* ─── Drag-and-Drop Overlay ─── */
/* NOTE: .marvin-panel must have position: relative for this to work.
   Verify in estimate.css — if not set, add: .marvin-panel { position: relative; } */
.marvin-drop-overlay {
  display: none;
  position: absolute;
  inset: 0;
  background: rgba(26, 115, 232, 0.08);
  border: 2px dashed #1A73E8;
  border-radius: 12px;
  z-index: 100;
  align-items: center;
  justify-content: center;
}
.marvin-drop-overlay.active {
  display: flex;
}
.marvin-drop-content {
  text-align: center;
  color: #1A73E8;
  font-size: 14px;
  font-weight: 500;
}
.marvin-drop-hint {
  font-size: 12px;
  color: #5f6368;
  font-weight: 400;
  margin-top: 4px;
}

/* ─── Import Action Card Styles ─── */
.marvin-import-meta {
  font-size: 12px;
  margin-bottom: 8px;
  color: var(--gw-text-secondary, #5f6368);
}
.marvin-import-skipped {
  color: #e65100;
  font-size: 11px;
  margin-left: 6px;
}

.marvin-import-mappings {
  font-size: 11px;
  margin-bottom: 10px;
}
.marvin-mapping-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
}
.marvin-mapping-src {
  color: var(--gw-text-secondary, #5f6368);
  background: #f1f3f4;
  padding: 1px 6px;
  border-radius: 4px;
  font-family: 'Roboto Mono', monospace;
  font-size: 10px;
}
.marvin-mapping-arrow {
  color: #80868b;
  font-size: 10px;
}
/* Editable mapping dropdown */
.marvin-mapping-select {
  font-size: 11px;
  padding: 1px 4px;
  border: 1px solid #dadce0;
  border-radius: 4px;
  background: white;
  color: #1e7e34;
  font-weight: 500;
  cursor: pointer;
}
.marvin-mapping-select:hover {
  border-color: #1A73E8;
}
.marvin-mapping-dst {
  color: #1e7e34;
  font-weight: 500;
}
.marvin-mapping-unmapped {
  color: #80868b;
  font-style: italic;
  font-size: 10px;
  margin-top: 4px;
}

.marvin-import-preview-table {
  font-size: 10px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}
.marvin-import-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(60px, 1fr));
  padding: 4px 6px;
  border-bottom: 1px solid #eee;
}
.marvin-import-row.header {
  background: #f8f9fa;
  font-weight: 600;
  color: var(--gw-text-secondary, #5f6368);
}
.marvin-import-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 2px;
}

/* Import action icon */
.marvin-action-icon.import-data {
  background: #e8f5e9;
  color: #2e7d32;
}

/* PDF CSV download link */
.marvin-csv-download-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px 0 2px;
  font-size: 11px;
  color: var(--gw-text-secondary, #5f6368);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.marvin-csv-download-btn:hover {
  color: var(--gw-text-primary, #202124);
}

/* ─── Undo Import Banner ─── */
.marvin-undo-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #fff8e1;
  border: 1px solid #ffe082;
  border-radius: 8px;
  font-size: 12px;
}
.marvin-undo-btn {
  background: none;
  border: 1px solid #e65100;
  color: #e65100;
  border-radius: 4px;
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
}
.marvin-undo-btn:hover {
  background: #fff3e0;
}
.marvin-undo-countdown {
  color: #80868b;
  font-size: 11px;
  min-width: 28px;
  text-align: right;
}
```

---

## User Experience Flow

**Spreadsheets (CSV / Excel):**
1. **User clicks paperclip or drags a file onto the Marvin panel** → a dashed blue overlay appears on drag-over with "Drop file here". File is accepted and parsed client-side. If over 10MB, rejected with a toast.
2. **File chip appears** showing "plants.xlsx — 47 rows, 6 columns · 3 rows skipped". If the Excel file has multiple sheets, a dropdown appears in the chip to switch between them.
3. **User types** (or uses the auto-suggested prompt) and **sends** → Marvin receives the message + headers and sample rows in context
4. **Marvin analyzes the data** → responds with something like: "This looks like a plant order from GreatScapes Nursery. I see 47 plants with common names, sizes, and costs. 3 empty rows were skipped. I can import these into your Plant Catalog."
5. **Marvin returns an `importData` action card** → shows editable column mappings (each with a dropdown to change the target field or skip), skipped columns, and a 3-row preview
6. **User adjusts mappings if needed** (e.g., changes "$/unit" from "(skip)" to "unitCost"), then clicks **"Import 47 rows"**
7. **Button becomes a progress counter**: "Importing 12/47..." → "Importing 34/47..." → "✓ Done"
8. **Marvin posts a follow-up message**: "Import complete: 23 created, 12 updated, 2 skipped (duplicates). [View Plant Catalog →]"
9. **Undo banner appears below**: "Undo import? (23 new items) [Undo] 60s" — expires after 60 seconds

**PDFs:**
1. **User clicks paperclip** → selects a PDF (e.g., a nursery price sheet)
2. **pdf.js extracts text client-side** → file chip appears showing "greatscapes-spring-2026.pdf — 12 pages"
3. **User sends** → Marvin receives up to 8,000 characters of extracted text in context
4. **Marvin reads the text, identifies structured data** (price tables, plant lists, contact lists, etc.) and **extracts it into rows server-side**
5. **Marvin returns an `importData` action** with `source: "pdf"` and `extractedRows` — the actual structured data it parsed from the text, plus the same mapping/preview format as spreadsheets
6. **User has two options on the action card:**
   - **"Import 23 rows"** button (primary) → imports directly into the system
   - **"Download as CSV to review first"** link (secondary, below the button) → downloads a CSV of Marvin's extracted data so the user can spot-check prices, names, etc. If they find errors, they can edit the CSV and re-upload it as a spreadsheet for a clean import
7. **Same toast/refresh as spreadsheets**

If Marvin can't extract structured data from a PDF (scanned image, too unstructured, or text is truncated), it tells the user and suggests alternatives like pasting the data into a spreadsheet.

If Marvin can't determine the import target for either file type, it asks: "I see columns for Name, Email, Phone, and Address. Should I import these as Contacts, or is this something else?"

---

## Implementation Notes

1. **SheetJS is already loaded.** Use the global `XLSX` object. No new dependency needed for spreadsheets.

2. **pdf.js is the only new dependency.** Load from CDN. If it fails to load, file upload still works for CSV/Excel — just show a toast "PDF support requires pdf.js" and skip.

3. **Don't send all spreadsheet rows to Lambda.** Only send headers + first 8 sample rows in `context.attachedFile`. The full data stays in `marvinAttachedFile.allRows` on the client for the actual import. For PDFs, send up to 8,000 characters of extracted text — enough for Marvin to find and extract structured data.

4. **Two import paths.** For spreadsheets, column mapping happens on Lambda but row mapping happens client-side (the full data never leaves the browser). For PDFs, Marvin extracts the structured rows server-side and returns them in `extractedRows` — the client imports them directly. The `applyMarvinImport()` function handles both paths.

5. **Column matching is Marvin's job.** The Lambda backend does the fuzzy matching (e.g., "Plant Name" → `commonName`). For PDFs, Marvin also does the data extraction (parsing tables from raw text into structured rows). The frontend just executes whatever Marvin returns. The user can adjust mappings via the editable dropdowns.

6. **Existing import functions are the reference.** The `importPlantRow()` function mirrors the existing `confirmPlantImport()` logic at line 11044 — including matching against existing plants and updating sizes. Follow the same patterns.

7. **Error handling per row.** If one row fails to import, continue with the rest. Report the totals at the end: created, updated, skipped (duplicates), and failed.

8. **File data lifecycle.** `marvinAttachedFile` persists in memory until: (a) the import completes, (b) a new file is attached, or (c) `clearMarvinChat()` is called. This allows the user to have a back-and-forth with Marvin about the data before importing.

9. **The `marvin-panel-input` HTML modification replaces lines 2013–2018.** The existing textarea and send button are preserved — the attachment button, drop zone, and file chip are additions.

10. **Scanned PDFs won't work.** pdf.js can only extract embedded text, not OCR. If the extracted text is empty or very short relative to the page count, show a message: "This PDF appears to be scanned. I can only read PDFs with embedded text. Try re-saving with OCR or using a spreadsheet instead."

11. **Long PDFs get truncated.** The prompt sends up to 8,000 characters. If the PDF is longer, `truncated: true` is set in the context so Marvin can tell the user it only saw a portion and ask if they want to proceed with what it found.

12. **Rate limiting.** Each row is a separate POST to Apps Script, which has per-user concurrent execution limits. The function adds a 100ms delay every 5 rows. For 200+ row imports this is slow (~4 seconds per 100 rows). A future optimization would be a batch endpoint (e.g., `bulkSavePlantEntries`) that accepts an array — but this would require backend changes. The current sequential approach is reliable if slow.

13. **No Apps Script backend changes needed.** All save endpoints already exist. The only backend work is updating the Lambda system prompt to include the import target schemas and PDF extraction instructions (documented in the comment block).

14. **CSV download is PDF-only.** The "Download as CSV to review first" link only appears on `importData` actions where `source === 'pdf'`. The CSV is generated client-side from Marvin's `extractedRows`. Filename: `{original-pdf-name}-extracted.csv`.

15. **Drag and drop.** The Marvin panel is a drop zone. When a file is dragged over it, a dashed blue overlay appears with "Drop file here — CSV, Excel, or PDF". The `initMarvinDragDrop()` function is called once on init. It uses a `dragCounter` to handle child element enter/leave events correctly.

16. **Multi-sheet Excel files.** If an .xlsx file has multiple sheets, a dropdown picker appears in the file chip. The user can switch sheets and the data re-parses. The default is the first sheet. `marvinWorkbook` is stored so sheet switching doesn't re-read the file.

17. **Empty/malformed row filtering.** Before building `marvinAttachedFile`, rows where fewer than 30% of columns have data are filtered out. Completely empty rows are silently dropped. Partially empty rows (likely subtotals or section headers) are tracked in `skippedRows` and the count is shown in the file chip and sent to Lambda so Marvin can mention it.

18. **File size guardrail.** Files over 10MB are rejected with a toast before any parsing. This prevents SheetJS from freezing the browser tab on massive files.

19. **Duplicate detection.** Contacts are checked by email and full name. Item catalog entries are checked by item name + division. Service catalog entries are checked by service name. Properties are checked by normalized street address (case-insensitive, punctuation stripped). Plants use the existing match-by-name logic (updates existing, creates new). Duplicates are reported as "skipped" in the import summary.

20. **Column mapping is editable.** Each source column in the action card has a dropdown of available target fields. The user can change mappings before clicking import. Choosing "(skip)" removes the mapping. Columns are identified by numeric index (not by name string) to avoid `escapeHtml()` corrupting column names containing `&`, `<`, etc. When a mapping changes, the preview table re-renders immediately via `renderMarvinImportPreview()` to reflect the new column assignments.

21. **Post-import navigation.** After import completes, Marvin posts a follow-up message with the summary and a clickable "View Plant Catalog →" (or Contacts, etc.) link that calls `showView()`. This gets the user to the data they just imported in one click.

22. **Undo import — verified action names.** The undo feature uses these backend actions (verified against the codebase): `deletePlantEntry` (NOT `deletePlant` — line 10952), `deleteContact` (line 8609), `deleteServiceCatalog` (line 10673), `deleteProperty` (line 9163). **Undo is NOT supported for Item Catalog** — `deleteItem` (line 18272) requires a `rowIndex`, but the `addItem` response returns an ID, not a row index. The undo banner is suppressed for item catalog imports. The 60-second countdown applies to all other targets.

23. **Progress feedback.** The import button itself updates during the process: "Import 47 rows" → "Importing 12/47..." → "✓ Done". No separate progress bar needed — the button IS the progress indicator.

24. **Property address parsing.** `importPropertyRow()` handles full addresses in a single column (e.g., "123 Oak St, Orlando, FL 32801") by splitting on commas and extracting city, state, and zip. It also normalizes addresses for duplicate detection (strips punctuation, lowercases). The street portion (before the first comma) is sent as `address`, with `city`, `state`, `zip` parsed separately — matching the `getPropertyDataFromModal()` pattern at line 9073.

25. **CSS: position: relative on marvin-panel.** The drag-and-drop overlay uses `position: absolute; inset: 0`, which requires `.marvin-panel` to have `position: relative`. Check `estimate.css` — if it's not already set, add it.

26. **Content-Type headers.** The import fetch calls omit `Content-Type: application/json`. The rest of the codebase also omits this header on POST calls to Apps Script (which doesn't require it), so this is intentionally consistent. If you want to add it for correctness, include `headers: { 'Content-Type': 'application/json' }` in all fetch POST calls.
