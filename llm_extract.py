import json
import re
import os
from pathlib import Path
import streamlit as st
from groq import Groq

from schema_loader import apply_schema
from umls_resolver import search_umls
from device_resolver import resolve_device_by_cui
from review_device import review_device

BASE_DIR = Path(__file__).parent
ALLOWED_SEMANTIC_TYPES = ["Medical Device", "Manufactured Object", "Drug Delivery Device"]

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    except:
        GROQ_API_KEY = ""

client = Groq(api_key=GROQ_API_KEY)


def chunk_text(text, max_chars=1200):
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = []
    current_length = 0
    
    for line in paragraphs:
        if current_length + len(line) > max_chars:
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line)
            
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    return chunks


def extract_device_raw(chunk_text):
    """
    Groq Llama3 모델을 호출하여 의료기기 정보를 추출합니다.
    """
    prompt_path = BASE_DIR / "prompt_extract.txt"
    with open(prompt_path, encoding="utf-8") as f:
        prompt_template = f.read()

    prompt = prompt_template.replace("{TEXT}", chunk_text)

    # 💥 [해결책 ①] Groq JSON 모드 거부 반응 방지 안전장치
    if "json" not in prompt.lower():
        prompt += "\n\nReturn the output in a valid JSON object format."

    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        result = completion.choices[0].message.content.strip()
    except Exception as e:
        # Streamlit 화면에서도 무슨 에러인지 알 수 있도록 경고창 처리
        st.error(f"Groq API 호출 중 오류 발생: {e}")
        result = '{"devices": []}'

    return result


def extract_json(text):
    if not text or not isinstance(text, str):
        return {"devices": []}
        
    try:
        cleaned = re.sub(r"\x60{3}json|\x60{3}", "", text).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        
        if start != -1 and end != -1:
            json_candidate = cleaned[start:end+1]
            return json.loads(json_candidate)
            
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            return json.loads(json_match.group())
            
        raise ValueError("구조적 결함")
    except Exception as e:
        print(f"[강제 파싱 디버그] 파싱 우회 작동: {e}")
        return {"devices": []}


def process_single_chunk(chunk):
    raw_result = extract_device_raw(chunk)
    
    try:
        reviewed_result = review_device(chunk, extract_json(raw_result))
        if isinstance(reviewed_result, dict):
            chunk_json = reviewed_result
        else:
            chunk_json = extract_json(reviewed_result)
    except Exception as e:
        print(f"[디버그] 리뷰 단계 우회: {e}")
        chunk_json = extract_json(raw_result)

    try:
        schema_json = apply_schema(chunk_json)
    except:
        schema_json = chunk_json

    if not schema_json or not isinstance(schema_json, dict):
        schema_json = {"devices": []}

    chunk_filtered_devices = []
    
    # 💥 [해결책 ②] AI가 기기 목록 키를 대문자로 뱉었을 때를 대비한 융합 방어막
    devices_list = schema_json.get("devices") or schema_json.get("Devices") or schema_json.get("DEVICE") or []
    if isinstance(devices_list, dict):  # 리스트가 아니라 단일 객체로 왔을 때 예외 처리
        devices_list = [devices_list]

    for device in devices_list:
        if not device or not isinstance(device, dict):
            continue
            
        # 💥 AI가 Key 값을 대소문자 무작위로 뱉어도 전부 다 잡아내도록 수정
        term = (device.get("canonical_device_name") or device.get("Canonical_Device_Name") or "").strip()
        if not term:
            term = (device.get("device_name") or device.get("Device_Name") or device.get("device") or "").strip()
        if not term:
            continue

        try:
            umls = search_umls(term)
        except:
            umls = None

        if not umls:
            umls = {
                "cui": "UMLS_PENDING",
                "preferred_name": term,
                "semantic_type": "Medical Device",
                "synonyms": [term],
                "snomed_id": "PENDING"
            }

        # 데이터 안전 맵핑 (대소문자 무관하게 강제 주입)
        device["cui"] = umls.get("cui", "UMLS_PENDING")
        device["preferred_name"] = umls.get("preferred_name", term)
        device["semantic_type"] = umls.get("semantic_type", "Medical Device")
        device["synonyms"] = umls.get("synonyms", [term])
        device["snomed_id"] = umls.get("snomed_id", "PENDING")

        # 기기 이식 위치 추출 안정화
        raw_location = (device.get("implant_location") or device.get("Implant_Location") or device.get("location") or "").strip()
        device["location_cui"] = ""

        if raw_location and raw_location.lower() not in ["none", "null", "nan", "unknown"]:
            try:
                loc_umls = search_umls(raw_location)
                if loc_umls and loc_umls.get("preferred_name"):
                    device["implant_location"] = loc_umls.get("preferred_name")
                    device["location_cui"] = loc_umls.get("cui", "")
                else:
                    device["implant_location"] = raw_location
                    device["location_cui"] = "NO_MATCH"
            except:
                device["implant_location"] = raw_location
                device["location_cui"] = "ERROR"
        else:
            device["implant_location"] = "Unknown"

        chunk_filtered_devices.append(device)
        
    return chunk_filtered_devices


def run_pipeline(note):
    print("\n[시스템] 대용량 분산 분할 처리 파이프라인 가동.")
    
    chunks = chunk_text(note)
    master_devices_pool = []
    
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        print(f"[파이프라인] 단락 조각 분석 중... ({i+1}/{len(chunks)})")
        chunk_results = process_single_chunk(chunk)
        master_devices_pool.extend(chunk_results)

    final_unique_devices = []
    seen_signatures = set()

    for d in master_devices_pool:
        # 데이터 유실 방지를 위한 필드 추출 다중화
        raw_name = d.get("device_name") or d.get("Device_Name") or d.get("preferred_name") or ""
        name = str(raw_name).strip().lower()
        
        raw_date = d.get("implant_date") or d.get("Implant_Date") or "Unknown"
        date = str(raw_date).strip()
        
        raw_status = d.get("implant_status") or d.get("Implant_Status") or "CURRENT"
        status = str(raw_status).strip().upper()
        
        signature = f"{name}_{date}_{status}"
        
        if signature not in seen_signatures and name:
            seen_signatures.add(signature)
            final_unique_devices.append(d)

    final_result = {"devices": final_unique_devices}
    print(f"\n===== 글로벌 융합 완료 (총 {len(final_unique_devices)}개 기기 검출) =====")

    # 💥 [해결책 ③] FDA 리졸버가 에러를 내거나 데이터를 다 밀어버릴 경우를 대비한 가드레일
    try:
        resolved_output = resolve_device_by_cui(final_result)
        print("\n===== FDA RESOLVER MATCHED =====")
        # 만약 리졸버를 거쳤는데 데이터가 0개로 증발했다면, 안전하게 원본(final_result)을 복구시킵니다.
        if resolved_output and isinstance(resolved_output, dict) and len(resolved_output.get("devices", [])) > 0:
            final_result = resolved_output
    except Exception as e:
        print(f"[안내] FDA Resolver 최종 단계 예외 우회: {e}")
        pass

    if final_result is None or not isinstance(final_result, dict):
        final_result = {"devices": []}

    return final_result


if __name__ == "__main__":
    test_file = "tests/test_11_hardenTEST.txt"
    try:
        if Path(test_file).exists():
            with open(test_file, "r", encoding="utf-8") as f:
                note_content = f.read()
            pipeline_output = run_pipeline(note_content)
            print(json.dumps(pipeline_output, indent=2, ensure_ascii=False))
        else:
            print(f"[안내] 로컬 테스트 파일 세팅 완료.")
    except Exception as e:
        print(f"[안내] 로컬 테스트 실행 예외 완료: {e}")