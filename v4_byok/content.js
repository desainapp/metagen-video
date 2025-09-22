let isProcessing = false;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "start") {
        console.log("Message received from popup. Starting process...");
        isProcessing = true;
        processVideoCards();
    } else if (request.action === "stop") {
        console.log("Stop message received. Halting process...");
        isProcessing = false;
    }
});

// Helper function to wait for an element to appear in the DOM
function waitForElement(selector, timeout = 5000) {
    return new Promise((resolve, reject) => {
        const interval = 100;
        const endTime = Date.now() + timeout;
        const timer = setInterval(() => {
            const element = document.querySelector(selector);
            if (element) {
                clearInterval(timer);
                resolve(element);
            } else if (Date.now() > endTime) {
                clearInterval(timer);
                reject(new Error(`Element not found: ${selector}`));
            }
        }, interval);
    });
}

async function processVideoCards() {
    console.log("Searching for video cards...");
    const cards = document.querySelectorAll('.upload-tile__thumbnail');
    console.log(`Found ${cards.length} cards.`);

    for (let i = 0; i < cards.length; i++) {
        if (!isProcessing) {
            console.log("Processing was stopped. Exiting loop.");
            break;
        }

        const card = cards[i];
        console.log(`Processing card ${i + 1}/${cards.length}`);
        card.click();

        try {
            // Wait for the sidebar thumbnail to appear and then click it
            const sidebarThumb = await waitForElement('[data-t="asset-sidebar-header-thumbnail"]');
            console.log("Found sidebar thumbnail. Clicking to open modal.");
            sidebarThumb.click();

            // Wait for the video player source to appear
            const videoElement = await waitForElement('[data-t="asset-preview-modal-video-player"] source');
            const videoUrl = videoElement.src;
            console.log("Found video URL:", videoUrl);

            if (videoUrl.endsWith('.mp4')) {
                console.log("Fetching metadata for:", videoUrl);
                const metadata = await fetchMetadata(videoUrl);
                console.log("Metadata received:", metadata);
                fillMetadata(metadata);

                // Wait a moment for the UI to update before closing
                console.log("Waiting 1 second for UI to update...");
                await new Promise(resolve => setTimeout(resolve, 1000));
            } else {
                console.log("Source is not an MP4 video. Skipping.");
            }

        } catch (error) {
            console.error(`Error processing card ${i + 1}:`, error.message);
        }

        // Close the modal
        const closeButton = document.querySelector('a.modal__close[data-t="asset-preview-modal-close"]');
        if (closeButton) {
            console.log("Closing modal.");
            closeButton.click();
            await new Promise(resolve => setTimeout(resolve, 500)); // Brief pause for modal to close
        } else {
            console.log("Close button not found. Moving to next card.");
        }
    }
    console.log("Finished processing all cards.");
}

async function fetchMetadata(videoUrl) {
    const response = await fetch('http://localhost:2411/generate-video-metadata', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ video_url: videoUrl }),
    });
    if (!response.ok) {
        throw new Error('Failed to fetch metadata');
    }
    return await response.json();
}

function fillMetadata(metadata) {
    function setReactValue(element, value) {
        let prototype = element instanceof HTMLTextAreaElement
            ? HTMLTextAreaElement.prototype
            : HTMLInputElement.prototype;

        let setValue = Object.getOwnPropertyDescriptor(prototype, "value").set;
        setValue.call(element, value);

        element.dispatchEvent(new Event("input", { bubbles: true }));
        element.dispatchEvent(new Event("change", { bubbles: true }));
    }

    // === Title ===
    const titleInput = document.querySelector('[data-t="asset-title-content-tagger"]');
    if (titleInput) {
        console.log("Setting title:", metadata.title);
        setReactValue(titleInput, metadata.title);
    } else {
        console.log("Title input not found.");
    }

    // === Keywords ===
    const textarea = document.querySelector("#content-keywords-ui-textarea");
    if (textarea) {
        // Pecah string jadi array dan rapikan
        const keywords = metadata.keywords
            .split(',')
            .map(k => k.trim())
            .filter(Boolean);

        // Simpan sebagai global variable
        window.keywords = keywords;
        console.log(window.keywords);

        // Log dalam format array seperti yang kamu mau
        console.log("const keywords = [\n  \"" + keywords.join('",\n  "') + "\"\n];");

        // Isi textarea dengan string gabungan
        setReactValue(textarea, window.keywords.join(", "));
    } else {
        console.log("Keywords textarea not found.");
    }
    setTimeout(() => {
        console.log("2 detik kemudian");
    }, 2000);
}
