chrome.runtime.onInstalled.addListener(() => {
    console.log("MetaGen Video extension installed and service worker is running.");
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log("Message received in background script:", request);
});
