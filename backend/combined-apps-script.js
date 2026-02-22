// ═══════════════════════════════════════════════════════════════
// COMBINED Apps Script — Estimate Builder + Text My Team
// Deploy as Web App: "Execute as: Me", "Who has access: Anyone"
// ═══════════════════════════════════════════════════════════════

// ─── CONFIGURATION ───────────────────────────────────────────
var ESTIMATE_DRIVE_FOLDER_ID = '1pwK1a7BAgcNc5vcwjuiyY8hk1fmqGe64';
var TEXT_MY_TEAM_DRIVE_FOLDER_ID = '13Jn7FtrGevihB4TngKyjSa_ytBiH4R9_';

// ═══════════════════════════════════════════════════════════════
//  ROUTING
// ═══════════════════════════════════════════════════════════════

function doGet(e) {
  var action = e.parameter.action;

  try {
    switch (action) {
      // ─── Estimate Builder ───
      case 'getItemCatalog':
        return jsonResponse(getItemCatalog());
      case 'getBidSettings':
        return jsonResponse(getBidSettings());
      case 'getBids':
        return jsonResponse(getBids());
      case 'getTemplates':
        return jsonResponse(getTemplates());
      case 'getTemplate':
        return jsonResponse(getTemplate(e.parameter.templateId));
      case 'getServiceCatalog':
        return jsonResponse(getServiceCatalog());
      case 'getContracts':
        return jsonResponse(getContracts());
      case 'getTickets':
        return jsonResponse(getTickets(e));

      // ─── Text My Team ───
      case 'getRequests':
        return jsonResponse(getRequests(e.parameter.phone));
      case 'getProperties':
        return jsonResponse(getProperties());
      case 'getSavedReports':
        return jsonResponse(getSavedReports(e.parameter.property));
      case 'getReportData':
        return jsonResponse(getReportData(e.parameter.fileId));
      case 'getPhotoBase64':
        return jsonResponse(getPhotoBase64(e.parameter.fileId));

      // ─── Crew Schedule ───
      case 'getCrewSchedule':
        return jsonResponse(getCrewSchedule(e.parameter.phone, e.parameter.date));
      case 'getCrewMembers':
        return jsonResponse(getCrewMembers(e.parameter.phone));
      case 'getCrews':
        return jsonResponse(getCrews());
      case 'getRouteOrder':
        return jsonResponse(getRouteOrder(e.parameter.crew, e.parameter.dayOfWeek));
      case 'getWeeklyReportData':
        return jsonResponse(getWeeklyReportData(e.parameter.weekOf));
      case 'verifyPin':
        return verifyPin(e.parameter.pin);

      // ─── Production Analysis ───
      case 'getProductionAnalysis':
        return jsonResponse(getProductionAnalysis(e));

      // ─── Contacts ───
      case 'getContacts':
        return jsonResponse(getContacts());

      default:
        return jsonResponse({ success: false, error: 'Unknown action: ' + action });
    }
  } catch (err) {
    return jsonResponse({ success: false, error: err.toString() });
  }
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);

    // ─── Estimate Builder POST handlers ───
    if (data.uploadEstimateJson) {
      return uploadEstimateJson(data);
    }
    if (data.createContract) {
      return jsonResponse(createContract(data));
    }
    if (data.saveTickets) {
      return jsonResponse(saveTickets(data));
    }
    if (data.updateContract) {
      return jsonResponse(updateContract(data));
    }
    if (data.deleteFutureTickets) {
      return jsonResponse(deleteFutureTickets(data));
    }
    if (data.updateTicketStatus) {
      return jsonResponse(updateTicketStatus(data));
    }
    if (data.rescheduleTicket) {
      return jsonResponse(rescheduleTicket(data));
    }
    if (data.bulkSkipDay) {
      return jsonResponse(bulkSkipDay(data));
    }
    if (data.saveBid) {
      return jsonResponse(saveBid(data.bidData));
    }
    if (data.updateBid) {
      return jsonResponse(updateBid(data.bidData));
    }
    if (data.saveBidSettings) {
      return jsonResponse(saveBidSettings(data));
    }
    if (data.saveTemplate) {
      return jsonResponse(saveTemplate(data));
    }
    if (data.deleteTemplate) {
      return jsonResponse(deleteTemplate(data.templateId));
    }
    if (data.deleteBid) {
      return jsonResponse(deleteBid(data.bidId));
    }

    // ─── Crew Schedule POST handlers ───
    if (data.saveTimeEntry) {
      return jsonResponse(saveTimeEntry(data));
    }
    if (data.updateTimeEntry) {
      return jsonResponse(updateTimeEntry(data));
    }
    if (data.deleteTimeEntry) {
      return jsonResponse(deleteTimeEntry(data));
    }
    if (data.completeJob) {
      return jsonResponse(completeJob(data));
    }
    if (data.saveRouteOrder) {
      return jsonResponse(saveRouteOrder(data));
    }
    if (data.sendWeeklyReport) {
      return jsonResponse(sendWeeklyReport(data));
    }
    if (data.reopenTicketService) {
      return jsonResponse(reopenTicketService(data));
    }

    // ─── Contacts POST handlers ───
    if (data.saveContact) return jsonResponse(saveContact(data));
    if (data.updateContact) return jsonResponse(updateContact(data));
    if (data.deleteContact) return jsonResponse(deleteContact(data));

    // ─── Text My Team POST handlers ───
    if (data.photoOnly) {
      return jsonResponse(uploadPhoto(data));
    }
    if (data.updateAcknowledged) {
      return jsonResponse(updateAcknowledged(data));
    }
    if (data.updateStatus) {
      return jsonResponse(updateStatus(data));
    }
    if (data.submitTicket) {
      return jsonResponse(submitRequest(data));
    }
    if (data.inspectionPhoto) {
      return jsonResponse(uploadInspectionPhoto(data));
    }
    if (data.siteReportPdf) {
      return jsonResponse(uploadSiteReportPdf(data));
    }
    if (data.siteReportPhoto) {
      return jsonResponse(uploadSiteReportPhoto(data));
    }
    if (data.siteReportJson) {
      return jsonResponse(saveSiteReportJson(data));
    }

    // Customer request submission (from index.html)
    if (data.customerName && data.propertyAddress) {
      if (data.photo && !data.photoUrl) {
        var photoResult = uploadPhoto({
          photo: data.photo,
          filename: data.propertyAddress.split(',')[0] + ' - Request',
          property: data.propertyAddress,
          internal: false
        });
        data.photoUrl = photoResult.photoUrl || '';
      }
      return jsonResponse(submitRequest(data));
    }

    return jsonResponse({ success: false, error: 'Unknown POST action' });
  } catch (err) {
    return jsonResponse({ success: false, error: err.toString() });
  }
}

function jsonResponse(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}


// ═══════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════
//  ESTIMATE BUILDER FUNCTIONS
// ═══════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════


// ═══════════════════════════════════════════════════════════════
// ESTIMATE JSON UPLOAD/DOWNLOAD (Google Drive)
// ═══════════════════════════════════════════════════════════════

function uploadEstimateJson(data) {
  try {
    var mainFolder = DriveApp.getFolderById(ESTIMATE_DRIVE_FOLDER_ID);
    var targetFolder = mainFolder;

    // Try to organize into property subfolder
    var propertyAddress = data.propertyAddress || '';
    if (propertyAddress && propertyAddress.trim() !== '') {
      var streetAddress = propertyAddress.split(',')[0].trim();
      if (streetAddress && streetAddress.length > 0) {
        // Get or create property folder
        var subFolders = mainFolder.getFoldersByName(streetAddress);
        var propertyFolder;
        if (subFolders.hasNext()) {
          propertyFolder = subFolders.next();
        } else {
          propertyFolder = mainFolder.createFolder(streetAddress);
        }

        // Get or create Estimates subfolder
        var estimateFolders = propertyFolder.getFoldersByName('Estimates');
        if (estimateFolders.hasNext()) {
          targetFolder = estimateFolders.next();
        } else {
          targetFolder = propertyFolder.createFolder('Estimates');
        }
      }
    }

    var filename = (data.bidId || ('EST-' + new Date().getTime())) + '.json';

    // If updating, try to delete the old file first
    if (data.oldFileId) {
      try {
        var oldFile = DriveApp.getFileById(data.oldFileId);
        oldFile.setTrashed(true);
      } catch (e) {
        Logger.log('Could not delete old estimate file: ' + e);
      }
    }

    var jsonBlob = Utilities.newBlob(data.estimateJson, 'application/json', filename);
    var jsonFile = targetFolder.createFile(jsonBlob);
    jsonFile.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      fileId: jsonFile.getId()
    }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    Logger.log('Estimate JSON upload error: ' + err);
    return ContentService.createTextOutput(JSON.stringify({ success: false, error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// ═══════════════════════════════════════════════════════════════
// ITEM CATALOG
// ═══════════════════════════════════════════════════════════════

function getItemCatalog() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Item Catalog');
  if (!sheet) return { success: false, error: 'Item Catalog sheet not found' };

  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var items = [];

  // Map sheet headers to frontend property names (lowercase)
  var headerMap = {
    'Item': 'item',
    'Unit': 'unit',
    'Easy': 'easy',
    'Medium': 'medium',
    'Hard': 'hard',
    'Category': 'category'
  };

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    if (!row[0]) continue;

    var item = {};
    headers.forEach(function(header, index) {
      var mappedKey = headerMap[header] || header;
      item[mappedKey] = row[index];
    });
    items.push(item);
  }

  return { success: true, items: items };
}

// ═══════════════════════════════════════════════════════════════
// SERVICE CATALOG
// ═══════════════════════════════════════════════════════════════

function getServiceCatalog() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Service Catalog');
  if (!sheet) return { success: false, error: 'Service Catalog sheet not found' };

  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var services = [];

  // Map sheet headers to frontend property names
  var headerMap = {
    'Service ID': 'serviceId',
    'Section Name': 'sectionName',
    'Service Name': 'serviceName',
    'Default Visits': 'defaultVisits',
    'Default Billing Tier': 'defaultBillingTier',
    'Default Proposal Name': 'defaultProposalName',
    'Default Description': 'defaultDescription',
    'Default Map Color': 'defaultMapColor',
    'Items': 'items',
    'Is Manual Entry': 'isManualEntry',
    'Sort Order': 'sortOrder',
    'Last Modified': 'lastModified',
    'Duration Type': 'durationType'
  };

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    if (!row[0]) continue;

    var service = {};
    headers.forEach(function(header, index) {
      var mappedKey = headerMap[header] || header;
      service[mappedKey] = row[index];
    });
    services.push(service);
  }

  return { success: true, services: services };
}

// ═══════════════════════════════════════════════════════════════
// BID SETTINGS
// ═══════════════════════════════════════════════════════════════

function getBidSettings() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Settings');
  if (!sheet) return { success: true, settings: {} };

  var data = sheet.getDataRange().getValues();
  var settings = {};

  for (var i = 1; i < data.length; i++) {
    var key = data[i][0];
    var value = data[i][1];
    if (key) settings[key] = value;
  }

  return { success: true, settings: settings };
}

function saveBidSettings(data) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Settings');
  if (!sheet) {
    SpreadsheetApp.getActiveSpreadsheet().insertSheet('Settings');
  }

  var settingsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Settings');
  settingsSheet.clear();
  settingsSheet.appendRow(['Key', 'Value']);

  var settings = data.settings || data;
  Object.keys(settings).forEach(function(key) {
    if (key !== 'saveBidSettings') {
      settingsSheet.appendRow([key, settings[key]]);
    }
  });

  return { success: true };
}

// ═══════════════════════════════════════════════════════════════
// BIDS
// ═══════════════════════════════════════════════════════════════

function getBids() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Bids');
  if (!sheet) return { success: true, bids: [] };

  var data = sheet.getDataRange().getValues();
  if (data.length <= 1) return { success: true, bids: [] };

  var headers = data[0];
  var bids = [];

  // Map sheet headers to frontend property names
  var headerMap = {
    'Bid ID': 'bidId',
    'Date': 'date',
    'Property Address': 'propertyAddress',
    'Division': 'division',
    'Type': 'propertyType',
    'Lot Size SF': 'lotSizeSF',
    'Labor Rate': 'laborRate',
    'Labor Markup %': 'laborMarkup',
    'Material Markup %': 'materialMarkup',
    'Sub Markup %': 'subMarkup',
    'Travel Time %': 'travelPercent',
    'Total Labor Hours': 'totalLaborHours',
    'Total Labor Cost': 'totalLaborCost',
    'Total Material Cost': 'totalMaterialCost',
    'Total Sub Cost': 'totalSubCost',
    'Internal Cost': 'internalCost',
    'Bid Total': 'bidTotal',
    'Profit': 'profit',
    'Margin %': 'margin',
    'Status': 'status',
    'Notes': 'notes',
    'estimateFileID': 'estimateFileId',
    'Contract ID': 'contractId',
    'Revision Count': 'revisionCount'
  };

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    if (!row[0]) continue;

    var bid = {};
    headers.forEach(function(header, index) {
      var mappedKey = headerMap[header] || header;
      bid[mappedKey] = row[index];
    });
    bids.push(bid);
  }

  return { success: true, bids: bids };
}

function saveBid(bidData) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Bids');

  if (!sheet) {
    return { success: false, error: 'Bids sheet not found' };
  }

  // Map frontend property names to sheet headers
  var propertyToHeader = {
    'bidId': 'Bid ID',
    'date': 'Date',
    'propertyAddress': 'Property Address',
    'division': 'Division',
    'propertyType': 'Type',
    'lotSizeSF': 'Lot Size SF',
    'laborRate': 'Labor Rate',
    'laborMarkup': 'Labor Markup %',
    'materialMarkup': 'Material Markup %',
    'subMarkup': 'Sub Markup %',
    'travelPercent': 'Travel Time %',
    'totalLaborHours': 'Total Labor Hours',
    'totalLaborCost': 'Total Labor Cost',
    'totalMaterialCost': 'Total Material Cost',
    'totalSubCost': 'Total Sub Cost',
    'internalCost': 'Internal Cost',
    'bidTotal': 'Bid Total',
    'profit': 'Profit',
    'margin': 'Margin %',
    'status': 'Status',
    'notes': 'Notes',
    'estimateFileId': 'estimateFileID',
    'contractId': 'Contract ID',
    'revisionCount': 'Revision Count'
  };

  // Reverse map: header to property
  var headerToProperty = {};
  Object.keys(propertyToHeader).forEach(function(prop) {
    headerToProperty[propertyToHeader[prop]] = prop;
  });

  var bidId = 'BID-' + Date.now();
  var date = new Date().toLocaleDateString();

  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var rowData = headers.map(function(header) {
    var prop = headerToProperty[header] || header;
    if (prop === 'bidId' || header === 'Bid ID') return bidId;
    if (prop === 'date' || header === 'Date') return date;
    if (prop === 'services') return JSON.stringify(bidData.services || []);
    return bidData[prop] !== undefined ? bidData[prop] : '';
  });

  sheet.appendRow(rowData);

  return { success: true, bidId: bidId };
}

function updateBid(bidData) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Bids');
  if (!sheet) return { success: false, error: 'Bids sheet not found' };

  var data = sheet.getDataRange().getValues();
  var headers = data[0];

  // Find Bid ID column
  var bidIdCol = headers.indexOf('Bid ID');
  if (bidIdCol === -1) bidIdCol = headers.indexOf('bidId');
  if (bidIdCol === -1) return { success: false, error: 'Bid ID column not found' };

  // Find the row to update
  var rowIndex = -1;
  var searchBidId = String(bidData.bidId);
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][bidIdCol]) === searchBidId) {
      rowIndex = i + 1;
      break;
    }
  }

  if (rowIndex === -1) {
    return { success: false, error: 'Bid not found: ' + searchBidId };
  }

  // Map frontend property names to sheet headers
  var propertyToHeader = {
    'bidId': 'Bid ID',
    'date': 'Date',
    'propertyAddress': 'Property Address',
    'division': 'Division',
    'propertyType': 'Type',
    'lotSizeSF': 'Lot Size SF',
    'laborRate': 'Labor Rate',
    'laborMarkup': 'Labor Markup %',
    'materialMarkup': 'Material Markup %',
    'subMarkup': 'Sub Markup %',
    'travelPercent': 'Travel Time %',
    'totalLaborHours': 'Total Labor Hours',
    'totalLaborCost': 'Total Labor Cost',
    'totalMaterialCost': 'Total Material Cost',
    'totalSubCost': 'Total Sub Cost',
    'internalCost': 'Internal Cost',
    'bidTotal': 'Bid Total',
    'profit': 'Profit',
    'margin': 'Margin %',
    'status': 'Status',
    'notes': 'Notes',
    'estimateFileId': 'estimateFileID',
    'contractId': 'Contract ID',
    'revisionCount': 'Revision Count'
  };

  var headerToProperty = {};
  Object.keys(propertyToHeader).forEach(function(prop) {
    headerToProperty[propertyToHeader[prop]] = prop;
  });

  var rowData = headers.map(function(header) {
    var prop = headerToProperty[header] || header;
    if (prop === 'services') return JSON.stringify(bidData.services || []);
    return bidData[prop] !== undefined ? bidData[prop] : data[rowIndex - 1][headers.indexOf(header)];
  });

  sheet.getRange(rowIndex, 1, 1, rowData.length).setValues([rowData]);

  return { success: true, bidId: bidData.bidId };
}

function deleteBid(bidId) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Bids');
  if (!sheet) return { success: false, error: 'Bids sheet not found' };

  var data = sheet.getDataRange().getValues();
  var headers = data[0];

  // Find Bid ID column (could be 'Bid ID' or 'bidId')
  var bidIdCol = headers.indexOf('Bid ID');
  if (bidIdCol === -1) bidIdCol = headers.indexOf('bidId');
  if (bidIdCol === -1) return { success: false, error: 'Bid ID column not found' };

  var searchBidId = String(bidId);

  for (var i = data.length - 1; i >= 1; i--) {
    var sheetBidId = String(data[i][bidIdCol]);
    if (sheetBidId === searchBidId) {
      sheet.deleteRow(i + 1);
      return { success: true };
    }
  }

  return { success: false, error: 'Bid not found: ' + searchBidId };
}

// ═══════════════════════════════════════════════════════════════
// TEMPLATES
// ═══════════════════════════════════════════════════════════════

function getTemplates() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Templates');
  if (!sheet) return { success: true, templates: [] };

  var data = sheet.getDataRange().getValues();
  if (data.length <= 1) return { success: true, templates: [] };

  var headers = data[0];
  var templates = [];

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    if (!row[0]) continue;

    var template = {};
    headers.forEach(function(header, index) {
      template[header] = row[index];
    });

    if (template.services && typeof template.services === 'string') {
      try { template.services = JSON.parse(template.services); } catch (e) {}
    }
    if (template.takeoffs && typeof template.takeoffs === 'string') {
      try { template.takeoffs = JSON.parse(template.takeoffs); } catch (e) {}
    }

    templates.push(template);
  }

  return { success: true, templates: templates };
}

function getTemplate(templateId) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Templates');
  if (!sheet) return { success: false, error: 'Templates sheet not found' };

  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var templateIdCol = headers.indexOf('templateId');

  for (var i = 1; i < data.length; i++) {
    if (data[i][templateIdCol] === templateId) {
      var template = {};
      headers.forEach(function(header, index) {
        template[header] = data[i][index];
      });

      if (template.services && typeof template.services === 'string') {
        try { template.services = JSON.parse(template.services); } catch (e) {}
      }
      if (template.takeoffs && typeof template.takeoffs === 'string') {
        try { template.takeoffs = JSON.parse(template.takeoffs); } catch (e) {}
      }

      return { success: true, template: template };
    }
  }

  return { success: false, error: 'Template not found' };
}

function saveTemplate(templateData) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Templates');

  if (!sheet) {
    sheet = SpreadsheetApp.getActiveSpreadsheet().insertSheet('Templates');
    var headerRow = ['templateId', 'name', 'division', 'description', 'services', 'takeoffs', 'createdAt', 'updatedAt'];
    sheet.appendRow(headerRow);
  }

  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var templateIdCol = headers.indexOf('templateId');
  var data = sheet.getDataRange().getValues();

  var existingRow = -1;
  if (templateData.templateId) {
    for (var i = 1; i < data.length; i++) {
      if (data[i][templateIdCol] === templateData.templateId) {
        existingRow = i + 1;
        break;
      }
    }
  }

  var templateId = templateData.templateId || 'TPL-' + Date.now();
  var now = new Date().toISOString();

  var rowData = headers.map(function(header) {
    if (header === 'templateId') return templateId;
    if (header === 'createdAt') return existingRow > 0 ? data[existingRow - 1][headers.indexOf('createdAt')] : now;
    if (header === 'updatedAt') return now;
    if (header === 'services') return JSON.stringify(templateData.services || []);
    if (header === 'takeoffs') return JSON.stringify(templateData.takeoffs || {});
    if (header === 'saveTemplate') return '';
    return templateData[header] !== undefined ? templateData[header] : '';
  });

  if (existingRow > 0) {
    sheet.getRange(existingRow, 1, 1, rowData.length).setValues([rowData]);
  } else {
    sheet.appendRow(rowData);
  }

  return { success: true, templateId: templateId };
}

function deleteTemplate(templateId) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Templates');
  if (!sheet) return { success: false, error: 'Templates sheet not found' };

  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var templateIdCol = headers.indexOf('templateId');

  if (templateIdCol === -1) return { success: false, error: 'templateId column not found' };

  var searchTemplateId = String(templateId);

  for (var i = data.length - 1; i >= 1; i--) {
    if (String(data[i][templateIdCol]) === searchTemplateId) {
      sheet.deleteRow(i + 1);
      return { success: true };
    }
  }

  return { success: false, error: 'Template not found' };
}

// ═══════════════════════════════════════════════════════════════
//  CONTRACT & TICKET ENDPOINTS
// ═══════════════════════════════════════════════════════════════

function createContract(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Contracts');

  if (!sheet) {
    sheet = ss.insertSheet('Contracts');
    sheet.getRange(1, 1, 1, 11).setValues([['Contract ID', 'Bid ID', 'Property Address', 'Assigned Crew', 'Preferred Day', 'Start Date', 'End Date', 'Contract Months', 'Monthly Payment', 'Status', 'Created Date']]);
    sheet.getRange(1, 1, 1, 11).setFontWeight('bold');
  }

  var existingData = sheet.getDataRange().getValues();
  var headers = existingData[0];
  var numCols = headers.length;

  var col = {
    contractId: headers.indexOf('Contract ID'),
    bidId: headers.indexOf('Bid ID'),
    propertyAddress: headers.indexOf('Property Address'),
    assignedCrew: headers.indexOf('Assigned Crew'),
    preferredDay: headers.indexOf('Preferred Day'),
    startDate: headers.indexOf('Start Date'),
    endDate: headers.indexOf('End Date'),
    contractMonths: headers.indexOf('Contract Months'),
    monthlyPayment: headers.indexOf('Monthly Payment'),
    status: headers.indexOf('Status'),
    createdDate: headers.indexOf('Created Date')
  };

  var idCol = col.contractId !== -1 ? col.contractId : 0;
  var maxId = 0;
  for (var i = 1; i < existingData.length; i++) {
    var existingId = existingData[i][idCol];
    if (existingId && typeof existingId === 'string' && existingId.indexOf('CTR-') === 0) {
      var num = parseInt(existingId.replace('CTR-', ''), 10);
      if (num > maxId) maxId = num;
    }
  }
  var contractId = 'CTR-' + String(maxId + 1).padStart(3, '0');

  var now = new Date();
  var dateStr = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  // Build row array matching actual column positions
  var row = [];
  for (var c = 0; c < numCols; c++) {
    if (c === col.contractId) row.push(contractId);
    else if (c === col.bidId) row.push(data.bidId || '');
    else if (c === col.propertyAddress) row.push(data.propertyAddress || '');
    else if (c === col.assignedCrew) row.push(data.assignedCrew || '');
    else if (c === col.preferredDay) row.push(data.preferredDay !== undefined ? data.preferredDay : 0);
    else if (c === col.startDate) row.push(data.startDate || '');
    else if (c === col.endDate) row.push(data.endDate || '');
    else if (c === col.contractMonths) row.push(data.contractMonths || 12);
    else if (c === col.monthlyPayment) row.push(data.monthlyPayment || 0);
    else if (c === col.status) row.push('active');
    else if (c === col.createdDate) row.push(dateStr);
    else row.push('');
  }

  sheet.appendRow(row);

  return { success: true, contractId: contractId };
}

function updateContract(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Contracts');
  if (!sheet) return { success: false, error: 'Contracts sheet not found' };

  var rows = sheet.getDataRange().getValues();
  var headers = rows[0];

  var contractIdCol = headers.indexOf('Contract ID');
  if (contractIdCol === -1) contractIdCol = headers.indexOf('contractId');
  if (contractIdCol === -1) return { success: false, error: 'Contract ID column not found' };

  for (var i = 1; i < rows.length; i++) {
    if (String(rows[i][contractIdCol]) === String(data.contractId)) {
      var fieldsToUpdate = {
        'Assigned Crew': data.assignedCrew,
        'Preferred Day': data.preferredDay,
        'Start Date': data.startDate,
        'End Date': data.endDate,
        'Contract Months': data.contractMonths,
        'Monthly Payment': data.monthlyPayment,
        'Status': data.status || 'active'
      };

      for (var field in fieldsToUpdate) {
        var col = headers.indexOf(field);
        if (col >= 0 && fieldsToUpdate[field] !== undefined) {
          sheet.getRange(i + 1, col + 1).setValue(fieldsToUpdate[field]);
        }
      }

      return { success: true, contractId: data.contractId };
    }
  }

  return { success: false, error: 'Contract not found: ' + data.contractId };
}

function deleteFutureTickets(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Scheduled Tickets');
  if (!sheet) return { success: false, error: 'Scheduled Tickets sheet not found' };

  var rows = sheet.getDataRange().getValues();
  var headers = rows[0];

  var contractIdCol = headers.indexOf('contractId');
  if (contractIdCol === -1) contractIdCol = headers.indexOf('Contract ID');
  var statusCol = headers.indexOf('status');
  if (statusCol === -1) statusCol = headers.indexOf('Status');
  var dateCol = headers.indexOf('eventDate');
  if (dateCol === -1) dateCol = headers.indexOf('Event Date');

  var afterDate = data.afterDate;
  var deletedCount = 0;

  for (var i = rows.length - 1; i >= 1; i--) {
    var rowContractId = String(rows[i][contractIdCol]);
    var rowStatus = String(rows[i][statusCol]).toLowerCase();
    var rowDate = rows[i][dateCol];

    if (rowDate instanceof Date) {
      rowDate = Utilities.formatDate(rowDate, Session.getScriptTimeZone(), 'yyyy-MM-dd');
    } else {
      rowDate = String(rowDate);
    }

    if (rowContractId === String(data.contractId) && rowDate > afterDate && rowStatus === 'scheduled') {
      sheet.deleteRow(i + 1);
      deletedCount++;
    }
  }

  return { success: true, deletedCount: deletedCount };
}

function getContracts() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Contracts');

  if (!sheet) {
    return { success: true, contracts: [] };
  }

  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var col = {
    contractId: headers.indexOf('Contract ID'),
    bidId: headers.indexOf('Bid ID'),
    propertyAddress: headers.indexOf('Property Address'),
    assignedCrew: headers.indexOf('Assigned Crew'),
    preferredDay: headers.indexOf('Preferred Day'),
    startDate: headers.indexOf('Start Date'),
    endDate: headers.indexOf('End Date'),
    contractMonths: headers.indexOf('Contract Months'),
    monthlyPayment: headers.indexOf('Monthly Payment'),
    status: headers.indexOf('Status'),
    createdDate: headers.indexOf('Created Date')
  };

  var contracts = [];

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    var contractId = col.contractId !== -1 ? row[col.contractId] : row[0];
    if (contractId) {
      contracts.push({
        contractId: contractId || '',
        bidId: col.bidId !== -1 ? (row[col.bidId] || '') : '',
        propertyAddress: col.propertyAddress !== -1 ? (row[col.propertyAddress] || '') : '',
        assignedCrew: col.assignedCrew !== -1 ? (row[col.assignedCrew] || '') : '',
        preferredDay: col.preferredDay !== -1 ? row[col.preferredDay] : 0,
        startDate: col.startDate !== -1 ? (row[col.startDate] || '') : '',
        endDate: col.endDate !== -1 ? (row[col.endDate] || '') : '',
        contractMonths: col.contractMonths !== -1 ? (row[col.contractMonths] || 12) : 12,
        monthlyPayment: col.monthlyPayment !== -1 ? (row[col.monthlyPayment] || 0) : 0,
        status: col.status !== -1 ? (row[col.status] || 'active') : 'active',
        createdDate: col.createdDate !== -1 ? (row[col.createdDate] || '') : ''
      });
    }
  }

  return { success: true, contracts: contracts };
}

function saveTickets(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Scheduled Tickets');

  if (!sheet) {
    sheet = ss.insertSheet('Scheduled Tickets');
    sheet.getRange(1, 1, 1, 14).setValues([['Ticket ID', 'Contract ID', 'Property Address', 'Assigned Crew', 'Event Date', 'Services JSON', 'Total Est Hours', 'Travel Hours', 'Earned Value', 'Internal Cost', 'Status', 'Completed Date', 'Notes', 'Created Date']]);
    sheet.getRange(1, 1, 1, 14).setFontWeight('bold');
  } else {
    // Auto-upgrade existing sheets to include Earned Value and Internal Cost columns
    var headerRow = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    if (headerRow.indexOf('Earned Value') === -1) {
      var nextCol = sheet.getLastColumn() + 1;
      sheet.getRange(1, nextCol).setValue('Earned Value');
      sheet.getRange(1, nextCol + 1).setValue('Internal Cost');
      sheet.getRange(1, nextCol, 1, 2).setFontWeight('bold');
    }
    // Auto-upgrade: add Needs Reschedule column if missing
    headerRow = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    if (headerRow.indexOf('Needs Reschedule') === -1) {
      var nrCol = sheet.getLastColumn() + 1;
      sheet.getRange(1, nrCol).setValue('Needs Reschedule');
      sheet.getRange(1, nrCol).setFontWeight('bold');
    }
  }

  var tickets = data.tickets || [];
  if (tickets.length === 0) {
    return { success: false, error: 'No tickets to save' };
  }

  // Re-read headers after potential upgrade
  var existingData = sheet.getDataRange().getValues();
  var headers = existingData[0];
  var numCols = headers.length;

  // Build column index map
  var colIdx = {
    ticketId: headers.indexOf('Ticket ID'),
    contractId: headers.indexOf('Contract ID'),
    propertyAddress: headers.indexOf('Property Address'),
    assignedCrew: headers.indexOf('Assigned Crew'),
    eventDate: headers.indexOf('Event Date'),
    services: headers.indexOf('Services JSON'),
    totalEstHours: headers.indexOf('Total Est Hours'),
    travelHours: headers.indexOf('Travel Hours'),
    earnedValue: headers.indexOf('Earned Value'),
    internalCost: headers.indexOf('Internal Cost'),
    status: headers.indexOf('Status'),
    completedDate: headers.indexOf('Completed Date'),
    notes: headers.indexOf('Notes'),
    createdDate: headers.indexOf('Created Date'),
    stopOrder: headers.indexOf('Stop Order'),
    needsReschedule: headers.indexOf('Needs Reschedule')
  };

  var maxId = 0;
  var idCol = colIdx.ticketId !== -1 ? colIdx.ticketId : 0;
  for (var i = 1; i < existingData.length; i++) {
    var existingId = existingData[i][idCol];
    if (existingId && typeof existingId === 'string' && existingId.indexOf('TKT-') === 0) {
      var num = parseInt(existingId.replace('TKT-', ''), 10);
      if (num > maxId) maxId = num;
    }
  }

  var now = new Date();
  var dateStr = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  var rows = [];
  for (var j = 0; j < tickets.length; j++) {
    var t = tickets[j];
    var ticketId = 'TKT-' + String(maxId + 1 + j).padStart(4, '0');

    // Build row array matching actual column positions
    var row = [];
    for (var c = 0; c < numCols; c++) {
      if (c === colIdx.ticketId) row.push(ticketId);
      else if (c === colIdx.contractId) row.push(t.contractId || '');
      else if (c === colIdx.propertyAddress) row.push(t.propertyAddress || '');
      else if (c === colIdx.assignedCrew) row.push(t.assignedCrew || '');
      else if (c === colIdx.eventDate) row.push(t.eventDate || '');
      else if (c === colIdx.services) row.push(typeof t.services === 'string' ? t.services : JSON.stringify(t.services || []));
      else if (c === colIdx.totalEstHours) row.push(t.totalEstHours || 0);
      else if (c === colIdx.travelHours) row.push(t.travelHours || 0);
      else if (c === colIdx.earnedValue) row.push(t.earnedValue || 0);
      else if (c === colIdx.internalCost) row.push(t.internalCost || 0);
      else if (c === colIdx.status) row.push('scheduled');
      else if (c === colIdx.completedDate) row.push('');
      else if (c === colIdx.notes) row.push('');
      else if (c === colIdx.createdDate) row.push(dateStr);
      else if (c === colIdx.stopOrder) row.push('');
      else if (c === colIdx.needsReschedule) row.push('');
      else row.push('');
    }
    rows.push(row);
  }

  if (rows.length > 0) {
    var lastRow = sheet.getLastRow();
    sheet.getRange(lastRow + 1, 1, rows.length, numCols).setValues(rows);
  }

  return { success: true, ticketCount: rows.length };
}

function getTickets(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Scheduled Tickets');

  if (!sheet) {
    return { success: true, tickets: [] };
  }

  // Read parameters — support both old (contractId string) and new (event object) calling styles
  var contractId = '';
  var startDate = '';
  var endDate = '';
  var crew = '';
  var needsRescheduleFilter = false;

  if (typeof e === 'string') {
    // Legacy: called as getTickets('CTR-001')
    contractId = e;
  } else if (e && e.parameter) {
    // New: called as getTickets(e) with URL params
    contractId = e.parameter.contractId || '';
    startDate = e.parameter.startDate || '';
    endDate = e.parameter.endDate || '';
    crew = e.parameter.crew || '';
    needsRescheduleFilter = e.parameter.needsReschedule === 'true';
  }

  var data = sheet.getDataRange().getValues();
  var headers = data[0];

  // Find column indices dynamically
  var colMap = {};
  var colAliases = {
    'ticketId': ['Ticket ID'],
    'contractId': ['Contract ID'],
    'propertyAddress': ['Property Address'],
    'assignedCrew': ['Assigned Crew'],
    'eventDate': ['Event Date'],
    'services': ['Services JSON'],
    'totalEstHours': ['Total Est Hours'],
    'travelHours': ['Travel Hours'],
    'earnedValue': ['Earned Value'],
    'internalCost': ['Internal Cost'],
    'status': ['Status'],
    'completedDate': ['Completed Date'],
    'notes': ['Notes'],
    'createdDate': ['Created Date'],
    'stopOrder': ['Stop Order'],
    'needsReschedule': ['Needs Reschedule']
  };

  Object.keys(colAliases).forEach(function(key) {
    colMap[key] = -1;
    for (var a = 0; a < colAliases[key].length; a++) {
      var idx = headers.indexOf(colAliases[key][a]);
      if (idx !== -1) { colMap[key] = idx; break; }
    }
  });

  var tickets = [];

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    if (!row[colMap.ticketId !== -1 ? colMap.ticketId : 0]) continue;

    // Normalize event date
    var rawDate = colMap.eventDate !== -1 ? row[colMap.eventDate] : '';
    var eventDateStr = '';
    if (rawDate instanceof Date) {
      eventDateStr = rawDate.getFullYear() + '-' +
        String(rawDate.getMonth() + 1).padStart(2, '0') + '-' +
        String(rawDate.getDate()).padStart(2, '0');
    } else {
      eventDateStr = String(rawDate || '');
      if (eventDateStr.indexOf('T') !== -1) eventDateStr = eventDateStr.split('T')[0];
    }

    // Determine needsReschedule flag for this row
    var rowNeedsReschedule = colMap.needsReschedule !== -1 && String(row[colMap.needsReschedule] || '').toUpperCase() === 'TRUE';

    // Apply filters
    if (contractId && String(row[colMap.contractId] || '') !== contractId) continue;
    if (crew && String(row[colMap.assignedCrew] || '') !== crew) continue;
    if (needsRescheduleFilter) {
      // When filtering for queue, skip date filters — queue spans all dates
      if (!rowNeedsReschedule) continue;
    } else {
      if (startDate && eventDateStr < startDate) continue;
      if (endDate && eventDateStr > endDate) continue;
    }

    tickets.push({
      ticketId: colMap.ticketId !== -1 ? (row[colMap.ticketId] || '') : '',
      contractId: colMap.contractId !== -1 ? (row[colMap.contractId] || '') : '',
      propertyAddress: colMap.propertyAddress !== -1 ? (row[colMap.propertyAddress] || '') : '',
      assignedCrew: colMap.assignedCrew !== -1 ? (row[colMap.assignedCrew] || '') : '',
      eventDate: eventDateStr,
      services: colMap.services !== -1 ? (row[colMap.services] || '[]') : '[]',
      totalEstHours: colMap.totalEstHours !== -1 ? (row[colMap.totalEstHours] || 0) : 0,
      travelHours: colMap.travelHours !== -1 ? (row[colMap.travelHours] || 0) : 0,
      earnedValue: colMap.earnedValue !== -1 ? (parseFloat(row[colMap.earnedValue]) || 0) : 0,
      internalCost: colMap.internalCost !== -1 ? (parseFloat(row[colMap.internalCost]) || 0) : 0,
      status: (function() {
        if (colMap.status === -1) return 'scheduled';
        var rawStatus = row[colMap.status];
        if (!rawStatus) return 'scheduled';
        var s = String(rawStatus).toLowerCase().trim();
        // Only accept valid status values
        if (s === 'scheduled' || s === 'completed' || s === 'skipped' || s === 'rescheduled' || s === 'partial') return s;
        return 'scheduled';
      })(),
      completedDate: colMap.completedDate !== -1 ? (row[colMap.completedDate] || '') : '',
      notes: colMap.notes !== -1 ? (row[colMap.notes] || '') : '',
      createdDate: colMap.createdDate !== -1 ? (row[colMap.createdDate] || '') : '',
      stopOrder: colMap.stopOrder !== -1 ? (row[colMap.stopOrder] || null) : null,
      needsReschedule: rowNeedsReschedule
    });
  }

  // Look up actual hours from Time Entries for completed tickets
  var timeSheet = ss.getSheetByName('Time Entries');
  if (timeSheet) {
    var teData = timeSheet.getDataRange().getValues();
    var teHeaders = teData[0];
    var teTicketCol = teHeaders.indexOf('Ticket ID');
    var teTypeCol = teHeaders.indexOf('Entry Type');
    var teDurationCol = teHeaders.indexOf('Duration Minutes');

    if (teTicketCol !== -1 && teDurationCol !== -1) {
      // Build a map of ticketId -> total actual minutes (sum all job entries)
      var actualMinutesMap = {};
      for (var te = 1; te < teData.length; te++) {
        var teType = teTypeCol !== -1 ? String(teData[te][teTypeCol] || '') : '';
        if (teType !== 'job') continue;
        var teTicketId = String(teData[te][teTicketCol] || '');
        var teDuration = parseFloat(teData[te][teDurationCol]) || 0;
        if (teTicketId && teDuration > 0) {
          actualMinutesMap[teTicketId] = (actualMinutesMap[teTicketId] || 0) + teDuration;
        }
      }

      // Attach actual hours to completed tickets
      for (var j = 0; j < tickets.length; j++) {
        var tid = tickets[j].ticketId;
        if (actualMinutesMap[tid] !== undefined) {
          tickets[j].actualHours = parseFloat((actualMinutesMap[tid] / 60).toFixed(4));
        }
      }
    }
  }

  return { success: true, tickets: tickets };
}

function updateTicketStatus(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Scheduled Tickets');

  if (!sheet) {
    return { success: false, error: 'Scheduled Tickets sheet not found' };
  }

  var sheetData = sheet.getDataRange().getValues();
  var headers = sheetData[0];
  var ticketIdCol = headers.indexOf('Ticket ID');
  var statusCol = headers.indexOf('Status');
  var completedDateCol = headers.indexOf('Completed Date');
  var notesCol = headers.indexOf('Notes');
  var needsRescheduleCol = headers.indexOf('Needs Reschedule');

  if (ticketIdCol === -1) ticketIdCol = 0;

  for (var i = 1; i < sheetData.length; i++) {
    if (sheetData[i][ticketIdCol] === data.ticketId) {
      if (statusCol !== -1) {
        sheet.getRange(i + 1, statusCol + 1).setValue(data.status || 'scheduled');
      }
      if (data.completedDate && completedDateCol !== -1) {
        sheet.getRange(i + 1, completedDateCol + 1).setValue(data.completedDate);
      }
      if (data.notes && notesCol !== -1) {
        sheet.getRange(i + 1, notesCol + 1).setValue(data.notes);
      }
      // Auto-set needsReschedule when status is skipped
      if (needsRescheduleCol !== -1 && String(data.status || '').toLowerCase() === 'skipped') {
        sheet.getRange(i + 1, needsRescheduleCol + 1).setValue('TRUE');
      }
      return { success: true };
    }
  }

  return { success: false, error: 'Ticket not found' };
}

/**
 * Reopen a completed service on a ticket.
 * Removes the service from the Completed Services JSON column.
 * If revertStatus is true and ticket is completed, reverts to partial.
 * POST: { reopenTicketService: true, ticketId, serviceName, revertStatus }
 */
function reopenTicketService(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Scheduled Tickets');
  if (!sheet) return { success: false, error: 'Scheduled Tickets sheet not found' };

  var sheetData = sheet.getDataRange().getValues();
  var headers = sheetData[0];
  var ticketIdCol = headers.indexOf('Ticket ID');
  var statusCol = headers.indexOf('Status');
  var completedServicesCol = headers.indexOf('Completed Services');

  if (ticketIdCol === -1) ticketIdCol = 0;

  for (var i = 1; i < sheetData.length; i++) {
    if (sheetData[i][ticketIdCol] === data.ticketId) {
      // Remove service from Completed Services JSON
      if (completedServicesCol !== -1) {
        var raw = sheetData[i][completedServicesCol] || '[]';
        var completedArr = [];
        try { completedArr = JSON.parse(raw); } catch(e) {}
        var idx = completedArr.indexOf(data.serviceName);
        if (idx >= 0) completedArr.splice(idx, 1);
        sheet.getRange(i + 1, completedServicesCol + 1).setValue(JSON.stringify(completedArr));
      }
      // Revert status from completed to partial if requested
      if (data.revertStatus && statusCol !== -1 && sheetData[i][statusCol] === 'completed') {
        sheet.getRange(i + 1, statusCol + 1).setValue('partial');
      }
      return { success: true };
    }
  }

  return { success: false, error: 'Ticket not found' };
}

function rescheduleTicket(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Scheduled Tickets');

  if (!sheet) {
    return { success: false, error: 'Scheduled Tickets sheet not found' };
  }

  var sheetData = sheet.getDataRange().getValues();
  var headers = sheetData[0];
  var ticketIdCol = headers.indexOf('Ticket ID');
  var eventDateCol = headers.indexOf('Event Date');
  var statusCol = headers.indexOf('Status');
  var needsRescheduleCol = headers.indexOf('Needs Reschedule');

  if (ticketIdCol === -1) ticketIdCol = 0;

  for (var i = 1; i < sheetData.length; i++) {
    if (sheetData[i][ticketIdCol] === data.ticketId) {
      if (eventDateCol !== -1) {
        sheet.getRange(i + 1, eventDateCol + 1).setValue(data.newDate);
      }
      if (statusCol !== -1) {
        sheet.getRange(i + 1, statusCol + 1).setValue('rescheduled');
      }
      // Clear needsReschedule flag when ticket is rescheduled
      if (needsRescheduleCol !== -1) {
        sheet.getRange(i + 1, needsRescheduleCol + 1).setValue('');
      }
      return { success: true };
    }
  }

  return { success: false, error: 'Ticket not found' };
}

/**
 * Bulk skip all tickets for a crew on a specific date.
 * POST: { bulkSkipDay: true, crew: 'MNT-Jake', date: '2026-02-23', reason: 'Weather' }
 * Sets status → 'skipped', Needs Reschedule → TRUE, Notes → reason
 */
function bulkSkipDay(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Scheduled Tickets');

  if (!sheet) {
    return { success: false, error: 'Scheduled Tickets sheet not found' };
  }

  var sheetData = sheet.getDataRange().getValues();
  var headers = sheetData[0];
  var ticketIdCol = headers.indexOf('Ticket ID');
  var assignedCrewCol = headers.indexOf('Assigned Crew');
  var eventDateCol = headers.indexOf('Event Date');
  var statusCol = headers.indexOf('Status');
  var notesCol = headers.indexOf('Notes');
  var needsRescheduleCol = headers.indexOf('Needs Reschedule');

  if (ticketIdCol === -1) ticketIdCol = 0;

  var targetDate = String(data.date || '');
  var targetCrew = String(data.crew || '');
  var reason = String(data.reason || 'Skipped');
  var skippedCount = 0;
  var skippedIds = [];

  for (var i = 1; i < sheetData.length; i++) {
    var row = sheetData[i];

    // Match crew
    if (assignedCrewCol !== -1 && String(row[assignedCrewCol] || '') !== targetCrew) continue;

    // Match date (normalize Date objects)
    var rawDate = eventDateCol !== -1 ? row[eventDateCol] : '';
    var eventDateStr = '';
    if (rawDate instanceof Date) {
      eventDateStr = rawDate.getFullYear() + '-' +
        String(rawDate.getMonth() + 1).padStart(2, '0') + '-' +
        String(rawDate.getDate()).padStart(2, '0');
    } else {
      eventDateStr = String(rawDate || '');
      if (eventDateStr.indexOf('T') !== -1) eventDateStr = eventDateStr.split('T')[0];
    }
    if (eventDateStr !== targetDate) continue;

    // Only skip tickets that are scheduled or partial
    var currentStatus = statusCol !== -1 ? String(row[statusCol] || '').toLowerCase().trim() : 'scheduled';
    if (currentStatus !== 'scheduled' && currentStatus !== 'partial') continue;

    // Apply skip
    var rowNum = i + 1;
    if (statusCol !== -1) sheet.getRange(rowNum, statusCol + 1).setValue('skipped');
    if (needsRescheduleCol !== -1) sheet.getRange(rowNum, needsRescheduleCol + 1).setValue('TRUE');
    if (notesCol !== -1) sheet.getRange(rowNum, notesCol + 1).setValue(reason);

    skippedCount++;
    skippedIds.push(row[ticketIdCol] || '');
  }

  return { success: true, skippedCount: skippedCount, skippedIds: skippedIds };
}


// ═══════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════
//  TEXT MY TEAM FUNCTIONS
// ═══════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════


// ═══════════════════════════════════════════════════════════════
//  GET REQUESTS (Auth + Request Loading)
// ═══════════════════════════════════════════════════════════════

function getRequests(phone) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  var crewSheet = ss.getSheetByName('Crew');
  var propsSheet = ss.getSheetByName('Properties');

  // ─── Auth: check phone against Crew Members first, then Crew, then Properties ───
  var crewName = null;

  // ─── Auth: check Crew Members first ───
  var cmSheet = ss.getSheetByName('Crew Members');
  if (cmSheet && !crewName) {
    var cmData = cmSheet.getDataRange().getValues();
    var cmHeaders = cmData[0];
    var cmPhoneCol = findCol(cmHeaders, ['Phone', 'phone']);
    var cmNameCol = findCol(cmHeaders, ['Name', 'name']);
    var cmRoleCol = findCol(cmHeaders, ['Role', 'role']);
    var cmCrewCol = findCol(cmHeaders, ['Crew', 'crew']);

    if (cmPhoneCol !== -1) {
      var cleanPhone = String(phone).replace(/\D/g, '');
      for (var cm = 1; cm < cmData.length; cm++) {
        var cmPhone = String(cmData[cm][cmPhoneCol]).replace(/\D/g, '');
        var cmRole = cmRoleCol !== -1 ? String(cmData[cm][cmRoleCol]).toLowerCase() : '';
        if (cmPhone === cleanPhone && cmRole === 'leader') {
          crewName = cmData[cm][cmNameCol];
          break;
        }
      }
    }
  }

  if (crewSheet && !crewName) {
    var crewData = crewSheet.getDataRange().getValues();
    var crewHeaders = crewData[0];
    var cPhoneCol = findCol(crewHeaders, ['Phone', 'phone', 'Crew Phone']);
    var cNameCol = findCol(crewHeaders, ['Name', 'name', 'Crew Leader', 'crewLeader']);

    if (cPhoneCol !== -1) {
      for (var i = 1; i < crewData.length; i++) {
        var crewPhone = String(crewData[i][cPhoneCol]).replace(/\D/g, '');
        if (crewPhone === String(phone).replace(/\D/g, '')) {
          crewName = crewData[i][cNameCol !== -1 ? cNameCol : 0];
          break;
        }
      }
    }
  }

  // If no Crew sheet or not found there, check Properties sheet
  if (!crewName && propsSheet) {
    var propsData = propsSheet.getDataRange().getValues();
    var propsHeaders = propsData[0];
    var pPhoneCol = findCol(propsHeaders, ['Crew Phone', 'Phone', 'phone']);
    var pCrewCol = findCol(propsHeaders, ['Crew Leader', 'Crew', 'crew']);

    if (pPhoneCol !== -1 && pCrewCol !== -1) {
      for (var j = 1; j < propsData.length; j++) {
        var propPhone = String(propsData[j][pPhoneCol]).replace(/\D/g, '');
        if (propPhone === String(phone).replace(/\D/g, '')) {
          crewName = propsData[j][pCrewCol];
          break;
        }
      }
    }
  }

  if (!crewName) return { authorized: false };

  // ─── Load properties for this crew ───
  var crewProperties = [];
  if (propsSheet) {
    var pData = propsSheet.getDataRange().getValues();
    var pH = pData[0];
    var pAddr = findCol(pH, ['Address', 'address', 'Property Address']);
    var pCrew = findCol(pH, ['Crew Leader', 'Crew', 'crew', 'Assigned Crew']);

    if (pAddr !== -1 && pCrew !== -1) {
      for (var p = 1; p < pData.length; p++) {
        var pc = String(pData[p][pCrew]);
        if (pc === crewName || pc.indexOf(crewName) !== -1) {
          crewProperties.push(String(pData[p][pAddr]));
        }
      }
    }
  }

  // ─── Load requests ───
  var reqSheet = ss.getSheetByName('Requests');
  if (!reqSheet) return { authorized: true, crewName: crewName, requests: [] };

  var reqData = reqSheet.getDataRange().getValues();
  var reqHeaders = reqData[0];

  var colMap = {};
  var headerAliases = {
    'id': ['ID', 'id', 'Request ID', 'requestId'],
    'property': ['Property', 'property', 'Property Address', 'propertyAddress'],
    'date': ['Date', 'date', 'Timestamp'],
    'time': ['Time', 'time'],
    'message': ['Message', 'message', 'Description'],
    'customerName': ['Customer Name', 'customerName', 'Name'],
    'customerPhone': ['Customer Phone', 'customerPhone'],
    'status': ['Status', 'status'],
    'photo': ['Photo', 'photo', 'Photo URL'],
    'translatedMessage': ['Translated Message', 'translatedMessage', 'Translation'],
    'acknowledged': ['Acknowledged', 'acknowledged'],
    'type': ['Type', 'type'],
    'crewLeader': ['Crew Leader', 'crewLeader', 'Crew'],
    'completedDate': ['Completed Date', 'completedDate'],
    'completedPhoto': ['Completed Photo', 'completedPhoto', 'Completion Photo']
  };

  Object.keys(headerAliases).forEach(function(key) {
    colMap[key] = findCol(reqHeaders, headerAliases[key]);
  });

  var requests = [];
  for (var r = 1; r < reqData.length; r++) {
    var row = reqData[r];
    var reqProperty = colMap.property !== -1 ? String(row[colMap.property]) : '';

    var isCrewProperty = false;
    for (var cp = 0; cp < crewProperties.length; cp++) {
      if (reqProperty === crewProperties[cp] || reqProperty.indexOf(crewProperties[cp]) !== -1 || crewProperties[cp].indexOf(reqProperty) !== -1) {
        isCrewProperty = true;
        break;
      }
    }

    var reqCrew = colMap.crewLeader !== -1 ? String(row[colMap.crewLeader]) : '';
    if (reqCrew === crewName || reqCrew.indexOf(crewName) !== -1) {
      isCrewProperty = true;
    }

    if (!isCrewProperty && crewProperties.length > 0) continue;

    var request = {};
    Object.keys(colMap).forEach(function(key) {
      request[key] = colMap[key] !== -1 ? row[colMap[key]] : '';
    });

    if (!request.id) {
      request.id = r;
    }

    requests.push(request);
  }

  return { authorized: true, crewName: crewName, requests: requests };
}

// ═══════════════════════════════════════════════════════════════
//  GET PROPERTIES
// ═══════════════════════════════════════════════════════════════

function getProperties() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Properties');
  if (!sheet) return { success: true, properties: [] };

  var data = sheet.getDataRange().getValues();
  var headers = data[0];

  var addrCol = findCol(headers, ['Address', 'address', 'Property Address']);
  var crewCol = findCol(headers, ['Crew', 'crew', 'Crew Leader', 'Assigned Crew']);
  var phoneCol = findCol(headers, ['Phone', 'phone', 'Crew Phone', 'Crew Leader Phone']);
  var pinCol = findCol(headers, ['Pin', 'pin', 'PIN']);

  var properties = [];
  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    if (!row[addrCol !== -1 ? addrCol : 0]) continue;

    properties.push({
      address: addrCol !== -1 ? row[addrCol] : '',
      crew: crewCol !== -1 ? row[crewCol] : '',
      phone: phoneCol !== -1 ? String(row[phoneCol]) : '',
      pin: pinCol !== -1 ? String(row[pinCol]) : ''
    });
  }

  return { success: true, properties: properties };
}

// ═══════════════════════════════════════════════════════════════
//  SUBMIT REQUEST (Internal from crew or External from customer)
// ═══════════════════════════════════════════════════════════════

function submitRequest(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Requests');
  if (!sheet) return { success: false, error: 'Requests sheet not found' };

  var lastCol = sheet.getLastColumn();
  if (lastCol === 0) return { success: false, error: 'No headers found in Requests sheet' };

  var headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  Logger.log('Headers found: ' + JSON.stringify(headers));
  Logger.log('Data received: ' + JSON.stringify(data));

  var now = new Date();
  var dateStr = data.date || now.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  var timeStr = data.time || now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true, timeZoneName: 'short' });

  var lastRow = sheet.getLastRow();
  var newId = lastRow;

  // Translate the message (English ↔ Spanish)
  var translatedMessage = '';
  if (data.message && data.message.trim().length > 0) {
    try {
      // Detect language and translate
      var detected = LanguageApp.translate(data.message, '', 'en'); // Translate to English to detect
      var isSpanish = (detected !== data.message); // If translation changed it, original was not English

      if (isSpanish) {
        // Original is Spanish, translate to English
        translatedMessage = LanguageApp.translate(data.message, 'es', 'en');
      } else {
        // Original is English, translate to Spanish
        translatedMessage = LanguageApp.translate(data.message, 'en', 'es');
      }
    } catch (e) {
      Logger.log('Translation error: ' + e.toString());
      translatedMessage = '';
    }
  }

  var fieldMap = {
    'ID': newId,
    'id': newId,
    'Request ID': newId,
    'Date': dateStr,
    'date': dateStr,
    'Timestamp': dateStr,
    'Time': timeStr,
    'time': timeStr,
    'Property': data.propertyAddress || '',
    'property': data.propertyAddress || '',
    'Property Address': data.propertyAddress || '',
    'Customer Name': data.customerName || '',
    'customerName': data.customerName || '',
    'Name': data.customerName || '',
    'Customer Phone': data.customerPhone || '',
    'customerPhone': data.customerPhone || '',
    'Message': data.message || '',
    'message': data.message || '',
    'Description': data.message || '',
    'Status': data.status || 'Open',
    'status': data.status || 'Open',
    'Photo': data.photoUrl || '',
    'photo': data.photoUrl || '',
    'Photo URL': data.photoUrl || '',
    'Type': data.type || 'External',
    'type': data.type || 'External',
    'Crew Leader': data.crewLeader || '',
    'crewLeader': data.crewLeader || '',
    'Crew': data.crewLeader || '',
    'Crew Leader Phone': data.crewLeaderPhone || '',
    'crewLeaderPhone': data.crewLeaderPhone || '',
    'Acknowledged': '',
    'acknowledged': '',
    'Completed Date': '',
    'completedDate': '',
    'Completed Photo': '',
    'completedPhoto': '',
    'Translated Message': translatedMessage,
    'translatedMessage': translatedMessage
  };

  var rowData = headers.map(function(header) {
    return fieldMap[header] !== undefined ? fieldMap[header] : '';
  });

  Logger.log('Row data to write: ' + JSON.stringify(rowData));

  sheet.appendRow(rowData);
  SpreadsheetApp.flush(); // Force write immediately

  return { success: true, photoUrl: data.photoUrl || '', rowWritten: rowData.length };
}

// ═══════════════════════════════════════════════════════════════
//  UPDATE ACKNOWLEDGED
// ═══════════════════════════════════════════════════════════════

function updateAcknowledged(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Requests');
  if (!sheet) return { success: false, error: 'Requests sheet not found' };

  var sheetData = sheet.getDataRange().getValues();
  var headers = sheetData[0];
  var idCol = findCol(headers, ['ID', 'id', 'Request ID']);
  var ackCol = findCol(headers, ['Acknowledged', 'acknowledged']);

  if (ackCol === -1) return { success: false, error: 'Acknowledged column not found' };

  var searchId = String(data.requestId);
  for (var i = 1; i < sheetData.length; i++) {
    // Match by ID column if it exists, or by row number
    var rowMatches = (idCol !== -1 && String(sheetData[i][idCol]) === searchId) || i === Number(searchId);
    if (rowMatches) {
      sheet.getRange(i + 1, ackCol + 1).setValue(data.acknowledged);
      SpreadsheetApp.flush();
      return { success: true };
    }
  }

  return { success: false, error: 'Request not found: ' + searchId };
}

// ═══════════════════════════════════════════════════════════════
//  UPDATE STATUS
// ═══════════════════════════════════════════════════════════════

function updateStatus(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Requests');
  if (!sheet) return { success: false, error: 'Requests sheet not found' };

  var sheetData = sheet.getDataRange().getValues();
  var headers = sheetData[0];
  var idCol = findCol(headers, ['ID', 'id', 'Request ID']);
  var statusCol = findCol(headers, ['Status', 'status']);
  var completedDateCol = findCol(headers, ['Completed Date', 'completedDate']);
  var completedPhotoCol = findCol(headers, ['Completed Photo', 'completedPhoto', 'Completion Photo']);

  if (statusCol === -1) return { success: false, error: 'Status column not found' };

  var searchId = String(data.requestId);
  for (var i = 1; i < sheetData.length; i++) {
    // Match by ID column if it exists, or by row number
    var rowMatches = (idCol !== -1 && String(sheetData[i][idCol]) === searchId) || i === Number(searchId);
    if (rowMatches) {
      sheet.getRange(i + 1, statusCol + 1).setValue(data.status);

      if (data.completedDate && completedDateCol !== -1) {
        sheet.getRange(i + 1, completedDateCol + 1).setValue(data.completedDate);
      }
      if (data.completedPhoto && completedPhotoCol !== -1) {
        sheet.getRange(i + 1, completedPhotoCol + 1).setValue(data.completedPhoto);
      }
      SpreadsheetApp.flush();
      return { success: true };
    }
  }

  return { success: false, error: 'Request not found: ' + searchId };
}

// ═══════════════════════════════════════════════════════════════
//  PHOTO UPLOAD (General)
// ═══════════════════════════════════════════════════════════════

function uploadPhoto(data) {
  var folder = getPropertyFolder(data.property, 'Photos');
  var filename = (data.filename || 'Photo') + '.jpg';

  // Strip data URL prefix if present (e.g., "data:image/jpeg;base64,")
  var photoData = data.photo;
  if (photoData && photoData.indexOf(',') !== -1) {
    photoData = photoData.split(',')[1];
  }

  var blob = Utilities.newBlob(Utilities.base64Decode(photoData), 'image/jpeg', filename);
  var file = folder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  return {
    success: true,
    photoUrl: 'https://drive.google.com/uc?export=view&id=' + file.getId(),
    fileId: file.getId()
  };
}

// ═══════════════════════════════════════════════════════════════
//  QUICK PHOTOS (Inspection Photos)
// ═══════════════════════════════════════════════════════════════

function uploadInspectionPhoto(data) {
  var propertyFolder = getPropertyFolder(data.property, 'Photos');

  var targetFolder = propertyFolder;
  if (data.reportName) {
    var subFolders = propertyFolder.getFoldersByName(data.reportName);
    if (subFolders.hasNext()) {
      targetFolder = subFolders.next();
    } else {
      targetFolder = propertyFolder.createFolder(data.reportName);
    }
  }

  // Strip data URL prefix if present
  var photoData = data.photo;
  if (photoData && photoData.indexOf(',') !== -1) {
    photoData = photoData.split(',')[1];
  }

  var filename = (data.filename || 'Photo') + '.jpg';
  var blob = Utilities.newBlob(Utilities.base64Decode(photoData), 'image/jpeg', filename);
  var file = targetFolder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  return {
    success: true,
    photoUrl: 'https://drive.google.com/uc?export=view&id=' + file.getId(),
    fileId: file.getId()
  };
}

// ═══════════════════════════════════════════════════════════════
//  SITE REPORT PDF UPLOAD
// ═══════════════════════════════════════════════════════════════

function uploadSiteReportPdf(data) {
  var folder = getPropertyFolder(data.property, 'Site Reports');
  var filename = (data.filename || 'Site Report') + '.pdf';

  // Strip data URL prefix if present
  var pdfData = data.pdfBase64;
  if (pdfData && pdfData.indexOf(',') !== -1) {
    pdfData = pdfData.split(',')[1];
  }

  var blob = Utilities.newBlob(Utilities.base64Decode(pdfData), 'application/pdf', filename);
  var file = folder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  return {
    success: true,
    pdfUrl: file.getUrl(),
    fileId: file.getId()
  };
}

// ═══════════════════════════════════════════════════════════════
//  SITE REPORT PHOTO UPLOAD
// ═══════════════════════════════════════════════════════════════

function uploadSiteReportPhoto(data) {
  var folder = getPropertyFolder(data.property, 'Site Reports');

  var reportFolderName = data.filename || 'Report Photos';
  var subFolders = folder.getFoldersByName(reportFolderName);
  var targetFolder;
  if (subFolders.hasNext()) {
    targetFolder = subFolders.next();
  } else {
    targetFolder = folder.createFolder(reportFolderName);
  }

  // Strip data URL prefix if present
  var photoData = data.photoBase64;
  if (photoData && photoData.indexOf(',') !== -1) {
    photoData = photoData.split(',')[1];
  }

  var photoFilename = 'Photo ' + (data.photoIndex + 1) + '.jpg';
  var blob = Utilities.newBlob(Utilities.base64Decode(photoData), 'image/jpeg', photoFilename);
  var file = targetFolder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  return {
    success: true,
    photoUrl: 'https://drive.google.com/uc?export=view&id=' + file.getId(),
    fileId: file.getId()
  };
}

// ═══════════════════════════════════════════════════════════════
//  SITE REPORT JSON DATA SAVE
// ═══════════════════════════════════════════════════════════════

function saveSiteReportJson(data) {
  var folder = getPropertyFolder(data.property, 'Site Reports');
  var filename = (data.filename || 'Report Data') + '.json';

  var jsonStr = JSON.stringify(data.jsonData);
  var blob = Utilities.newBlob(jsonStr, 'application/json', filename);
  var file = folder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  return {
    success: true,
    fileId: file.getId()
  };
}

// ═══════════════════════════════════════════════════════════════
//  GET SAVED REPORTS (for Before & After)
// ═══════════════════════════════════════════════════════════════

function getSavedReports(property) {
  if (!property) return { success: false, error: 'No property provided' };

  try {
    var mainFolder = DriveApp.getFolderById(TEXT_MY_TEAM_DRIVE_FOLDER_ID);
    var streetAddress = property.split(',')[0].trim();

    var propFolders = mainFolder.getFoldersByName(streetAddress);
    if (!propFolders.hasNext()) return { success: true, reports: [] };

    var propFolder = propFolders.next();
    var reportFolders = propFolder.getFoldersByName('Site Reports');
    if (!reportFolders.hasNext()) return { success: true, reports: [] };

    var siteReportsFolder = reportFolders.next();

    var files = siteReportsFolder.getFilesByType('application/json');
    var reports = [];

    while (files.hasNext()) {
      var file = files.next();
      reports.push({
        id: file.getId(),
        name: file.getName().replace('.json', ''),
        date: file.getDateCreated().toISOString()
      });
    }

    reports.sort(function(a, b) {
      return new Date(b.date) - new Date(a.date);
    });

    return { success: true, reports: reports };
  } catch (err) {
    Logger.log('getSavedReports error: ' + err);
    return { success: false, error: err.toString() };
  }
}

// ═══════════════════════════════════════════════════════════════
//  GET REPORT DATA (Read JSON from Drive)
// ═══════════════════════════════════════════════════════════════

function getReportData(fileId) {
  try {
    if (!fileId) return { success: false, error: 'No fileId provided' };

    var file = DriveApp.getFileById(fileId);
    var content = file.getBlob().getDataAsString();
    var data = JSON.parse(content);

    return { success: true, data: data };
  } catch (err) {
    Logger.log('getReportData error: ' + err);
    return { success: false, error: err.toString() };
  }
}

// ═══════════════════════════════════════════════════════════════
//  GET PHOTO BASE64 (Read photo from Drive)
// ═══════════════════════════════════════════════════════════════

function getPhotoBase64(fileId) {
  try {
    if (!fileId) return { success: false, error: 'No fileId provided' };

    var file = DriveApp.getFileById(fileId);
    var blob = file.getBlob();
    var base64 = Utilities.base64Encode(blob.getBytes());
    var mimeType = blob.getContentType() || 'image/jpeg';

    return {
      success: true,
      base64: 'data:' + mimeType + ';base64,' + base64
    };
  } catch (err) {
    Logger.log('getPhotoBase64 error: ' + err);
    return { success: false, error: err.toString() };
  }
}

// ═══════════════════════════════════════════════════════════════
//  CREW SCHEDULE & TIME CLOCK
// ═══════════════════════════════════════════════════════════════

/**
 * Get crew schedule for a specific date.
 * Called with: ?action=getCrewSchedule&phone=4075551234&date=2026-03-06
 * Returns: { crew, members, tickets, timeEntries }
 */
function getCrewSchedule(phone, dateStr) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  // ─── Find crew leader by phone in Crew Members ───
  var cmSheet = ss.getSheetByName('Crew Members');
  if (!cmSheet) return { success: false, error: 'Crew Members sheet not found' };

  var cmData = cmSheet.getDataRange().getValues();
  var cmHeaders = cmData[0];
  var cmNameCol = findCol(cmHeaders, ['Name', 'name']);
  var cmPhoneCol = findCol(cmHeaders, ['Phone', 'phone']);
  var cmRoleCol = findCol(cmHeaders, ['Role', 'role']);
  var cmCrewCol = findCol(cmHeaders, ['Crew', 'crew']);
  var cmStatusCol = findCol(cmHeaders, ['Status', 'status']);

  var crewName = null;
  var leaderName = null;
  var cleanPhone = String(phone).replace(/\D/g, '');

  for (var i = 1; i < cmData.length; i++) {
    var memberPhone = String(cmData[i][cmPhoneCol]).replace(/\D/g, '');
    var role = cmRoleCol !== -1 ? String(cmData[i][cmRoleCol]) : '';
    if (memberPhone === cleanPhone && role.toLowerCase() === 'leader') {
      leaderName = cmData[i][cmNameCol];
      crewName = cmCrewCol !== -1 ? cmData[i][cmCrewCol] : '';
      break;
    }
  }

  if (!crewName) return { success: false, error: 'Crew leader not found for this phone' };

  // ─── Load all crew members ───
  var members = [];
  for (var m = 1; m < cmData.length; m++) {
    var mCrew = cmCrewCol !== -1 ? String(cmData[m][cmCrewCol]) : '';
    var mStatus = cmStatusCol !== -1 ? String(cmData[m][cmStatusCol]).toLowerCase() : 'active';
    if (mCrew === crewName && mStatus === 'active') {
      members.push({
        name: cmData[m][cmNameCol] || '',
        phone: cmPhoneCol !== -1 ? String(cmData[m][cmPhoneCol]) : '',
        role: cmRoleCol !== -1 ? cmData[m][cmRoleCol] : ''
      });
    }
  }

  // ─── Determine target date ───
  var targetDate = dateStr || new Date().toISOString().split('T')[0];
  // Normalize: if dateStr is an ISO timestamp, extract just the date
  if (targetDate.indexOf('T') !== -1) {
    targetDate = targetDate.split('T')[0];
  }

  // ─── Load tickets for this crew on this date ───
  var ticketSheet = ss.getSheetByName('Scheduled Tickets');
  var tickets = [];

  if (ticketSheet) {
    var tData = ticketSheet.getDataRange().getValues();
    var tHeaders = tData[0];
    var tColIdx = {
      ticketId: tHeaders.indexOf('Ticket ID'),
      contractId: tHeaders.indexOf('Contract ID'),
      propertyAddress: tHeaders.indexOf('Property Address'),
      assignedCrew: tHeaders.indexOf('Assigned Crew'),
      eventDate: tHeaders.indexOf('Event Date'),
      services: tHeaders.indexOf('Services JSON'),
      totalEstHours: tHeaders.indexOf('Total Est Hours'),
      travelHours: tHeaders.indexOf('Travel Hours'),
      earnedValue: tHeaders.indexOf('Earned Value'),
      internalCost: tHeaders.indexOf('Internal Cost'),
      status: tHeaders.indexOf('Status'),
      completedDate: tHeaders.indexOf('Completed Date'),
      notes: tHeaders.indexOf('Notes'),
      stopOrder: tHeaders.indexOf('Stop Order'),
      completedServices: tHeaders.indexOf('Completed Services')
    };

    var addedTicketIds = {};

    for (var t = 1; t < tData.length; t++) {
      var ticketCrew = String(tData[t][tColIdx.assignedCrew !== -1 ? tColIdx.assignedCrew : 3] || '');
      var rawDate = tData[t][tColIdx.eventDate !== -1 ? tColIdx.eventDate : 4];
      var ticketDate = '';

      // Handle Date objects from Google Sheets
      if (rawDate instanceof Date) {
        ticketDate = rawDate.getFullYear() + '-' +
          String(rawDate.getMonth() + 1).padStart(2, '0') + '-' +
          String(rawDate.getDate()).padStart(2, '0');
      } else {
        ticketDate = String(rawDate || '');
        // Normalize if ISO timestamp
        if (ticketDate.indexOf('T') !== -1) {
          ticketDate = ticketDate.split('T')[0];
        }
      }

      // Validate status value
      var rawStatus = tColIdx.status !== -1 ? tData[t][tColIdx.status] : '';
      var validStatus = 'scheduled';
      if (rawStatus) {
        var s = String(rawStatus).toLowerCase().trim();
        if (s === 'scheduled' || s === 'completed' || s === 'skipped' || s === 'rescheduled' || s === 'partial') {
          validStatus = s;
        }
      }

      // Include: today's tickets for this crew, OR partial tickets from any date for this crew
      var isToday = (ticketCrew === crewName && ticketDate === targetDate);
      var isPartialCarryover = (ticketCrew === crewName && validStatus === 'partial');

      if (isToday || isPartialCarryover) {
        var tid = tColIdx.ticketId !== -1 ? (tData[t][tColIdx.ticketId] || '') : '';
        if (addedTicketIds[tid]) continue; // avoid duplicates
        addedTicketIds[tid] = true;

        var services = tColIdx.services !== -1 ? (tData[t][tColIdx.services] || '[]') : '[]';
        if (typeof services === 'string') {
          try { services = JSON.parse(services); } catch(e) { services = []; }
        }

        // Parse completedServices JSON
        var completedServices = [];
        if (tColIdx.completedServices !== -1) {
          var csRaw = tData[t][tColIdx.completedServices] || '';
          if (csRaw && typeof csRaw === 'string') {
            try { completedServices = JSON.parse(csRaw); } catch(e) { completedServices = []; }
          }
        }

        tickets.push({
          ticketId: tid,
          contractId: tColIdx.contractId !== -1 ? (tData[t][tColIdx.contractId] || '') : '',
          propertyAddress: tColIdx.propertyAddress !== -1 ? (tData[t][tColIdx.propertyAddress] || '') : '',
          assignedCrew: ticketCrew,
          eventDate: isPartialCarryover && !isToday ? ticketDate : targetDate,
          services: services,
          totalEstHours: tColIdx.totalEstHours !== -1 ? (tData[t][tColIdx.totalEstHours] || 0) : 0,
          travelHours: tColIdx.travelHours !== -1 ? (parseFloat(tData[t][tColIdx.travelHours]) || 0) : 0,
          earnedValue: tColIdx.earnedValue !== -1 ? (parseFloat(tData[t][tColIdx.earnedValue]) || 0) : 0,
          internalCost: tColIdx.internalCost !== -1 ? (parseFloat(tData[t][tColIdx.internalCost]) || 0) : 0,
          status: validStatus,
          completedDate: tColIdx.completedDate !== -1 ? (tData[t][tColIdx.completedDate] || '') : '',
          completedServices: completedServices,
          notes: tColIdx.notes !== -1 ? (tData[t][tColIdx.notes] || '') : '',
          stopOrder: tColIdx.stopOrder !== -1 ? tData[t][tColIdx.stopOrder] : null
        });
      }
    }

    // Sort: partial tickets first, then by stopOrder (nulls last)
    tickets.sort(function(a, b) {
      var aPartial = a.status === 'partial' ? 0 : 1;
      var bPartial = b.status === 'partial' ? 0 : 1;
      if (aPartial !== bPartial) return aPartial - bPartial;
      var orderA = a.stopOrder !== undefined && a.stopOrder !== null && a.stopOrder !== '' ? parseInt(a.stopOrder) : 999;
      var orderB = b.stopOrder !== undefined && b.stopOrder !== null && b.stopOrder !== '' ? parseInt(b.stopOrder) : 999;
      return orderA - orderB;
    });
  }

  // ─── Load time entries for this crew on this date ───
  var teSheet = ss.getSheetByName('Time Entries');
  var timeEntries = [];

  if (teSheet) {
    var teData = teSheet.getDataRange().getValues();
    var teHeaders = teData[0];

    for (var te = 1; te < teData.length; te++) {
      var row = teData[te];
      var teCrew = String(row[findCol(teHeaders, ['Crew', 'crew'])] || '');
      var teDate = String(row[findCol(teHeaders, ['Date', 'date'])] || '');

      if (teDate.indexOf('T') !== -1) teDate = teDate.split('T')[0];

      if (teCrew === crewName && teDate === targetDate) {
        var entry = {};
        teHeaders.forEach(function(h, idx) {
          entry[h] = row[idx];
        });
        timeEntries.push(entry);
      }
    }
  }

  return {
    success: true,
    crewName: crewName,
    leaderName: leaderName,
    members: members,
    date: targetDate,
    tickets: tickets,
    timeEntries: timeEntries
  };
}

/**
 * Get crew members for daily check-in.
 * Called with: ?action=getCrewMembers&phone=4075551234
 */
function getCrewMembers(phone) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var cmSheet = ss.getSheetByName('Crew Members');
  if (!cmSheet) return { success: false, error: 'Crew Members sheet not found' };

  var cmData = cmSheet.getDataRange().getValues();
  var cmHeaders = cmData[0];
  var cmNameCol = findCol(cmHeaders, ['Name', 'name']);
  var cmPhoneCol = findCol(cmHeaders, ['Phone', 'phone']);
  var cmRoleCol = findCol(cmHeaders, ['Role', 'role']);
  var cmCrewCol = findCol(cmHeaders, ['Crew', 'crew']);
  var cmStatusCol = findCol(cmHeaders, ['Status', 'status']);

  var crewName = null;
  var cleanPhone = String(phone).replace(/\D/g, '');

  for (var i = 1; i < cmData.length; i++) {
    var memberPhone = String(cmData[i][cmPhoneCol]).replace(/\D/g, '');
    var role = cmRoleCol !== -1 ? String(cmData[i][cmRoleCol]) : '';
    if (memberPhone === cleanPhone && role.toLowerCase() === 'leader') {
      crewName = cmCrewCol !== -1 ? cmData[i][cmCrewCol] : '';
      break;
    }
  }

  if (!crewName) return { success: false, error: 'Crew not found' };

  var members = [];
  for (var m = 1; m < cmData.length; m++) {
    var mCrew = cmCrewCol !== -1 ? String(cmData[m][cmCrewCol]) : '';
    var mStatus = cmStatusCol !== -1 ? String(cmData[m][cmStatusCol]).toLowerCase() : 'active';
    if (mCrew === crewName && mStatus === 'active') {
      members.push({
        name: cmData[m][cmNameCol] || '',
        role: cmRoleCol !== -1 ? cmData[m][cmRoleCol] : ''
      });
    }
  }

  return { success: true, crewName: crewName, members: members };
}

/**
 * Verify a 4-digit PIN against the Crew Members sheet.
 * Called with: ?action=verifyPin&pin=1234
 * Returns: { success, name, role, crew, pin }
 */
function verifyPin(pin) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Crew Members');
  if (!sheet) {
    return ContentService.createTextOutput(JSON.stringify({
      success: false, error: 'Crew Members sheet not found'
    })).setMimeType(ContentService.MimeType.JSON);
  }

  var rows = sheet.getDataRange().getValues();
  var headers = rows[0];

  var pinCol = findCol(headers, ['pin', 'Pin', 'PIN']);
  var nameCol = findCol(headers, ['name', 'Name']);
  var roleCol = findCol(headers, ['role', 'Role']);
  var crewCol = findCol(headers, ['crew', 'Crew']);
  var statusCol = findCol(headers, ['status', 'Status']);

  if (pinCol === -1) {
    return ContentService.createTextOutput(JSON.stringify({
      success: false, error: 'PIN column not found in Crew Members sheet'
    })).setMimeType(ContentService.MimeType.JSON);
  }

  for (var i = 1; i < rows.length; i++) {
    var memberStatus = statusCol !== -1 ? String(rows[i][statusCol]).toLowerCase() : 'active';
    if (String(rows[i][pinCol]) === String(pin) && memberStatus === 'active') {
      return ContentService.createTextOutput(JSON.stringify({
        success: true,
        name: nameCol !== -1 ? rows[i][nameCol] : '',
        role: roleCol !== -1 ? rows[i][roleCol] : '',
        crew: crewCol !== -1 ? rows[i][crewCol] : '',
        pin: pin
      })).setMimeType(ContentService.MimeType.JSON);
    }
  }

  return ContentService.createTextOutput(JSON.stringify({
    success: false,
    error: 'Invalid PIN'
  })).setMimeType(ContentService.MimeType.JSON);
}

/**
 * Get all unique active crews for dropdown population.
 * Called with: ?action=getCrews
 */
function getCrews() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Crew Members');

  if (!sheet) {
    // Fallback: try Contracts sheet for unique crew names
    var contractSheet = ss.getSheetByName('Contracts');
    if (!contractSheet) return { success: true, crews: [], crewSizes: {} };
    var contractData = contractSheet.getDataRange().getValues();
    var crewCol = contractData[0].indexOf('Assigned Crew');
    if (crewCol === -1) return { success: true, crews: [], crewSizes: {} };
    var crewSet = {};
    for (var i = 1; i < contractData.length; i++) {
      var c = String(contractData[i][crewCol] || '').trim();
      if (c) crewSet[c] = 1;
    }
    return { success: true, crews: Object.keys(crewSet).sort(), crewSizes: crewSet };
  }

  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var nameCol = headers.indexOf('Crew');
  if (nameCol === -1) nameCol = headers.indexOf('crew');
  var statusCol = headers.indexOf('Status');
  if (statusCol === -1) statusCol = headers.indexOf('status');

  var crewCounts = {};
  for (var i = 1; i < data.length; i++) {
    var crewName = String(data[i][nameCol] || '').trim();
    if (!crewName) continue;
    var status = statusCol !== -1 ? String(data[i][statusCol] || '').toLowerCase() : 'active';
    if (status !== 'active' && status !== '') continue;
    if (!crewCounts[crewName]) crewCounts[crewName] = 0;
    crewCounts[crewName]++;
  }

  return {
    success: true,
    crews: Object.keys(crewCounts).sort(),
    crewSizes: crewCounts
  };
}

/**
 * Save a time entry (day clock, job clock, or indirect).
 * POST: { saveTimeEntry: true, crew, date, entryType, ticketId, propertyAddress,
 *          indirectCategory, clockIn, clockOut, durationMinutes, crewMembers, notes }
 */
function saveTimeEntry(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Time Entries');

  if (!sheet) {
    sheet = ss.insertSheet('Time Entries');
    sheet.getRange(1, 1, 1, 17).setValues([[
      'Entry ID', 'Crew', 'Date', 'Entry Type', 'Ticket ID', 'Property Address',
      'Indirect Category', 'Clock In', 'Clock Out', 'Duration Minutes',
      'Crew Members', 'Notes', 'Created Date', 'Lat In', 'Lng In', 'Lat Out', 'Lng Out'
    ]]);
    sheet.getRange(1, 1, 1, 17).setFontWeight('bold');
  } else {
    // Auto-upgrade existing sheets to include GPS columns
    var headerRow = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    if (headerRow.indexOf('Lat In') === -1) {
      var nextCol = sheet.getLastColumn() + 1;
      sheet.getRange(1, nextCol, 1, 4).setValues([['Lat In', 'Lng In', 'Lat Out', 'Lng Out']]);
      sheet.getRange(1, nextCol, 1, 4).setFontWeight('bold');
    }
    // Auto-upgrade: add Service Name and Member Count columns if missing
    headerRow = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    if (headerRow.indexOf('Service Name') === -1) {
      var nextCol2 = sheet.getLastColumn() + 1;
      sheet.getRange(1, nextCol2, 1, 2).setValues([['Service Name', 'Member Count']]);
      sheet.getRange(1, nextCol2, 1, 2).setFontWeight('bold');
    }
    // Auto-upgrade: add Duration Type column if missing
    headerRow = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    if (headerRow.indexOf('Duration Type') === -1) {
      var nextCol3 = sheet.getLastColumn() + 1;
      sheet.getRange(1, nextCol3).setValue('Duration Type');
      sheet.getRange(1, nextCol3).setFontWeight('bold');
    }
    // Auto-upgrade: add Reopened column if missing
    headerRow = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    if (headerRow.indexOf('Reopened') === -1) {
      var nextCol4 = sheet.getLastColumn() + 1;
      sheet.getRange(1, nextCol4).setValue('Reopened');
      sheet.getRange(1, nextCol4).setFontWeight('bold');
    }
    // Auto-upgrade: add Estimated Hours column if missing
    headerRow = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    if (headerRow.indexOf('Estimated Hours') === -1) {
      var nextCol5 = sheet.getLastColumn() + 1;
      sheet.getRange(1, nextCol5).setValue('Estimated Hours');
      sheet.getRange(1, nextCol5).setFontWeight('bold');
    }
  }

  // Re-read headers after potential upgrade
  var currentHeaders = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var serviceNameCol = currentHeaders.indexOf('Service Name');
  var memberCountCol = currentHeaders.indexOf('Member Count');
  var durationTypeCol = currentHeaders.indexOf('Duration Type');
  var reopenedCol = currentHeaders.indexOf('Reopened');
  var estimatedHoursCol = currentHeaders.indexOf('Estimated Hours');

  // Generate entry ID
  var existingData = sheet.getDataRange().getValues();
  var maxId = 0;
  for (var i = 1; i < existingData.length; i++) {
    var existingId = existingData[i][0];
    if (existingId && typeof existingId === 'string' && existingId.indexOf('TE-') === 0) {
      var num = parseInt(existingId.replace('TE-', ''), 10);
      if (num > maxId) maxId = num;
    }
  }
  var entryId = 'TE-' + String(maxId + 1).padStart(4, '0');

  var now = new Date();
  var createdDate = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  // Build row with correct number of columns
  var baseRow = [
    entryId,
    data.crew || '',
    data.date || now.toISOString().split('T')[0],
    data.entryType || '',           // day_clock, job, indirect, service
    data.ticketId || '',
    data.propertyAddress || '',
    data.indirectCategory || '',    // travel, shop, dump_run, fuel, break, meeting, equipment, other
    data.clockIn || '',
    data.clockOut || '',
    data.durationMinutes || 0,
    typeof data.crewMembers === 'string' ? data.crewMembers : JSON.stringify(data.crewMembers || []),
    data.notes || '',
    createdDate,
    data.latIn || '',
    data.lngIn || '',
    data.latOut || '',
    data.lngOut || ''
  ];

  // Pad row to match header count and set serviceName/memberCount
  while (baseRow.length < currentHeaders.length) {
    baseRow.push('');
  }
  if (serviceNameCol !== -1) baseRow[serviceNameCol] = data.serviceName || '';
  if (memberCountCol !== -1) baseRow[memberCountCol] = data.memberCount || '';
  if (durationTypeCol !== -1) baseRow[durationTypeCol] = data.durationType || '';
  if (reopenedCol !== -1) baseRow[reopenedCol] = data.reopened ? 'true' : '';
  if (estimatedHoursCol !== -1) baseRow[estimatedHoursCol] = data.estimatedHours || '';

  sheet.appendRow(baseRow);

  return { success: true, entryId: entryId };
}

/**
 * Complete a job — update ticket status and save time entry in one call.
 * POST: { completeJob: true, ticketId, crew, date, clockIn, clockOut,
 *          durationMinutes, crewMembers, servicesCompleted, notes, photoUrl }
 */
function completeJob(data) {
  var isPartial = data.partial === true;

  // Update ticket status + completedServices
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Scheduled Tickets');
  if (sheet) {
    var sheetData = sheet.getDataRange().getValues();
    var headers = sheetData[0];
    var ticketIdCol = headers.indexOf('Ticket ID');
    var statusCol = headers.indexOf('Status');
    var completedDateCol = headers.indexOf('Completed Date');
    var notesCol = headers.indexOf('Notes');

    // Auto-upgrade: add Completed Services column if missing
    var completedServicesCol = headers.indexOf('Completed Services');
    if (completedServicesCol === -1) {
      var nextCol = sheet.getLastColumn() + 1;
      sheet.getRange(1, nextCol).setValue('Completed Services');
      sheet.getRange(1, nextCol).setFontWeight('bold');
      completedServicesCol = nextCol - 1;
    }

    if (ticketIdCol === -1) ticketIdCol = 0;

    for (var i = 1; i < sheetData.length; i++) {
      if (sheetData[i][ticketIdCol] === data.ticketId) {
        if (statusCol !== -1) {
          sheet.getRange(i + 1, statusCol + 1).setValue(isPartial ? 'partial' : 'completed');
        }
        if (!isPartial && completedDateCol !== -1) {
          sheet.getRange(i + 1, completedDateCol + 1).setValue(data.date || new Date().toISOString().split('T')[0]);
        }
        if (data.notes && notesCol !== -1) {
          sheet.getRange(i + 1, notesCol + 1).setValue(data.notes);
        }
        if (data.completedServices && completedServicesCol !== -1) {
          sheet.getRange(i + 1, completedServicesCol + 1).setValue(JSON.stringify(data.completedServices));
        }
        break;
      }
    }
  }

  // Update existing open time entry (don't create a new one)
  var entryResult = updateTimeEntry({
    crew: data.crew,
    date: data.date,
    entryType: 'job',
    ticketId: data.ticketId,
    clockOut: data.clockOut,
    durationMinutes: data.durationMinutes,
    notes: data.notes,
    latOut: data.latOut,
    lngOut: data.lngOut
  });

  return { success: true, entryId: entryResult.entryId || '' };
}

/**
 * Update an existing time entry (clock out, duration, notes).
 */
function updateTimeEntry(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Time Entries');
  if (!sheet) return { success: false, error: 'Time Entries sheet not found' };

  var sheetData = sheet.getDataRange().getValues();
  var headers = sheetData[0];

  // Find by entry ID
  if (data.entryId) {
    var idCol = headers.indexOf('Entry ID');
    if (idCol === -1) return { success: false, error: 'Entry ID column not found' };

    for (var i = 1; i < sheetData.length; i++) {
      if (String(sheetData[i][idCol]) === String(data.entryId)) {
        // Update Clock Out
        var clockOutCol = headers.indexOf('Clock Out');
        if (clockOutCol !== -1 && data.clockOut !== undefined) {
          sheet.getRange(i + 1, clockOutCol + 1).setValue(data.clockOut);
        }
        // Update Duration
        var durationCol = headers.indexOf('Duration Minutes');
        if (durationCol !== -1 && data.durationMinutes !== undefined) {
          sheet.getRange(i + 1, durationCol + 1).setValue(data.durationMinutes);
        }
        // Update Notes
        var notesCol = headers.indexOf('Notes');
        if (notesCol !== -1 && data.notes !== undefined) {
          sheet.getRange(i + 1, notesCol + 1).setValue(data.notes);
        }
        // Update Indirect Category
        var indirectCol = headers.indexOf('Indirect Category');
        if (indirectCol !== -1 && data.indirectCategory !== undefined) {
          sheet.getRange(i + 1, indirectCol + 1).setValue(data.indirectCategory);
        }
        // Update GPS coordinates
        var latInCol = headers.indexOf('Lat In');
        if (latInCol !== -1 && data.latIn !== undefined) {
          sheet.getRange(i + 1, latInCol + 1).setValue(data.latIn);
        }
        var lngInCol = headers.indexOf('Lng In');
        if (lngInCol !== -1 && data.lngIn !== undefined) {
          sheet.getRange(i + 1, lngInCol + 1).setValue(data.lngIn);
        }
        var latOutCol = headers.indexOf('Lat Out');
        if (latOutCol !== -1 && data.latOut !== undefined) {
          sheet.getRange(i + 1, latOutCol + 1).setValue(data.latOut);
        }
        var lngOutCol = headers.indexOf('Lng Out');
        if (lngOutCol !== -1 && data.lngOut !== undefined) {
          sheet.getRange(i + 1, lngOutCol + 1).setValue(data.lngOut);
        }
        // Update Crew Members
        var crewMembersCol = headers.indexOf('Crew Members');
        if (crewMembersCol !== -1 && data.crewMembers !== undefined) {
          var membersVal = typeof data.crewMembers === 'string' ? data.crewMembers : JSON.stringify(data.crewMembers || []);
          sheet.getRange(i + 1, crewMembersCol + 1).setValue(membersVal);
        }
        // Update Member Count
        var memberCountCol = headers.indexOf('Member Count');
        if (memberCountCol !== -1 && data.memberCount !== undefined) {
          sheet.getRange(i + 1, memberCountCol + 1).setValue(data.memberCount);
        }
        return { success: true };
      }
    }
    return { success: false, error: 'Entry not found: ' + data.entryId };
  }

  // Find by crew + date + entryType + no clockOut (find the open entry)
  var crewCol = headers.indexOf('Crew');
  var dateCol = headers.indexOf('Date');
  var typeCol = headers.indexOf('Entry Type');
  var clockOutCol = headers.indexOf('Clock Out');
  var ticketCol = headers.indexOf('Ticket ID');
  var serviceNameCol = headers.indexOf('Service Name');

  for (var j = sheetData.length - 1; j >= 1; j--) {
    var row = sheetData[j];
    var matchesCrew = String(row[crewCol]) === String(data.crew);
    var matchesDate = String(row[dateCol]).indexOf(data.date) !== -1 || String(data.date).indexOf(String(row[dateCol])) !== -1;
    var matchesType = String(row[typeCol]) === String(data.entryType);
    var isOpen = !row[clockOutCol] || String(row[clockOutCol]).trim() === '';
    var matchesTicket = !data.ticketId || String(row[ticketCol]) === String(data.ticketId);
    // For service entries, also match on serviceName
    var matchesService = true;
    if (data.entryType === 'service' && data.serviceName && serviceNameCol !== -1) {
      matchesService = String(row[serviceNameCol]) === String(data.serviceName);
    }

    if (matchesCrew && matchesDate && matchesType && isOpen && matchesTicket && matchesService) {
      if (data.clockOut) {
        sheet.getRange(j + 1, clockOutCol + 1).setValue(data.clockOut);
      }
      var durationCol2 = headers.indexOf('Duration Minutes');
      if (durationCol2 !== -1 && data.durationMinutes !== undefined) {
        sheet.getRange(j + 1, durationCol2 + 1).setValue(data.durationMinutes);
      }
      var notesCol2 = headers.indexOf('Notes');
      if (notesCol2 !== -1 && data.notes !== undefined) {
        sheet.getRange(j + 1, notesCol2 + 1).setValue(data.notes);
      }
      // Update Indirect Category
      var indirectCol2 = headers.indexOf('Indirect Category');
      if (indirectCol2 !== -1 && data.indirectCategory !== undefined) {
        sheet.getRange(j + 1, indirectCol2 + 1).setValue(data.indirectCategory);
      }
      // Update GPS coordinates
      var latInCol2 = headers.indexOf('Lat In');
      if (latInCol2 !== -1 && data.latIn !== undefined) {
        sheet.getRange(j + 1, latInCol2 + 1).setValue(data.latIn);
      }
      var lngInCol2 = headers.indexOf('Lng In');
      if (lngInCol2 !== -1 && data.lngIn !== undefined) {
        sheet.getRange(j + 1, lngInCol2 + 1).setValue(data.lngIn);
      }
      var latOutCol2 = headers.indexOf('Lat Out');
      if (latOutCol2 !== -1 && data.latOut !== undefined) {
        sheet.getRange(j + 1, latOutCol2 + 1).setValue(data.latOut);
      }
      var lngOutCol2 = headers.indexOf('Lng Out');
      if (lngOutCol2 !== -1 && data.lngOut !== undefined) {
        sheet.getRange(j + 1, lngOutCol2 + 1).setValue(data.lngOut);
      }
      // Update Crew Members
      var crewMembersCol2 = headers.indexOf('Crew Members');
      if (crewMembersCol2 !== -1 && data.crewMembers !== undefined) {
        var membersVal2 = typeof data.crewMembers === 'string' ? data.crewMembers : JSON.stringify(data.crewMembers || []);
        sheet.getRange(j + 1, crewMembersCol2 + 1).setValue(membersVal2);
      }
      // Update Member Count
      var memberCountCol2 = headers.indexOf('Member Count');
      if (memberCountCol2 !== -1 && data.memberCount !== undefined) {
        sheet.getRange(j + 1, memberCountCol2 + 1).setValue(data.memberCount);
      }
      return { success: true, entryId: row[headers.indexOf('Entry ID')] };
    }
  }

  return { success: false, error: 'Open entry not found' };
}

/**
 * POST: { deleteTimeEntry: true, entryId: 'TE-0001' }
 * Deletes a time entry row by Entry ID.
 */
function deleteTimeEntry(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Time Entries');
  if (!sheet) return { success: false, error: 'Time Entries sheet not found' };

  var rows = sheet.getDataRange().getValues();
  var headers = rows[0];
  var idCol = headers.indexOf('Entry ID');
  if (idCol === -1) return { success: false, error: 'Entry ID column not found' };

  for (var i = 1; i < rows.length; i++) {
    if (String(rows[i][idCol]) === String(data.entryId)) {
      sheet.deleteRow(i + 1);
      return { success: true };
    }
  }
  return { success: false, error: 'Entry not found: ' + data.entryId };
}


// ═══════════════════════════════════════════════════════════════
//  HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════

function findCol(headers, aliases) {
  for (var a = 0; a < aliases.length; a++) {
    var idx = headers.indexOf(aliases[a]);
    if (idx !== -1) return idx;
  }
  return -1;
}

function getPropertyFolder(propertyAddress, subfolder) {
  var mainFolder = DriveApp.getFolderById(TEXT_MY_TEAM_DRIVE_FOLDER_ID);

  var streetAddress = (propertyAddress || 'Unknown').split(',')[0].trim();

  var propFolders = mainFolder.getFoldersByName(streetAddress);
  var propFolder;
  if (propFolders.hasNext()) {
    propFolder = propFolders.next();
  } else {
    propFolder = mainFolder.createFolder(streetAddress);
  }

  if (subfolder) {
    var subFolders = propFolder.getFoldersByName(subfolder);
    if (subFolders.hasNext()) {
      return subFolders.next();
    } else {
      return propFolder.createFolder(subfolder);
    }
  }

  return propFolder;
}

function formatDateNice(dateStr) {
  if (!dateStr) return '';
  var d = new Date(dateStr + 'T00:00:00');
  var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  return days[d.getDay()] + ' ' + months[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear();
}


// ═══════════════════════════════════════════════════════════════
//  ROUTE ORDERING
// ═══════════════════════════════════════════════════════════════

/**
 * Get route order for a crew on a specific day of week.
 * Called with: ?action=getRouteOrder&crew=MNT%20Crew%201&dayOfWeek=0
 * dayOfWeek: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
 */
function getRouteOrder(crew, dayOfWeek) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ticketSheet = ss.getSheetByName('Scheduled Tickets');
  if (!ticketSheet) return { success: true, stops: [] };

  var dow = parseInt(dayOfWeek); // 0=Mon..6=Sun
  // Convert to JS getDay() where 0=Sun
  var jsDay = dow === 6 ? 0 : dow + 1;

  var data = ticketSheet.getDataRange().getValues();
  var headers = data[0];
  var crewCol = headers.indexOf('Assigned Crew');
  var addressCol = headers.indexOf('Property Address');
  var dateCol = headers.indexOf('Event Date');
  var statusCol = headers.indexOf('Status');
  var orderCol = headers.indexOf('Stop Order');

  // If Stop Order column doesn't exist, create it
  if (orderCol === -1) {
    ticketSheet.getRange(1, headers.length + 1).setValue('Stop Order');
    orderCol = headers.length;
  }

  var propertyMap = {}; // address → stopOrder

  for (var i = 1; i < data.length; i++) {
    var rowCrew = String(data[i][crewCol] || '').trim();
    var rowStatus = String(data[i][statusCol] || '').trim().toLowerCase();
    if (rowCrew !== crew) continue;
    if (rowStatus === 'completed' || rowStatus === 'skipped') continue;

    // Check if this ticket's date falls on the requested day of week
    var eventDate = data[i][dateCol];
    if (eventDate) {
      var d = eventDate instanceof Date ? eventDate : new Date(eventDate);
      if (d.getDay() !== jsDay) continue;
    }

    var address = String(data[i][addressCol] || '').trim();
    if (!address) continue;

    // Take the first non-empty stopOrder found for this property
    if (!propertyMap[address]) {
      var order = data[i][orderCol];
      propertyMap[address] = order ? parseInt(order) : null;
    }
  }

  var stops = Object.keys(propertyMap).map(function(addr) {
    return { propertyAddress: addr, stopOrder: propertyMap[addr] };
  });

  // Sort: by stopOrder (nulls last), then alphabetically
  stops.sort(function(a, b) {
    if (a.stopOrder === null && b.stopOrder === null) return a.propertyAddress.localeCompare(b.propertyAddress);
    if (a.stopOrder === null) return 1;
    if (b.stopOrder === null) return -1;
    return a.stopOrder - b.stopOrder;
  });

  return { success: true, stops: stops };
}

/**
 * Save route order for a crew.
 * POST: { saveRouteOrder: true, crew: "MNT Crew 1", stops: [{propertyAddress, stopOrder}] }
 */
function saveRouteOrder(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Scheduled Tickets');
  if (!sheet) return { success: false, error: 'Sheet not found' };

  var sheetData = sheet.getDataRange().getValues();
  var headers = sheetData[0];
  var crewCol = headers.indexOf('Assigned Crew');
  var addressCol = headers.indexOf('Property Address');
  var orderCol = headers.indexOf('Stop Order');

  if (orderCol === -1) {
    sheet.getRange(1, headers.length + 1).setValue('Stop Order');
    orderCol = headers.length;
    // Re-read data since we added a column
    sheetData = sheet.getDataRange().getValues();
  }

  // Build a lookup: address → stopOrder
  var orderMap = {};
  data.stops.forEach(function(stop) {
    orderMap[stop.propertyAddress] = stop.stopOrder;
  });

  // Update all tickets for this crew
  for (var i = 1; i < sheetData.length; i++) {
    var rowCrew = String(sheetData[i][crewCol] || '').trim();
    var rowAddress = String(sheetData[i][addressCol] || '').trim();
    if (rowCrew === data.crew && orderMap[rowAddress] !== undefined) {
      sheet.getRange(i + 1, orderCol + 1).setValue(orderMap[rowAddress]);
    }
  }

  return { success: true };
}


// ═══════════════════════════════════════════════════════════════
//  WEEKLY PROPERTY REPORTS
// ═══════════════════════════════════════════════════════════════

/**
 * Get weekly report data for all properties with completed work.
 * Called with: ?action=getWeeklyReportData&weekOf=2026-02-10
 */
function getWeeklyReportData(weekOf) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ticketSheet = ss.getSheetByName('Scheduled Tickets');
  var propSheet = ss.getSheetByName('Properties');

  if (!ticketSheet) return { success: true, reports: [] };

  // Determine week range (Mon–Sun)
  var monday;
  if (weekOf) {
    monday = new Date(weekOf + 'T00:00:00');
  } else {
    // Most recent Monday
    monday = new Date();
    var dow = monday.getDay(); // 0=Sun
    var diff = dow === 0 ? 6 : dow - 1;
    monday.setDate(monday.getDate() - diff);
  }
  monday.setHours(0, 0, 0, 0);

  var sunday = new Date(monday);
  sunday.setDate(sunday.getDate() + 6);

  var mondayStr = monday.toISOString().split('T')[0];
  var sundayStr = sunday.toISOString().split('T')[0];

  // Read tickets
  var tData = ticketSheet.getDataRange().getValues();
  var tHeaders = tData[0];
  var tDateCol = tHeaders.indexOf('Event Date');
  var tAddrCol = tHeaders.indexOf('Property Address');
  var tStatusCol = tHeaders.indexOf('Status');
  var tServicesCol = tHeaders.indexOf('Services JSON');
  var tNotesCol = tHeaders.indexOf('Notes');
  var tCrewCol = tHeaders.indexOf('Assigned Crew');
  var tCompletedCol = tHeaders.indexOf('Completed Date');

  // Read properties for email addresses
  var pData = propSheet ? propSheet.getDataRange().getValues() : [];
  var pHeaders = pData.length > 0 ? pData[0] : [];
  var pAddrCol = findCol(pHeaders, ['Address', 'Property Address']);
  var pEmailCol = findCol(pHeaders, ['Email', 'email']);
  var pNameCol = findCol(pHeaders, ['Customer Name', 'Name', 'name']);

  var emailMap = {};
  var nameMap = {};
  for (var p = 1; p < pData.length; p++) {
    var addr = pAddrCol !== -1 ? String(pData[p][pAddrCol] || '').trim() : '';
    if (addr) {
      emailMap[addr] = pEmailCol !== -1 ? String(pData[p][pEmailCol] || '').trim() : '';
      nameMap[addr] = pNameCol !== -1 ? String(pData[p][pNameCol] || '').trim() : '';
    }
  }

  // Group completed tickets by property for this week
  var propertyVisits = {}; // address → [{ date, services, notes, crew }]

  for (var t = 1; t < tData.length; t++) {
    var status = String(tData[t][tStatusCol] || '').toLowerCase();
    if (status !== 'completed') continue;

    var eventDate = tData[t][tDateCol];
    var dateStr;
    if (eventDate instanceof Date) {
      dateStr = eventDate.toISOString().split('T')[0];
    } else {
      dateStr = String(eventDate || '').split('T')[0];
    }

    if (dateStr < mondayStr || dateStr > sundayStr) continue;

    var address = String(tData[t][tAddrCol] || '').trim();
    if (!address) continue;

    var services = tData[t][tServicesCol] || '[]';
    if (typeof services === 'string') {
      try { services = JSON.parse(services); } catch(e) { services = []; }
    }

    var notes = String(tData[t][tNotesCol] || '').trim();
    var crew = String(tData[t][tCrewCol] || '').trim();

    if (!propertyVisits[address]) propertyVisits[address] = [];
    propertyVisits[address].push({
      date: dateStr,
      services: services,
      notes: notes,
      crew: crew
    });
  }

  // Build report objects
  var reports = Object.keys(propertyVisits).map(function(addr) {
    return {
      propertyAddress: addr,
      customerName: nameMap[addr] || '',
      customerEmail: emailMap[addr] || '',
      weekStart: mondayStr,
      weekEnd: sundayStr,
      visits: propertyVisits[addr].sort(function(a, b) { return a.date.localeCompare(b.date); })
    };
  });

  reports.sort(function(a, b) { return a.propertyAddress.localeCompare(b.propertyAddress); });

  return { success: true, reports: reports, weekStart: mondayStr, weekEnd: sundayStr };
}

/**
 * Send weekly report email to a property owner.
 * POST: { sendWeeklyReport: true, propertyAddress, customerEmail, customerName, weekStart, weekEnd, visits }
 */
function sendWeeklyReport(data) {
  var email = data.customerEmail;
  if (!email) return { success: false, error: 'No email address for this property' };

  var companyName = data.companyName || 'Endurance Services';
  var weekLabel = formatDateNice(data.weekStart) + ' – ' + formatDateNice(data.weekEnd);

  // Build HTML for the report
  var html = '<html><head><style>';
  html += 'body { font-family: Arial, sans-serif; font-size: 14px; color: #333; padding: 40px; }';
  html += '.header { border-bottom: 2px solid #2e7d32; padding-bottom: 12px; margin-bottom: 20px; }';
  html += '.header h1 { color: #2e7d32; font-size: 22px; margin: 0; }';
  html += '.header p { color: #666; margin: 4px 0 0 0; font-size: 13px; }';
  html += '.property { font-size: 16px; font-weight: 600; margin-bottom: 4px; }';
  html += '.week { color: #666; font-size: 13px; margin-bottom: 20px; }';
  html += '.visit { border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px; margin-bottom: 10px; }';
  html += '.visit-date { font-weight: 600; font-size: 14px; margin-bottom: 6px; }';
  html += '.visit-services { color: #555; font-size: 13px; }';
  html += '.visit-notes { color: #888; font-size: 12px; font-style: italic; margin-top: 6px; }';
  html += '.footer { margin-top: 30px; padding-top: 12px; border-top: 1px solid #e0e0e0; color: #999; font-size: 11px; }';
  html += '</style></head><body>';

  html += '<div class="header"><h1>' + companyName + '</h1>';
  html += '<p>Weekly Service Report</p></div>';

  html += '<div class="property">' + data.propertyAddress + '</div>';
  if (data.customerName) html += '<div style="color:#666;font-size:13px;margin-bottom:4px;">' + data.customerName + '</div>';
  html += '<div class="week">Week of ' + weekLabel + '</div>';

  data.visits.forEach(function(visit) {
    html += '<div class="visit">';
    html += '<div class="visit-date">' + formatDateNice(visit.date) + '</div>';

    // List services
    var serviceNames = [];
    if (visit.services && visit.services.length > 0) {
      visit.services.forEach(function(svc) {
        var name = typeof svc === 'string' ? svc : (svc.name || svc.serviceName || svc.proposalName || svc.sectionName || 'Service');
        serviceNames.push(name);
      });
    }
    html += '<div class="visit-services">Services completed: ' + (serviceNames.length > 0 ? serviceNames.join(', ') : 'N/A') + '</div>';

    if (visit.notes) {
      html += '<div class="visit-notes">Notes: ' + visit.notes + '</div>';
    }
    html += '</div>';
  });

  html += '<div class="footer">This report was automatically generated by ' + companyName + '. If you have any questions about the work performed, please contact us.</div>';
  html += '</body></html>';

  // Create PDF from HTML
  var blob = HtmlService.createHtmlOutput(html).getBlob().setName(
    'Service Report - ' + data.propertyAddress + ' - ' + data.weekStart + '.pdf'
  ).getAs('application/pdf');

  // Send email
  var subject = companyName + ' — Weekly Service Report (' + weekLabel + ')';
  var emailBody = 'Hello' + (data.customerName ? ' ' + data.customerName : '') + ',\n\n';
  emailBody += 'Please find attached your weekly service report for ' + data.propertyAddress + '.\n\n';
  emailBody += 'Week of ' + weekLabel + '\n\n';
  emailBody += 'Thank you for choosing ' + companyName + '!\n';

  MailApp.sendEmail({
    to: email,
    subject: subject,
    body: emailBody,
    attachments: [blob]
  });

  return { success: true, message: 'Report sent to ' + email };
}

// ═══════════════════════════════════════════════════════════════
//  CONTACTS (Lite CRM)
// ═══════════════════════════════════════════════════════════════

function getContacts() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Contacts');
  if (!sheet) {
    sheet = ss.insertSheet('Contacts');
    sheet.getRange(1, 1, 1, 13).setValues([['contactId', 'firstName', 'lastName', 'email', 'phone', 'company', 'billingAddress', 'propertyAddress', 'stage', 'source', 'notes', 'createdAt', 'updatedAt']]);
    return { success: true, contacts: [] };
  }
  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var contacts = [];
  for (var i = 1; i < data.length; i++) {
    var obj = {};
    for (var j = 0; j < headers.length; j++) {
      obj[headers[j]] = data[i][j];
    }
    contacts.push(obj);
  }
  return { success: true, contacts: contacts };
}

function saveContact(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Contacts');
  if (!sheet) {
    sheet = ss.insertSheet('Contacts');
    sheet.getRange(1, 1, 1, 13).setValues([['contactId', 'firstName', 'lastName', 'email', 'phone', 'company', 'billingAddress', 'propertyAddress', 'stage', 'source', 'notes', 'createdAt', 'updatedAt']]);
  }
  var contactId = 'C-' + Date.now();
  var now = new Date().toISOString();
  sheet.appendRow([
    contactId,
    data.firstName || '',
    data.lastName || '',
    data.email || '',
    data.phone || '',
    data.company || '',
    data.billingAddress || '',
    data.propertyAddress || '',
    data.stage || 'Lead',
    data.source || '',
    data.notes || '',
    now,
    now
  ]);
  return { success: true, contactId: contactId };
}

function updateContact(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Contacts');
  var rows = sheet.getDataRange().getValues();
  for (var i = 1; i < rows.length; i++) {
    if (String(rows[i][0]) === String(data.contactId)) {
      var now = new Date().toISOString();
      sheet.getRange(i + 1, 2, 1, 12).setValues([[
        data.firstName || '',
        data.lastName || '',
        data.email || '',
        data.phone || '',
        data.company || '',
        data.billingAddress || '',
        data.propertyAddress || '',
        data.stage || 'Lead',
        data.source || '',
        data.notes || '',
        rows[i][11],  // keep original createdAt
        now
      ]]);
      return { success: true };
    }
  }
  return { success: false, error: 'Contact not found' };
}

function deleteContact(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Contacts');
  var rows = sheet.getDataRange().getValues();
  for (var i = 1; i < rows.length; i++) {
    if (String(rows[i][0]) === String(data.contactId)) {
      sheet.deleteRow(i + 1);
      return { success: true };
    }
  }
  return { success: false, error: 'Contact not found' };
}

// ═══════════════════════════════════════════════════════════════
// PRODUCTION ANALYSIS
// ═══════════════════════════════════════════════════════════════

function getProductionAnalysis(e) {
  var startDate = (e.parameter && e.parameter.startDate) || '';
  var endDate = (e.parameter && e.parameter.endDate) || '';
  var crewFilter = (e.parameter && e.parameter.crew) || 'all';

  var ss = SpreadsheetApp.getActiveSpreadsheet();

  // ─── Read Scheduled Tickets ───
  var ticketSheet = ss.getSheetByName('Scheduled Tickets');
  if (!ticketSheet) return { success: true, services: [], items: [] };

  var ticketData = ticketSheet.getDataRange().getValues();
  var ticketHeaders = ticketData[0];
  var tCol = {};
  ['Ticket ID', 'Property Address', 'Assigned Crew', 'Event Date', 'Services JSON', 'Total Est Hours', 'Status'].forEach(function(h) {
    tCol[h] = ticketHeaders.indexOf(h);
  });

  // Filter tickets to completed/partial within date range
  var tickets = [];
  for (var i = 1; i < ticketData.length; i++) {
    var row = ticketData[i];
    if (!row[tCol['Ticket ID']]) continue;

    var status = String(row[tCol['Status']] || '').toLowerCase().trim();
    if (status !== 'completed' && status !== 'partial') continue;

    var rawDate = row[tCol['Event Date']];
    var dateStr = '';
    if (rawDate instanceof Date) {
      dateStr = rawDate.getFullYear() + '-' + String(rawDate.getMonth() + 1).padStart(2, '0') + '-' + String(rawDate.getDate()).padStart(2, '0');
    } else {
      dateStr = String(rawDate || '');
      if (dateStr.indexOf('T') !== -1) dateStr = dateStr.split('T')[0];
    }

    if (startDate && dateStr < startDate) continue;
    if (endDate && dateStr > endDate) continue;

    var crew = String(row[tCol['Assigned Crew']] || '');
    if (crewFilter !== 'all' && crew !== crewFilter) continue;

    var servicesRaw = row[tCol['Services JSON']] || '[]';
    var services;
    try { services = typeof servicesRaw === 'string' ? JSON.parse(servicesRaw) : servicesRaw; } catch(ex) { services = []; }

    tickets.push({
      ticketId: String(row[tCol['Ticket ID']]),
      propertyAddress: String(row[tCol['Property Address']] || ''),
      crew: crew,
      eventDate: dateStr,
      services: services
    });
  }

  // ─── Read Time Entries (service type only) ───
  var teSheet = ss.getSheetByName('Time Entries');
  var timeEntries = [];
  if (teSheet) {
    var teData = teSheet.getDataRange().getValues();
    var teHeaders = teData[0];
    var te = {};
    ['Entry ID', 'Ticket ID', 'Entry Type', 'Date', 'Duration Minutes', 'Service Name',
     'Member Count', 'Duration Type', 'Reopened', 'Estimated Hours', 'Crew'].forEach(function(h) {
      te[h] = teHeaders.indexOf(h);
    });

    for (var j = 1; j < teData.length; j++) {
      var teRow = teData[j];
      var entryType = te['Entry Type'] !== -1 ? String(teRow[te['Entry Type']] || '') : '';
      if (entryType !== 'service') continue;

      var teDateRaw = te['Date'] !== -1 ? teRow[te['Date']] : '';
      var teDateStr = '';
      if (teDateRaw instanceof Date) {
        teDateStr = teDateRaw.getFullYear() + '-' + String(teDateRaw.getMonth() + 1).padStart(2, '0') + '-' + String(teDateRaw.getDate()).padStart(2, '0');
      } else {
        teDateStr = String(teDateRaw || '');
        if (teDateStr.indexOf('T') !== -1) teDateStr = teDateStr.split('T')[0];
      }

      if (startDate && teDateStr < startDate) continue;
      if (endDate && teDateStr > endDate) continue;

      var teCrew = te['Crew'] !== -1 ? String(teRow[te['Crew']] || '') : '';
      if (crewFilter !== 'all' && teCrew !== crewFilter) continue;

      timeEntries.push({
        ticketId: te['Ticket ID'] !== -1 ? String(teRow[te['Ticket ID']] || '') : '',
        serviceName: te['Service Name'] !== -1 ? String(teRow[te['Service Name']] || '') : '',
        durationMinutes: te['Duration Minutes'] !== -1 ? (parseFloat(teRow[te['Duration Minutes']]) || 0) : 0,
        memberCount: te['Member Count'] !== -1 ? (parseInt(teRow[te['Member Count']]) || 1) : 1,
        durationType: te['Duration Type'] !== -1 ? String(teRow[te['Duration Type']] || 'scalable') : 'scalable',
        reopened: te['Reopened'] !== -1 ? String(teRow[te['Reopened']] || '') === 'true' : false,
        estimatedHours: te['Estimated Hours'] !== -1 ? (parseFloat(teRow[te['Estimated Hours']]) || 0) : 0
      });
    }
  }

  // ─── Aggregate time entries by ticketId + serviceName ───
  var teAgg = {}; // key: ticketId|serviceName
  for (var k = 0; k < timeEntries.length; k++) {
    var entry = timeEntries[k];
    var key = entry.ticketId + '|' + entry.serviceName;
    if (!teAgg[key]) {
      teAgg[key] = { totalMinutes: 0, totalManMinutes: 0, maxMemberCount: 0, reopened: false, durationType: entry.durationType, estimatedHours: entry.estimatedHours };
    }
    teAgg[key].totalMinutes += entry.durationMinutes;
    var manMin = entry.durationType === 'fixed' ? entry.durationMinutes : entry.durationMinutes * entry.memberCount;
    teAgg[key].totalManMinutes += manMin;
    if (entry.memberCount > teAgg[key].maxMemberCount) teAgg[key].maxMemberCount = entry.memberCount;
    if (entry.reopened) teAgg[key].reopened = true;
    if (entry.estimatedHours > 0 && teAgg[key].estimatedHours === 0) teAgg[key].estimatedHours = entry.estimatedHours;
  }

  // ─── Build service-level aggregation ───
  var serviceAgg = {}; // key: serviceName
  var ticketDetails = {}; // key: serviceName -> array of ticket details

  for (var t2 = 0; t2 < tickets.length; t2++) {
    var ticket = tickets[t2];
    for (var s = 0; s < ticket.services.length; s++) {
      var svc = ticket.services[s];
      var svcName = svc.name || svc.serviceName || '';
      if (!svcName) continue;
      var estHours = parseFloat(svc.estimatedHours) || 0;
      var teKey = ticket.ticketId + '|' + svcName;
      var actual = teAgg[teKey];

      if (!actual) continue; // No time entries for this service on this ticket

      var actualManHours = actual.totalManMinutes / 60;

      if (!serviceAgg[svcName]) {
        serviceAgg[svcName] = { ticketCount: 0, totalEstHours: 0, totalActualManHours: 0, reopenedCount: 0, itemCount: 0 };
      }
      serviceAgg[svcName].ticketCount++;
      serviceAgg[svcName].totalEstHours += estHours;
      serviceAgg[svcName].totalActualManHours += actualManHours;
      if (actual.reopened) serviceAgg[svcName].reopenedCount++;

      // Track item count from first ticket we see
      var items = svc.items || [];
      if (items.length > serviceAgg[svcName].itemCount) serviceAgg[svcName].itemCount = items.length;

      if (!ticketDetails[svcName]) ticketDetails[svcName] = [];

      // Build item-level implied rates
      var ticketItems = [];
      for (var it = 0; it < items.length; it++) {
        var item = items[it];
        var itemEntry = {
          name: item.name || '',
          estimatedHours: parseFloat(item.hours) || 0,
          unit: item.unit || ''
        };
        if (item.quantities) {
          itemEntry.quantities = item.quantities;
          // Calculate implied rates using efficiency ratio
          if (estHours > 0 && actualManHours > 0) {
            var efficiencyRatio = estHours / actualManHours;
            itemEntry.impliedRate = {};
            ['easy', 'medium', 'hard'].forEach(function(diff) {
              var qty = parseFloat((item.quantities || {})[diff]) || 0;
              var itemHrs = parseFloat(item.hours) || 0;
              if (qty > 0 && itemHrs > 0) {
                var catalogRate = qty / itemHrs;
                itemEntry.impliedRate[diff] = Math.round(catalogRate * efficiencyRatio);
              }
            });
          }
        }
        ticketItems.push(itemEntry);
      }

      ticketDetails[svcName].push({
        ticketId: ticket.ticketId,
        propertyAddress: ticket.propertyAddress,
        eventDate: ticket.eventDate,
        crew: ticket.crew,
        estimatedHours: estHours,
        actualManHours: Math.round(actualManHours * 100) / 100,
        memberCount: actual.maxMemberCount,
        durationMinutes: Math.round(actual.totalMinutes),
        reopened: actual.reopened,
        items: ticketItems
      });
    }
  }

  // ─── Build service response array ───
  var servicesResult = [];
  Object.keys(serviceAgg).forEach(function(svcName) {
    var agg = serviceAgg[svcName];
    var efficiency = agg.totalEstHours > 0 ? agg.totalEstHours / agg.totalActualManHours : 0;
    servicesResult.push({
      serviceName: svcName,
      ticketCount: agg.ticketCount,
      totalEstimatedHours: Math.round(agg.totalEstHours * 100) / 100,
      totalActualManHours: Math.round(agg.totalActualManHours * 100) / 100,
      efficiency: Math.round(efficiency * 100) / 100,
      avgEstPerVisit: agg.ticketCount > 0 ? Math.round((agg.totalEstHours / agg.ticketCount) * 100) / 100 : 0,
      avgActualPerVisit: agg.ticketCount > 0 ? Math.round((agg.totalActualManHours / agg.ticketCount) * 100) / 100 : 0,
      reopenedCount: agg.reopenedCount,
      itemCount: agg.itemCount,
      tickets: ticketDetails[svcName] || []
    });
  });

  // ─── Build item-level aggregation ───
  // Collect all item data across tickets for field rate calculation
  var itemAgg = {}; // key: itemName

  Object.keys(ticketDetails).forEach(function(svcName) {
    var svcTickets = ticketDetails[svcName];
    var isSingleItem = (serviceAgg[svcName].itemCount === 1);

    for (var td = 0; td < svcTickets.length; td++) {
      var tDetail = svcTickets[td];
      for (var ii = 0; ii < tDetail.items.length; ii++) {
        var itm = tDetail.items[ii];
        if (!itm.name || !itm.quantities) continue;

        if (!itemAgg[itm.name]) {
          itemAgg[itm.name] = {
            unit: itm.unit || '',
            singleItemQty: { easy: 0, medium: 0, hard: 0 },
            singleItemHours: 0,
            singleItemCount: 0,
            inferredRateSum: { easy: 0, medium: 0, hard: 0 },
            inferredRateCount: { easy: 0, medium: 0, hard: 0 },
            multiItemCount: 0
          };
        }

        if (isSingleItem && tDetail.actualManHours > 0) {
          // Measured rate: direct totalQty / actualManHours
          itemAgg[itm.name].singleItemCount++;
          itemAgg[itm.name].singleItemHours += tDetail.actualManHours;
          ['easy', 'medium', 'hard'].forEach(function(d) {
            itemAgg[itm.name].singleItemQty[d] += parseFloat((itm.quantities || {})[d]) || 0;
          });
        } else if (itm.impliedRate) {
          // Inferred rate from multi-item services
          itemAgg[itm.name].multiItemCount++;
          ['easy', 'medium', 'hard'].forEach(function(d) {
            if (itm.impliedRate[d]) {
              itemAgg[itm.name].inferredRateSum[d] += itm.impliedRate[d];
              itemAgg[itm.name].inferredRateCount[d]++;
            }
          });
        }
      }
    }
  });

  // ─── Read Item Catalog for catalog rates ───
  var catalogRatesMap = {};
  var catalogSheet = ss.getSheetByName('Item Catalog');
  if (catalogSheet) {
    var catData = catalogSheet.getDataRange().getValues();
    var catHeaders = catData[0];
    var catItemCol = catHeaders.indexOf('Item');
    var catUnitCol = catHeaders.indexOf('Unit');
    var catEasyCol = catHeaders.indexOf('Easy');
    var catMedCol = catHeaders.indexOf('Medium');
    var catHardCol = catHeaders.indexOf('Hard');

    for (var ci = 1; ci < catData.length; ci++) {
      var catRow = catData[ci];
      var catName = catItemCol !== -1 ? String(catRow[catItemCol] || '') : '';
      if (catName) {
        catalogRatesMap[catName] = {
          easy: catEasyCol !== -1 ? (parseFloat(catRow[catEasyCol]) || 0) : 0,
          medium: catMedCol !== -1 ? (parseFloat(catRow[catMedCol]) || 0) : 0,
          hard: catHardCol !== -1 ? (parseFloat(catRow[catHardCol]) || 0) : 0
        };
      }
    }
  }

  var itemsResult = [];
  Object.keys(itemAgg).forEach(function(itemName) {
    var ia = itemAgg[itemName];
    var catRates = catalogRatesMap[itemName] || { easy: 0, medium: 0, hard: 0 };

    var measuredRate = {};
    ['easy', 'medium', 'hard'].forEach(function(d) {
      if (ia.singleItemQty[d] > 0 && ia.singleItemHours > 0) {
        measuredRate[d] = Math.round(ia.singleItemQty[d] / ia.singleItemHours);
      }
    });

    var inferredRate = {};
    ['easy', 'medium', 'hard'].forEach(function(d) {
      if (ia.inferredRateCount[d] > 0) {
        inferredRate[d] = Math.round(ia.inferredRateSum[d] / ia.inferredRateCount[d]);
      }
    });

    itemsResult.push({
      itemName: itemName,
      unit: ia.unit,
      catalogRates: catRates,
      fieldData: {
        singleItemServices: ia.singleItemCount,
        measuredRate: measuredRate,
        multiItemServices: ia.multiItemCount,
        inferredRate: inferredRate
      }
    });
  });

  return {
    success: true,
    services: servicesResult,
    items: itemsResult
  };
}
