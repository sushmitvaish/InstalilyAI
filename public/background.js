// Open the side panel when the extension icon is clicked
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ windowId: tab.windowId });
});

// Enable the side panel on all sites
chrome.sidePanel.setOptions({
  enabled: true,
});

// Also allow opening via side panel button in Chrome
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
