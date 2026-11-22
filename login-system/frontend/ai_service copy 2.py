import json
import os

from dotenv import load_dotenv
from flask import Flask, request, jsonify
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
    language = str(data.get("language", "th")).strip().lower()

    if not diary_text:
        return jsonify({
            "error": "กรุณากรอกข้อความไดอารี่",
        }), 400

    if language not in ("th", "en"):
        language = "th"

    if language == "en":
        language_instruction = """
IMPORTANT LANGUAGE REQUIREMENT:
- Write reply_message in English only.
- Write detected_dyad in English.
- Write dominant_emotion_th in English.
- Do not include Thai text.
"""
        reply_language = "English"
    else:
        language_instruction = """
ข้อกำหนดเรื่องภาษา:
- เขียน reply_message เป็นภาษาไทยเท่านั้น
- ใช้ถ้อยคำที่อบอุ่น อ่อนโยน และเห็นอกเห็นใจ
- เขียน detected_dyad และ dominant_emotion_th เป็นภาษาไทย
"""
        reply_language = "Thai"

    prompt = f"""
คุณคือ AI ผู้เชี่ยวชาญด้านจิตวิทยา
วิเคราะห์ข้อความบันทึกประจำวันต่อไปนี้ตามทฤษฎี
Plutchik's Wheel of Emotions

ข้อความผู้ใช้:
{diary_text}

{language_instruction}

ให้ตอบกลับเฉพาะ JSON ที่ถูกต้องและวิเคราะห์ได้จากข้อความเท่านั้น
ห้ามใช้ code block
ห้ามเพิ่ม Markdown หรือข้อความอื่นนอก JSON
ภาษาที่ต้องตอบสำหรับข้อความทั้งหมดคือ: {reply_language}

โครงสร้าง JSON ที่ต้องใช้:

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
  "detected_dyad": "ชื่ออารมณ์ผสม",
  "dominant_emotion_th": "ชื่ออารมณ์หลัก",
  "reply_message": "ข้อความตอบกลับตามภาษาที่เลือก"
}}

คะแนนแต่ละ primary_emotions ต้องเป็นตัวเลขทศนิยม
ระหว่าง 0.0 ถึง 1.0
ค่าต้องสะท้อนระดับอารมณ์ที่วิเคราะห์ได้อย่างสมเหตุสมผล
"""

    try:
        response = gemini_model.generate_content(prompt)
        raw_text = response.text.strip()

        raw_text = raw_text.replace("```json", "")
        raw_text = raw_text.replace("```", "")
        raw_text = raw_text.strip()

        analysis_result = json.loads(raw_text)
        primary_emotions = analysis_result.get("primary_emotions", {})

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

            normalized_emotions[emotion] = max(
                0.0,
                min(1.0, value),
            )

        result = {
            "primary_emotions": normalized_emotions,
            "detected_dyad": analysis_result.get(
                "detected_dyad",
                "None",
            ),
            "dominant_emotion_th": analysis_result.get(
                "dominant_emotion_th",
                "ความรู้สึกปนปน",
            ),
            "reply_message": analysis_result.get(
                "reply_message",
                "ขอบคุณที่แบ่งปันความรู้สึกนะคะ",
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