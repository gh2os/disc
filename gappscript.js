function onEdit(e) {
    const sheet = e.source.getActiveSheet();
    const range = e.range;
    const editedCell = range.getA1Notation();
  
    // Allow editing only on the "Overrides" sheet
    if (sheet.getName() === 'Overrides') {
      // Check if the edited cell is in the 'Date' column
      const dateColumnIndex = sheet.getRange('C1').getColumn(); // Assuming 'Date' is in column C
      const editedColumnIndex = range.getColumn();
      const editedRowIndex = range.getRow();
  
      if (editedColumnIndex === dateColumnIndex && editedRowIndex > 1) { // Exclude header row
        const editedDate = new Date(sheet.getRange(editedCell).getValue());
        const today = new Date();
        today.setHours(0, 0, 0, 0); // Set time to midnight
  
        // Check if the edited date is today's date
        if (editedDate.getTime() !== today.getTime() && !isAdminUser()) {
          // Show an alert and undo the edit if the date is not today and user is not an admin
          SpreadsheetApp.getUi().alert('You can only edit scores for today\'s date.');
          e.range.setValue(e.oldValue); // Revert the edit
          return;
        }
      }
  
      processScores();
      triggerGitHubAction();
    }
  }
  
  function isAdminUser() {
    const adminEmails = ['admin1@example.com', 'admin2@example.com']; // Replace with actual admin emails
    const userEmail = Session.getActiveUser().getEmail();
    return adminEmails.includes(userEmail);
  }
  
  function processScores() {
    const sheet = SpreadsheetApp.getActiveSpreadsheet();
    const formResponsesSheet = sheet.getSheetByName('Form Responses');
    const overridesSheet = sheet.getSheetByName('Overrides');
    const processedSheet = sheet.getSheetByName('Processed Scores');
  
    const formValues = formResponsesSheet.getDataRange().getValues();
    const overrideValues = overridesSheet.getDataRange().getValues();
    
    const headers = formValues[0];
    const playerNameIndex = headers.indexOf('Player Name');
    const dateIndex = headers.indexOf('Date');
    const scoreIndex = headers.indexOf('Score');
  
    const processedScores = [];
    const overridesMap = {};
  
    // Create a map for overrides
    overrideValues.forEach((row, index) => {
      if (index === 0) return; // Skip header
      const [playerName, date, score, adjustment] = row;
      if (!overridesMap[playerName]) {
        overridesMap[playerName] = {};
      }
      overridesMap[playerName][date] = score;
    });
  
    // Process form responses and apply overrides
    formValues.slice(1).forEach(row => {
      const playerName = row[playerNameIndex];
      const date = row[dateIndex];
      let score = row[scoreIndex];
  
      // Apply override if exists
      if (overridesMap[playerName] && overridesMap[playerName][date]) {
        score = overridesMap[playerName][date];
      }
  
      processedScores.push([playerName, date, score]);
    });
  
    // Add scores from overrides that are not in form responses
    overrideValues.slice(1).forEach(row => {
      const [playerName, date, score] = row;
      const exists = processedScores.some(entry => entry[0] === playerName && entry[1] === date);
      if (!exists) {
        processedScores.push([playerName, date, score]);
      }
    });
  
    // Clear the output sheet and set new values
    processedSheet.clear();
    processedSheet.getRange(1, 1, processedScores.length, processedScores[0].length).setValues(processedScores);
  }
  
  function triggerGitHubAction() {
    const url = "https://api.github.com/repos/yourusername/yourrepo/dispatches";
    const token = "your_github_token";
    
    const payload = {
      event_type: "google_sheets_update",
      client_payload: {
        sheet: 'Overrides'
      }
    };
  
    const options = {
      method: 'post',
      contentType: 'application/json',
      headers: {
        Authorization: 'Bearer ' + token
      },
      payload: JSON.stringify(payload)
    };
  
    UrlFetchApp.fetch(url, options);
  }