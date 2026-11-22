import json
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/analyze": {
            "origins": [
                "http://localhost:5500",
                "http://127.0.0.1:5500",
                "https://jaicare-seven.vercel.app",
            ],
            "methods": ["POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    },
)

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if not API_KEY:
    raise RuntimeError(
        "ไม่พบ GEMINI_API_KEY กรุณาตั้งค่า Environment Variable GEMINI_API_KEY"
    )

genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-3.5-flash-lite")


def detect_fallback_language(text):
    if any("\u0e00" <= char <= "\u0e7f" for char in text):
        return "th"
    return "en"


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "Jaicare mood analysis backend",
    })


@app.route("/analyze", methods=["POST", "OPTIONS"])
def analyze_diary():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json(silent=True) or {}
    diary_text = str(data.get("text", "")).strip()
    language = str(data.get("language", "auto")).strip().lower()

    if not diary_text:
        return jsonify({
            "error": "กรุณากรอกข้อความไดอารี่",
        }), 400

    if language not in ("th", "en", "auto"):
        language = "auto"

    if language == "en":
        language_instruction = """
The requested response language is English.
Write detected_dyad, dominant_emotion_th, and reply_message in English.
Do not write Thai in those values.
"""
        fallback_language = "en"

    elif language == "th":
        language_instruction = """
ภาษาที่ต้องการคือภาษาไทย
เขียนค่า detected_dyad, dominant_emotion_th และ reply_message เป็นภาษาไทย
ห้ามเขียนค่าเหล่านี้เป็นภาษาอังกฤษ
"""
        fallback_language = "th"

    else:
        language_instruction = """
Detect the primary language used in the diary entry.
Write detected_dyad, dominant_emotion_th, and reply_message in that same language.
Do not choose the response language based on these instructions.
Use the language of the diary entry. If the diary is mainly Thai, respond in Thai.
If it is mainly English, respond in English.
"""
        fallback_language = detect_fallback_language(diary_text)

    prompt = f"""
You are a supportive emotion-analysis assistant.
Analyze the user's diary entry using Plutchik's Wheel of Emotions.
This is an estimate based only on the text, not a medical diagnosis.

Diary entry:
{diary_text}

{language_instruction}

Return only valid JSON. Do not include Markdown or text outside the JSON.
Keep all JSON keys and primary_emotions keys exactly as written below.
All text values must follow the requested or detected response language.

Use this exact JSON structure:
{{
  "primary_emotions": {{
    "joy": 0.0,
    "trust": 0.0,
    "fear": 0.0,
    "surprise": 0.0,
    "sadness": 0.0,
    "disgust": 0.0,
    "anger": 0.0,
    "anticipation": 0.0
  }},
  "detected_dyad": "the detected emotion combination, or None",
  "dominant_emotion_th": "the dominant emotion",
  "reply_message": "a warm, natural, empathetic response in the required language"
}}

Each primary_emotions value must be a number from 0.0 to 1.0.
Choose reasonable scores based on the diary entry.
"""

    raw_text = ""

    try:
        response = gemini_model.generate_content(prompt)
        raw_text = (response.text or "").strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.replace("```json", "", 1)
            raw_text = raw_text.replace("```", "")
            raw_text = raw_text.strip()

        analysis_result = json.loads(raw_text)
        primary_emotions = analysis_result.get("primary_emotions", {})

        if not isinstance(primary_emotions, dict):
            primary_emotions = {}

        normalized_emotions = {}

        for emotion in (
            "joy",
            "trust",
            "fear",
            "surprise",
            "sadness",
            "disgust",
            "anger",
            "anticipation",
        ):
            try:
                value = float(primary_emotions.get(emotion, 0))
            except (TypeError, ValueError):
                value = 0.0

            normalized_emotions[emotion] = max(0.0, min(1.0, value))

        if fallback_language == "en":
            default_dyad = "None"
            default_dominant_emotion = "Mixed emotions"
            default_reply = "Thank you for sharing how you feel."
        else:
            default_dyad = "ไม่มีอารมณ์ผสมที่ชัดเจน"
            default_dominant_emotion = "ความรู้สึกปนกัน"
            default_reply = "ขอบคุณที่แบ่งปันความรู้สึกนะคะ"

        result = {
            "primary_emotions": normalized_emotions,
            "detected_dyad": analysis_result.get(
                "detected_dyad",
                default_dyad,
            ),
            "dominant_emotion_th": analysis_result.get(
                "dominant_emotion_th",
                default_dominant_emotion,
            ),
            "reply_message": analysis_result.get(
                "reply_message",
                default_reply,
            ),
        }

        print(
            "ผลการวิเคราะห์:",
            json.dumps(result, ensure_ascii=False, indent=2),
        )

        return jsonify(result), 200

    except json.JSONDecodeError as error:
        print("Gemini returned invalid JSON:", error)
        print("Raw response:", raw_text)
        return jsonify({
            "error": "AI ส่งข้อมูลกลับมาไม่ตรงรูปแบบ JSON",
        }), 500

    except Exception as error:
        print("Error:", str(error))
        return jsonify({
            "error": str(error),
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )