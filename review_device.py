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
Your task is to review, refine, and aggressively clean the extracted device list based on the original clinical note.

[CRITICAL MERGING & DEDUPLICATION RULE]
- A clinical note often mentions a generic device name in the text and later specifies its exact brand/model/serial number in a settings block.
- You MUST combine these into a SINGLE JSON object representing that specific device. 
- NEVER create separate JSON objects for the generic term and the specific model name. Merge them!

[CRITICAL EXCLUSION & DELETION RULES - DO NOT EXTRACT]
You MUST act as a strict gatekeeper. If any device in the "Extracted Devices to Review" list falls into the following temporary, disposable, procedural, surgical-maintenance, or short-term medical supplies, you MUST COMPLETELY DELETE and REMOVE it from the final JSON array. Focus ONLY on long-term indwelling or permanent implants. Completely drop and ignore:
1. Short-term Drainage & Fluids: Any temporary line, tube, or catheter inserted for short-term fluid, air, or urine management (e.g., chest tubes, Blake drains, Foley catheters, rectal tubes, triple lumen catheters, arterial catheters/lines).
2. Intraoperative Tools & Access Equipment: Disposable devices used to perform the procedure but completely removed before completion (e.g., needles, sheaths, trocars, guide wires, introducers, surgical tools, temporary pacing wires).
3. Wound Closure & Vascular Hemostasis Devices: Materials used solely to close skin, fascia, or vessels, or to achieve immediate mechanical hemostasis (e.g., sutures, surgical silk, staples, clips, or active closure devices like Perclose, ProGlide, Angio-Seal).
4. Absorbable Topical Agents & Sponges: Bio-absorbable materials placed intraoperatively to control bleeding that naturally degrade (e.g., Gelfoam, Surgicel, bone wax, gelatin sponges).
5. Planned future devices or family history devices.

[STRICT DATE FORMATTING RULE]
- You MUST strictly normalize and convert ALL "implant_date" values into ISO format: YYYY-MM-DD (e.g., 2007-08-21).
- If the original clinical note or the extracted JSON contains dates in MM/DD/YYYY (e.g., 08/21/2007) or YY/MM/DD (e.g., 03/08/28), you MUST actively recalculate and convert them into the standard YYYY-MM-DD format before outputting. 
- NEVER copy non-standard raw date formats directly from the note. Transform them!

[STRICT IMPLANT LOCATION RULE]
You MUST choose EXACTLY ONE literal string for "implant_location" from this list. Do not alter the text, do not output sub-structures:
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

* Clinical Mapping Guideline: Any cardiac device component (pacemaker, ICD, pulse generator, lead, screw, RV apex placement) MUST be mapped to "Heart".

Rules for Fields:
- device_name: Detailed product name including model/serial numbers.
- canonical_device_name: Normalized generic concept.
- implant_date: MUST be strictly normalized to YYYY-MM-DD.
- implant_status: "CURRENT" or "NOT CURRENT".

IMPORTANT: Return a valid JSON OBJECT only. No conversational commentary, no markdown backticks.
{{
  "devices": [
    {{
      "device_name": "",
      "canonical_device_name": "",
      "device_size": "",
      "implant_location": "",
      "implant_date": "YYYY-MM-DD",
      "implant_status": "",
      "supporting_text": ""
    }}
  ]
}}

Clinical Note:
{note}

Extracted Devices to Review (Filter out temporary items and STRICTOR DATE FORMAT TO YYYY-MM-DD):
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
