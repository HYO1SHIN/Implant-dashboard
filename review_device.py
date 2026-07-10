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

[CRITICAL EXCLUSION & DELETION RULES - GATEKEEPER ROLE]

You MUST act as a strict gatekeeper. If any device in the "Extracted Devices to Review" list falls into the following temporary, disposable, procedural, or short-term access categories, you MUST COMPLETELY DELETE and REMOVE it from the final JSON array. Do NOT retain them.



1. ABSOLUTELY NO Short-term Drainage, Catheters & Lines:

   - Completely REMOVE temporary lines or tubes meant for short-term fluid/blood management or monitoring (e.g., triple lumen catheters, central venous lines, arterial catheters/lines, brachial/femoral catheters, Foley catheters, urinary lines, chest tubes, Blake drains, rectal tubes).

2. ABSOLUTELY NO Intraoperative Access Equipment:

   - Completely REMOVE surgical access or delivery tools (e.g., needles, sheaths, trocars, guide wires, introducers, temporary pacing wires/leads pulled post-op).

3. ABSOLUTELY NO Wound Closure & Vascular Sealing Devices:

   - Completely REMOVE items used solely to close blood vessels or skin (e.g., Perclose, ProGlide, Angio-Seal, Mynx, sutures, clips, staples, surgical silk).

4. ABSOLUTELY NO Topical Hemostatic Agents & Sponges:

   - Completely REMOVE bio-absorbable materials used to control surgical bleeding (e.g., Gelfoam, Surgicel, gelatin sponge, bone wax).



[CRITICAL CLINICAL & MERGING RULES]

1. STRICT PATIENT FOCUS: ONLY extract devices implanted in the PATIENT. Ignore family history.

2. EXPLANTED/REMOVED DEVICES: Keep historical or removed devices in the list, but set "implant_status" to "NOT CURRENT".

3. NO FUTURE/PLANNED DEVICES: Do NOT extract planned or considered procedures.

4. STRICT DEVICE CONSOLIDATION: Always keep generic text terms and specific serial/model specifications merged into a single device object.



[STRICT DATE FORMATTING RULE]

- You MUST strictly format ALL "implant_date" values into the ISO format: YYYY-MM-DD (e.g., 2007-08-21).

- If the original clinical note or the extracted JSON contains dates in MM/DD/YYYY (e.g., 08/21/2007) or YY/MM/DD (e.g., 03/08/28), you MUST actively recalculate and convert them into the standard YYYY-MM-DD format before outputting.



[STRICT IMPLANT LOCATION RULE]

For "implant_location", you MUST enforce the value to match EXACTLY ONE of the following 19 regions:

- Brain, Neck, Cervical Spine, Thoracic Spine, Lumbar Spine, Heart, Abdomen, Right Shoulder, Left Shoulder, Right Elbow, Left Elbow, Right Hand, Left Hand, Right Pelvis (Femoral Head), Left Pelvis (Femoral Head), Right Knee, Left Knee, Right Foot, Left Foot.

* Rule: Any cardiac/pacemaker components MUST remain mapped to "Heart".



Rules for Fields:

- device_name: Detailed product name including model/serial numbers.

- canonical_device_name: Normalized generic concept.

- implant_date: MUST be strictly normalized to YYYY-MM-DD.

- implant_status: "CURRENT" or "NOT CURRENT".



IMPORTANT: Return a valid JSON OBJECT only. No conversational commentary, no markdown backticks.

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
