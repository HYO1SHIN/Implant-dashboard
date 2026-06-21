import json
import os
import streamlit as st
from groq import Groq  # ◀ ollama 대신 외부 서버 AI 클라이언트를 도입합니다.

# qwen2.5:3b보다 훨씬 의학적 추론 능력이 뛰어나며 JSON 출력을 엄격히 보장하는 llama3 모델을 매핑합니다.
MODEL_NAME = "llama3-8b-8192"

# -------------------------------------------------------------
# [서버 배포 가드레일] 환경변수 및 Streamlit Secrets에서 API Key 로드
# -------------------------------------------------------------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    except:
        GROQ_API_KEY = ""

# Groq 클라이언트 안전 초기화
client = Groq(api_key=GROQ_API_KEY)


def review_device(note, extracted_json):
    if isinstance(extracted_json, str):
        try:
            extracted_json = json.loads(extracted_json)
        except json.JSONDecodeError:
            return {"devices": []}

    # 선생님의 정교한 임상 리뷰용 프롬프트 아키텍처를 원본 그대로 유지합니다.
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
        # [패치 완료] 로컬 CPU(ollama) 대신 웹 서버 인프라(Groq)를 안전하게 연결합니다.
        # response_format을 통해 AI 공장이 무조건 올바른 JSON만 반환하도록 강제합니다.
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        text = completion.choices[0].message.content
    except Exception:
        # 통신 에러 등 예외 발생 시 원본 데이터를 안전하게 보존하여 밀어주는 선생님의 방어가드레일
        return extracted_json

    # -------------------------------------------------------------
    # 아래의 모든 문자열 클렌징, JSON 파싱 및 구조 보정(Dict 랩핑) 로직은
    # 현재 완벽하게 작동 중인 선생님의 원본 코드를 100% 그대로 보존했습니다.
    # -------------------------------------------------------------
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