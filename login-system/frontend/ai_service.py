import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)


import os

API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel('models/gemini-3.5-flash')

@app.route('/analyze', methods=['POST'])
def analyze_diary():
    data = request.json
    diary_text = data.get('text', '')

    if not diary_text:
        return jsonify({'error': 'กรุณากรอกข้อความไดอารี่'}), 400

    try:

        prompt = f"""
        คุณคือ AI ผู้เชี่ยวชาญด้านจิตวิทยา ให้วิเคราะห์ข้อความบันทึกประจำวันต่อไปนี้ตามทฤษฎี Plutchik's Wheel of Emotions:
        ข้อความผู้ใช้: "{diary_text}"

        โปรดตอบกลับในรูปแบบ JSON โครงสร้างดังนี้เท่านั้น (ห้ามมีข้อความอื่นนอกเหนือจาก JSON):
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
            "detected_dyad": "ระบุอารมณ์ผสม เช่น Remorse (Sadness+Disgust), Love (Joy+Trust) หรือ None",
            "dominant_emotion_th": "ชื่ออารมณ์หลักที่เด่นที่สุดในภาษาไทย",
            "reply_message": "ข้อความตอบกลับปลอบใจหรือร่วมยินดี ภาษาไทย นุ่มนวล อบอุ่น ฮีลใจ"
        }}

        หมายเหตุ: คะแนน primary_emotions แต่ละช่องให้ใส่เป็นเลขทศนิยมช่วง 0.0 ถึง 1.0 ตามระดับความเข้มข้นที่วิเคราะห์ได้จากข้อความ
        """

        response = gemini_model.generate_content(prompt)
        
  
        raw_text = response.text.strip().replace("```json", "").replace("```", "")
        analysis_result = json.loads(raw_text)

        print("📊 ผลการวิเคราะห์ 8 อารมณ์:\n", json.dumps(analysis_result, ensure_ascii=False, indent=2))

        return jsonify(analysis_result)

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)