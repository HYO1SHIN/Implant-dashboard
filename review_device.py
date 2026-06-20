import json
import ollama

MODEL_NAME = "qwen2.5:3b"


def review_device(note, extracted_json):
    if isinstance(extracted_json, str):
        try:
            extracted_json = json.loads(extracted_json)
        except json.JSONDecodeError:
            return {"devices": []}

    prompt = f"""You are a clinical implantable device reviewer.
Review the extracted implantable devices.
Use BOTH:
1. Original clinical note
2. Extracted device list

Determine whether:
- a device is truly present
- a device was hallucinated
- a device was missed
- implant status is correct
- implant date is correct

If a device was replaced by a newer device of the same type, keep only the currently implanted device.
Do not keep both old device and replacement device.
For replacement events, represent only the active device.

Rules:
1. Remove unsupported devices.
2. Add clearly missing implantable devices.
3. Correct implant status if wrong.
4. Correct implant date if explicit evidence exists.
5. Keep only implantable medical devices.

Do not overwrite device_name.

device_name should preserve the original device name mentioned in the clinical note.

canonical_device_name should contain the normalized device concept.

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

Never return a single device object.
Never return explanations. Return JSON only.

IMPORTANT:
device_name = exact product name mentioned in note
canonical_device_name = normalized generic implant concept (Examples: Gore Excluder -> AAA Stent Graft, Sapien 3 -> Transcatheter Aortic Valve Prosthesis)
Do not replace canonical_device_name with a brand name.

Clinical Note:
{note}

Extracted Devices:
{json.dumps(extracted_json, indent=2)}
"""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
            format="json"  
        )
        text = response["message"]["content"]
    except Exception:
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