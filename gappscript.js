function onFormSubmit(e) {
    processScores();
    triggerGitHubAction();
  }
  
  function onEdit(e) {
    const sheet = e.source.getActiveSheet();
    const range = e.range;
    const editedCell = range.getA1Notation();
  
    if (sheet.getName() === 'Overrides') {
      const dateColumnIndex = sheet.getRange('C1').getColumn(); // Assuming 'Date' is in column C
      const editedColumnIndex = range.getColumn();
      const editedRowIndex = range.getRow();
  
      if (editedColumnIndex === dateColumnIndex && editedRowIndex > 1) {
        const editedDate = new Date(sheet.getRange(editedCell).getValue());
        const today = new Date();
        today.setHours(0, 0, 0, 0);
  
        if (editedDate.getTime() !== today.getTime() && !isAdminUser()) {
          SpreadsheetApp.getUi().alert('You can only edit scores for today\'s date.');
          e.range.setValue(e.oldValue);
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
  
    overrideValues.forEach((row, index) => {
      if (index === 0) return;
      const [playerName, date, score, adjustment] = row;
      if (!overridesMap[playerName]) {
        overridesMap[playerName] = {};
      }
      overridesMap[playerName][date] = score;
    });
  
    formValues.slice(1).forEach(row => {
      const playerName = row[playerNameIndex];
      const date = row[dateIndex];
      let score = row[scoreIndex];
  
      if (overridesMap[playerName] && overridesMap[playerName][date]) {
        score = overridesMap[playerName][date];
      }
  
      processedScores.push([playerName, date, score]);
    });
  
    overrideValues.slice(1).forEach(row => {
      const [playerName, date, score] = row;
      const exists = processedScores.some(entry => entry[0] === playerName && entry[1] === date);
      if (!exists) {
        processedScores.push([playerName, date, score]);
      }
    });
  
    processedSheet.clear();
    processedSheet.getRange(1, 1, processedScores.length, processedScores[0].length).setValues(processedScores);
  }
  
  function triggerGitHubAction() {
    const url = "https://api.github.com/repos/yourusername/yourrepo/dispatches";
    const token = "your_github_token"; // Add your GitHub token here
    
    const payload = {
      event_type: "google_sheets_update",
      client_payload: {
        sheet: 'Form Responses'
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