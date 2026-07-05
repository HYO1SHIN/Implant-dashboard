import json
import os
import streamlit as st
from groq import Groq  

MODEL_NAME = "llama-3.3-70b-versatile"

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

    prompt = f"""You are an expert clinical data scientist specializing in implantable medical devices.
Review and refine the extracted device list based on the original clinical note to maximize compliance and accuracy.

[CRITICAL CLINICAL & MERGING RULES]
1. STRICT PATIENT FOCUS: ONLY extract devices implanted in the PATIENT. Strictly IGNORE family history.
2. EXPLANTED/REMOVED DEVICES: Do NOT delete historical or removed devices. Set "implant_status" to "NOT CURRENT".
3. NO FUTURE/PLANNED DEVICES: Do NOT extract planned or considered procedures.
4. STRICT DEVICE CONSOLIDATION: Generic names in the text (e.g., "permanent pacemaker") and specific specs in the settings block (e.g., "Pulse Generator: Sigma, model #: 12345") represent the SAME device instance. 
   - You MUST keep them MERGED into a single object. 
   - NEVER split a consolidated device object back into separate generic and specific entries.

[STRICT IMPLANT LOCATION RULE]
For "implant_location", you MUST ensure the value belongs to EXACTLY ONE of the following 19 predefined anatomical regions. Do NOT let it hallucinate raw text terms like 'pectoral pocket' or 'lateral region':
- Brain
- Neck
- Cervical Spine
- Thoracic Spine
- Lumbar Spine
- Heart
- Abdomen
- Right Shoulder
- Left Shoulder
- Right Elbow
- Left Elbow
- Right Hand
- Left Hand
- Right Pelvis (Femoral Head)
- Left Pelvis (Femoral Head)
- Right Knee
- Left Knee
- Right Foot
- Left Foot

* Rule: Any cardiac/pacemaker components (lead, pulse generator, pocket, apex) MUST remain mapped to "Heart".

Rules for Fields:
- device_name: Detailed product name including model/serial numbers.
- canonical_device_name: Normalized generic concept (e.g., Cardiac Pacemaker, Pacemaker Lead).
- implant_status: "CURRENT" or "NOT CURRENT".

IMPORTANT: Always return a JSON OBJECT conforming to this format. No conversational text.
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

Clinical Note:
{note}

Extracted Devices to Review:
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
