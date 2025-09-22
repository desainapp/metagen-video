import sys
import time
import os
import json
import requests
import random
from flask import Flask, request, jsonify
from google import genai
from flask_cors import CORS
import uuid
import re
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFrame
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor
from werkzeug.serving import make_server

# Global variables
api_keys = ["AIzaSyCNDlnQmPaihCSdqqu_5AzQ_ywJSvj0s1c"]  # Default, can be overridden
server_running = False
log_text = ""

# ==========================
# Flask App Setup
# ==========================
app = Flask(__name__)
CORS(app)

SYSTEM_PROMPT = """
You are an expert in stock video metadata creation for platforms like Shutterstock, Adobe Stock, and Istock.
The user will upload an video. Your task is to analyze the image and generate the following metadata in English:

1. **Title**
   - Short, descriptive, 10–20 words.
   - Describe the main object and style.
   - No special characters.


3. **Keywords**
   - 40–45 additional relevant keywords.
   - Include synonyms, related events, styles, and uses.
   - Comma-separated.
   - No Numbers
   - Avoid duplicate keywords

4. **Descriptions**
   - 1–2 sentences describing the video in detail.
   - Mention colors, style, and background.
   - Avoid marketing language.
   - Avoid sentence like "This is vieo of..", just straight to point

Return ONLY pure JSON in this format without code block, markdown, or extra text:
{
  "title": "...",
  "keywords": "...",
  "description": "..."
}
"""

# ==========================
# Routes
# ==========================
@app.route("/")
def hello_world():
    return "Video Metadata API is Working! by @mujib_banget"

@app.route("/generate-video-metadata", methods=["POST"])
def generate_video_metadata():
    global api_keys, log_text
    if not api_keys:
        error_msg = "No API keys provided."
        log_text += f"[ERROR] {error_msg}\n"
        return jsonify({"error": error_msg}), 400

    selected_api_key = random.choice(api_keys)
    client = genai.Client(api_key=selected_api_key)

    data = request.get_json()
    if not data or "video_url" not in data:
        error_msg = "Missing video_url in request body"
        log_text += f"[ERROR] {error_msg}\n"
        return jsonify({"error": error_msg}), 400

    video_url = data["video_url"]
    log_text += f"[INFO] Processing video URL: {video_url}\n"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(video_url, stream=True, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to download video: {e}"
        log_text += f"[ERROR] {error_msg}\n"
        return jsonify({"error": error_msg}), 400

    # Save file temporarily
    temp_filename = f"{uuid.uuid4()}.mp4"
    temp_filepath = os.path.join("/tmp", temp_filename)

    with open(temp_filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    uploaded_file = None
    try:
        log_text += f"[INFO] Uploading file: {temp_filepath}\n"
        uploaded_file = client.files.upload(file=temp_filepath)
        log_text += f"[INFO] Completed upload: {uploaded_file.uri}\n"

        while uploaded_file.state.name == "PROCESSING":
            log_text += "[INFO] Processing...\n"
            time.sleep(10)
            uploaded_file = client.files.get(name=uploaded_file.name)

        if uploaded_file.state.name == "FAILED":
            raise ValueError("File processing failed.")

        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=[uploaded_file, SYSTEM_PROMPT]
        )
        log_text += f"[INFO] Generated content: {response.text}\n"

        cleaned_text = response.text.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.strip("`")
        if cleaned_text.lower().startswith("json"):
            cleaned_text = cleaned_text[4:].strip()

        # Remove trailing commas that might cause JSON decoding errors
        cleaned_text = re.sub(r",\s*([}\]])", r"\1", cleaned_text)

        metadata_json = json.loads(cleaned_text)

        if metadata_json:
            log_text += "[INFO] Metadata generated successfully\n"
            return jsonify(metadata_json), 200

    except Exception as e:
        error_msg = str(e)
        log_text += f"[ERROR] {error_msg}\n"
        return jsonify({"error": error_msg}), 500
    finally:
        # Clean up the uploaded file from Google and the temporary local file
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
                log_text += f"[INFO] Deleted remote file: {uploaded_file.name}\n"
            except Exception as e:
                log_text += f"[ERROR] Error deleting remote file {uploaded_file.name}: {e}\n"
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            log_text += f"[INFO] Deleted temporary file: {temp_filepath}\n"

    error_msg = "An unexpected error occurred"
    log_text += f"[ERROR] {error_msg}\n"
    return jsonify({"error": error_msg}), 500

# ==========================
# GUI Class
# ==========================
class ServerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.server_thread = None

    def initUI(self):
        self.setWindowTitle("Video Metadata Server GUI")
        self.setGeometry(100, 100, 600, 500)

        layout = QVBoxLayout()

        # Status
        self.status_label = QLabel("Server Status: 🔴 Off")
        self.status_label.setFont(QFont("Arial", 14))
        layout.addWidget(self.status_label)

        # API Keys Input
        layout.addWidget(QLabel("API Keys (one per line):"))
        self.api_input = QTextEdit()
        self.api_input.setPlainText("AIzaSyCNDlnQmPaihCSdqqu_5AzQ_ywJSvj0s1c")
        self.api_input.setMinimumHeight(100)
        layout.addWidget(self.api_input)

        # Start/Stop Button
        self.toggle_button = QPushButton("Start Server")
        self.toggle_button.clicked.connect(self.toggle_server)
        layout.addWidget(self.toggle_button)

        # Logs
        layout.addWidget(QLabel("Logs:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(125)
        layout.addWidget(self.log_area)

        # Footer
        footer_frame = QFrame()
        footer_layout = QHBoxLayout()
        footer_label = QLabel('<a href="https://desain.app">Powered by desain.app</a>')
        footer_label.setOpenExternalLinks(True)
        footer_layout.addWidget(footer_label)
        footer_frame.setLayout(footer_layout)
        layout.addWidget(footer_frame)

        self.setLayout(layout)

        # Timer to update logs
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_logs)
        self.timer.start(1000)  # Update every second

    def toggle_server(self):
        global server_running, api_keys, log_text
        if server_running:
            server_running = False
            self.status_label.setText("Server Status: 🔴 Off")
            self.toggle_button.setText("Start Server")
            if self.server_thread and hasattr(self.server_thread, 'server') and self.server_thread.server:
                self.server_thread.server.shutdown()
                log_text += "[INFO] Server stopped\n"
                self.server_thread.wait()
        else:
            # Update API keys
            api_keys_text = self.api_input.toPlainText().strip()
            if api_keys_text:
                api_keys = [line.strip() for line in api_keys_text.split('\n') if line.strip()]
            else:
                api_keys = []

            server_running = True
            self.status_label.setText("Server Status: 🟢 On")
            self.toggle_button.setText("Stop Server")
            log_text += "[INFO] Server started on http://localhost:2411\n"
            self.server_thread = ServerThread()
            self.server_thread.start()

    def update_logs(self):
        global log_text
        self.log_area.setPlainText(log_text)

class ServerThread(QThread):
    def __init__(self):
        super().__init__()
        self.server = None

    def run(self):
        self.server = make_server('0.0.0.0', 2411, app)
        self.server.serve_forever()

# ==========================
# Main
# ==========================
if __name__ == "__main__":
    app_qt = QApplication(sys.argv)
    gui = ServerGUI()
    gui.show()
    sys.exit(app_qt.exec())
