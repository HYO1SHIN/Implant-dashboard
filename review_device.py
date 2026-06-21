import json
import os
import streamlit as st
from groq import Groq  

# Groq 최강의 70B 모델 고정
MODEL_NAME = "llama-3.3-8b-versatile"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    except:
        GROQ_API_KEY = ""

client = Groq(api_key=GROQ_API_KEY)


def review_device(note, extracted_json):
    if isinstance(extracted_json, str):
        try:
            extracted_json = json.loads(extracted_json)
        except json.JSONDecodeError:
            return {"devices": []}

    # 💥 Llama-3.3-70b의 의학적 추론 능력을 극한으로 끌어올리는 초정밀 프롬프트 아키텍처
    prompt = f"""You are an expert clinical data scientist specializing in implantable medical devices.
Review and refine the extracted device list based on the original clinical note.

[CRITICAL CLINICAL RULES]
1. STRICT PATIENT FOCUS: ONLY extract devices implanted in the PATIENT. 
   - Check the section carefully. Strictly IGNORE any devices belonging to family members (e.g., 'Mother pacemaker', 'Father had pacemaker' -> NEVER EXTRACT).
2. EXPLANTED/REMOVED DEVICES: Do NOT delete historical or removed devices. 
   - If a device was 'removed', 'explanted', or 'replaced', KEEP the device in the list but set its "implant_status" to "NOT CURRENT".
3. CARDIOLOGY ABBREVIATIONS: 
   - 'RCA' stands for 'Right Coronary Artery' (Location). NEVER translate it to 'Root Cause Analysis'.
   - 'LAD' stands for 'Left Anterior Descending artery'.
4. NO FUTURE/PLANNED DEVICES: If a device is only being 'considered' or 'planned' but not yet implanted, do NOT extract it.

Rules for Fields:
- device_name: Exact product or device name from the note.
- canonical_device_name: Normalized generic implant concept.
- implant_status: Must be "CURRENT" (active) or "NOT CURRENT" (removed/explanted).

IMPORTANT:
Always return a JSON OBJECT conforming to this format:
{{
  "devices":[
    {{
      "device_name":"",
      "canonical_device_name":"",
      "device_size":"",
      "implant_location":"",
      "implant_date":"",
      "implant_status":"",
      "supporting_text":""
    }}
  ]
}}

Never return explanations or any text outside the JSON object. Return JSON only.

Clinical Note:
{note}

Extracted Devices:
{json.dumps(extracted_json, indent=2)}
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        text = completion.choices[0].message.content
    except Exception as e:
        st.error(f"🚨 [Reviewer Error] {e}")
        return extracted_json

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return extracted_json

    try:
        result = json.loads(text[start:end+1])

        if isinstance(result, dict) and "devices" not in result and "device_name" in result:
            result = {"devices": [result]}

        if not isinstance(result, dict) or "devices" not in result:
            return extracted_json

        for d in result.get("devices", []):
            if not d.get("device_name") and d.get("canonical_device_name"):
                d["device_name"] = d["canonical_device_name"]

        return result

    except json.JSONDecodeError:
        return extracted_json