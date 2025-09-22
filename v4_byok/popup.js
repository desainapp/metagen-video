document.addEventListener("DOMContentLoaded", () => {
    const startButton = document.getElementById("start-button");
    const stopButton = document.getElementById("stop-button");
    const status = document.getElementById("status");

    startButton.addEventListener("click", () => {
        status.textContent = "Starting process...";
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            console.log("Sending start message to tab:", tabs[0].id);
            chrome.tabs.sendMessage(tabs[0].id, {
                action: "start",
            });
        });
    });

    stopButton.addEventListener("click", () => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            console.log("Sending stop message to tab:", tabs[0].id);
            chrome.tabs.sendMessage(tabs[0].id, { action: "stop" });
            status.textContent = "Processing stopped.";
        });
    });
});
