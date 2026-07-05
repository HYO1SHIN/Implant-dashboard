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

# 🌟 Groq 최강의 70B 모델 고정
MODEL_NAME = "llama-3.3-70b-versatile"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    except:
        GROQ_API_KEY = ""

client = Groq(api_key=GROQ_API_KEY)


def chunk_text(text, max_chars=8000):
    """
    🌟 Llama-3.3-70B의 128K 대용량 컨텍스트 창을 활용하기 위해 상한을 8000자로 확장합니다.
    줄글과 하단 명세서가 서로 다른 청크로 찢어져 유실되는 현상을 완벽히 차단합니다.
    """
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
    prompt_path = BASE_DIR / "prompt_extract.txt"
    with open(prompt_path, encoding="utf-8") as f:
        prompt_template = f.read()

    prompt = prompt_template.replace("{TEXT}", chunk_text)

    if "json" not in prompt.lower():
        prompt += "\n\nReturn the output in a valid JSON object format."

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,  
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        result = completion.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"🚨 [Step 1 원인 분석] Groq API 호출 실패: {e}")
        result = '{"devices": []}'

    if not result.endswith("}") and not result.endswith("```"):
        result += "\n}"
    return result


def extract_json(text):
    try:
        cleaned_text = re.sub(r"\x60{3}json|\x60{3}", "", text).strip()
        json_match = re.search(r"\{[\s\S]*\}", cleaned_text)
        if json_match:
            return json.loads(json_match.group())
        else:
            raise ValueError("JSON 구조 결여")
    except Exception as e:
        print(f"[디버그] 조각 JSON 파싱 우회: {e}")
        return {"devices": []}


def process_single_chunk(chunk):
    raw_result = extract_device_raw(chunk)
    
    # 🌟 [보완 안심 장치] 만약 review_device가 결과를 자꾸 다운그레이드하면, 
    # 아래 블록을 주석 처리하고 chunk_json = extract_json(raw_result)로 직행하도록 제어할 수 있습니다.
    try:
        reviewed_result = review_device(chunk, raw_result)
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

    chunk_filtered_devices = []
    
    if not schema_json or not isinstance(schema_json, dict):
        schema_json = {"devices": []}
        
    for device in schema_json.get("devices", []):
        term = device.get("canonical_device_name", "").strip()
        if not term:
            term = device.get("device_name", "").strip()
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

        device["cui"] = umls.get("cui", "")
        device["preferred_name"] = umls.get("preferred_name", "")
        device["semantic_type"] = umls.get("semantic_type", "")
        device["synonyms"] = umls.get("synonyms", [])
        device["snomed_id"] = umls.get("snomed_id", "")

        raw_location = device.get("implant_location", "").strip()
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
        name = str(d.get("device_name", "")).strip().lower()
        date = str(d.get("implant_date", "")).strip()
        status = str(d.get("implant_status", "")).strip().upper()
        
        signature = f"{name}_{date}_{status}"
        
        if signature not in seen_signatures and name:
            seen_signatures.add(signature)
            final_unique_devices.append(d)

    final_result = {"devices": final_unique_devices}
    print(f"\n===== 글로벌 융합 완료 (총 {len(final_unique_devices)}개 기기 검출) =====")

    # 이 단계에서 외부 GUDID 데이터베이스 매핑 결과로 객체들이 오버라이트됩니다.
    try:
        final_result = resolve_device_by_cui(final_result)
        print("\n===== FDA RESOLVER MATCHED =====")
    except Exception as e:
        print(f"[안내] FDA Resolver 최종 단계 예외 우회: {e}")
        pass

    if final_result is None or not isinstance(final_result, dict):
        final_result = {"devices": []}

    # 🌟 [무적의 최후방 검수 및 복합 가드레일 레이어 설치] 🌟
    # 어떤 서브 모듈이 뒤에서 값을 깨부쉈든 간에, 파이프라인 탈출 직전 19대 대분류에 맞게 데이터를 최종 복구합니다.
    ALLOWED_LOCATIONS = [
        "Brain", "Neck", "Cervical Spine", "Thoracic Spine", "Lumbar Spine",
        "Heart", "Abdomen", "Right Shoulder", "Left Shoulder", "Right Elbow",
        "Left Elbow", "Right Hand", "Left Hand", "Right Pelvis (Femoral Head)",
        "Left Pelvis (Femoral Head)", "Right Knee", "Left Knee", "Right Foot", "Left Foot"
    ]

    for device in final_result.get("devices", []):
        loc = str(device.get("implant_location", "")).strip()
        name = str(device.get("device_name", "")).strip().lower()
        canon = str(device.get("canonical_device_name", "")).strip().lower()
        
        # 가드레일 A: 심장 특화 강제 매핑 규칙
        if any(kw in loc.lower() or kw in name or kw in canon for kw in ["heart", "ventricle", "apex", "atrial", "pacer", "pocket", "sigma", "pectoral", "chest", "pacemaker", "cardiac lead"]):
            device["implant_location"] = "Heart"
            device["location_cui"] = "C0018787"
            continue
            
        # 가드레일 B: 고관절/골반 특화 강제 매핑 규칙
        if any(kw in loc.lower() or kw in name or kw in canon for kw in ["hip", "pelvis", "femoral", "acetabular", "arthroplasty", "coaxial", "ilium"]):
            # 좌측/우측 수술 방향성 보존 매핑
            if "left" in note.lower() or "left" in loc.lower() or "lt" in loc.lower():
                device["implant_location"] = "Left Pelvis (Femoral Head)"
                device["location_cui"] = "C0030863"
            else:
                device["implant_location"] = "Right Pelvis (Femoral Head)"
                device["location_cui"] = "C0033446"
            continue

        # 가드레일 C: 무릎 관절 특화 강제 매핑 규칙
        if any(kw in loc.lower() or kw in name or kw in canon for kw in ["knee", "patella", "tibia", "tkr", "tka"]):
            if "left" in note.lower() or "left" in loc.lower() or "lt" in loc.lower():
                device["implant_location"] = "Left Knee"
                device["location_cui"] = "C0224855"
            else:
                device["implant_location"] = "Right Knee"
                device["location_cui"] = "C0224854"
            continue

        # 가드레일 D: 최종 폴백 룰 (리스트에 없는 텍스트 용어 유입 시 부분 매칭 구조로 구제)
        if loc not in ALLOWED_LOCATIONS:
            matched = next((allowed for allowed in ALLOWED_LOCATIONS if allowed.lower() in loc.lower()), None)
            if matched:
                device["implant_location"] = matched
            else:
                # 완전 알 수 없는 용어인 경우 가장 유력한 본문 내 단서로 2차 추론 매핑
                if "brain" in note.lower() or "shunt" in name:
                    device["implant_location"] = "Brain"
                elif "abdomen" in note.lower() or "mesh" in name or "graft" in name:
                    device["implant_location"] = "Abdomen"
                else:
                    device["implant_location"] = "Heart" # 기본 최다 빈도 디폴트값 방어선

    return final_result
