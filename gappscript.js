function onEdit(e) {
  triggerGitHubAction();
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