import time
import os
import json
import requests
from flask import Flask, request, jsonify
from google import genai
from flask_cors import CORS
from supabase import create_client, Client
import uuid
import re

# ==========================
# Flask App Setup
# ==========================
app = Flask(__name__)
CORS(app)


API_KEY = "API_KEY"
client = genai.Client(api_key=API_KEY)

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

    data = request.get_json()
    if not data or "video_url" not in data:
        return jsonify({"error": "Missing video_url in request body"}), 400

    video_url = data["video_url"]

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(video_url, stream=True, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to download video: {e}"}), 400

    # Save file temporarily
    temp_filename = f"{uuid.uuid4()}.mp4"
    temp_filepath = os.path.join("/tmp", temp_filename)
    
    with open(temp_filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    uploaded_file = None
    try:
        print(f"Uploading file: {temp_filepath}")
        uploaded_file = client.files.upload(file=temp_filepath)
        print(f"Completed upload: {uploaded_file.uri}")

        while uploaded_file.state.name == "PROCESSING":
            print("Processing...")
            time.sleep(10)
            uploaded_file = client.files.get(name=uploaded_file.name)

        if uploaded_file.state.name == "FAILED":
            raise ValueError("File processing failed.")

        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=[uploaded_file, SYSTEM_PROMPT]
        )
        print(response.text)

        cleaned_text = response.text.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.strip("`")
        if cleaned_text.lower().startswith("json"):
            cleaned_text = cleaned_text[4:].strip()
            
        # Remove trailing commas that might cause JSON decoding errors
        cleaned_text = re.sub(r",\s*([}\]])", r"\1", cleaned_text)
        
        metadata_json = json.loads(cleaned_text)

        if metadata_json:
            return jsonify(metadata_json), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the uploaded file from Google and the temporary local file
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
                print(f"Deleted remote file: {uploaded_file.name}")
            except Exception as e:
                print(f"Error deleting remote file {uploaded_file.name}: {e}")
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            print(f"Deleted temporary file: {temp_filepath}")

    return jsonify({"error": "An unexpected error occurred"}), 500

# ==========================
# Run App
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2411, debug=True)
