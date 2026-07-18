import json
import re
import os
from pathlib import Path
import streamlit as st
from groq import Groq  

from schema_loader import apply_schema
from umls_resolver import search_umls
from device_resolver import resolve_device_by_cui

BASE_DIR = Path(__file__).parent
ALLOWED_SEMANTIC_TYPES = ["Medical Device", "Manufactured Object", "Drug Delivery Device"]

MODEL_NAME = "llama-3.3-70b-versatile"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    except:
        GROQ_API_KEY = ""

client = Groq(api_key=GROQ_API_KEY)


def chunk_text(text, max_chars=8000):
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
        st.error(f"Groq API 호출 실패: {e}")
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
        print(f"조각 JSON 파싱 우회: {e}")
        return {"devices": []}


def process_single_chunk(chunk):
    raw_result = extract_device_raw(chunk)
    chunk_json = extract_json(raw_result)

    try:
        schema_json = apply_schema(chunk_json)
    except:
        schema_json = chunk_json

    chunk_filtered_devices = []
    
    if not schema_json or not isinstance(schema_json, dict):
        schema_json = {"devices": []}
        
    for device in schema_json.get("devices", []):
        orig_device_name = str(device.get("device_name") or "").strip()
        orig_canonical_name = str(device.get("canonical_device_name") or "").strip()
        orig_supporting_text = str(device.get("supporting_text") or "").strip()
        
        if not orig_device_name and not orig_canonical_name:
            continue
            
        term = orig_canonical_name if orig_canonical_name else orig_device_name

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
        device["preferred_name"] = orig_canonical_name if orig_canonical_name else orig_device_name
        device["semantic_type"] = umls.get("semantic_type", "")
        device["synonyms"] = umls.get("synonyms", [])
        device["snomed_id"] = umls.get("snomed_id", "")
        
        device["device_name"] = orig_device_name
        device["canonical_device_name"] = orig_canonical_name if orig_canonical_name else orig_device_name
        device["supporting_text"] = orig_supporting_text

        raw_location = str(device.get("implant_location") or "").strip()
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
    print("\n대용량 분산 분할 처리 파이프라인 가동.")
    
    chunks = chunk_text(note)
    master_devices_pool = []
    
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        print(f"단락 조각 분석 중... ({i+1}/{len(chunks)})")
        chunk_results = process_single_chunk(chunk)
        master_devices_pool.extend(chunk_results)

    final_unique_devices = []
    seen_signatures = set()

    for d in master_devices_pool:
        name = str(d.get("device_name") or "").strip().lower()
        date = str(d.get("implant_date") or "").strip()
        status = str(d.get("implant_status") or "").strip().upper()
        
        text_snippet = str(d.get("supporting_text") or "").strip()[:20].lower()
        signature = f"{name}_{date}_{status}_{text_snippet}"
        
        if signature not in seen_signatures and name:
            seen_signatures.add(signature)
            final_unique_devices.append(d)

    final_result = {"devices": final_unique_devices}
    print(f"\n===== 글로벌 융합 완료 (총 {len(final_unique_devices)}개 기기 검출) =====")

    try:
        final_result = resolve_device_by_cui(final_result)
        print("\n===== FDA RESOLVER MATCHED =====")
    except Exception as e:
        print(f"[안내] FDA Resolver 최종 단계 예외 우회: {e}")
        pass

    if final_result is None or not isinstance(final_result, dict):
        final_result = {"devices": []}

    ALLOWED_LOCATIONS = [
        "Brain", "Neck", "Cervical Spine", "Thoracic Spine", "Lumbar Spine",
        "Heart", "Abdomen", "Right Shoulder", "Left Shoulder", "Right Elbow",
        "Left Elbow", "Right Hand", "Left Hand", "Right Pelvis (Femoral Head)",
        "Left Pelvis (Femoral Head)", "Right Knee", "Left Knee", "Right Foot", "Left Foot"
    ]

    note_lower = str(note or "").lower()

    for device in final_result.get("devices", []):
        loc = str(device.get("implant_location") or "").strip()
        name = str(device.get("device_name") or "").strip().lower()
        canon = str(device.get("canonical_device_name") or "").strip().lower()
        pref = str(device.get("preferred_name") or "").strip().lower()
        
        combined_text = f"{loc.lower()} {name} {canon} {pref}"
        
        is_cardiac_context = any(kw in note_lower for kw in ["fontan", "glenn", "shunt", "embolization", "coil", "tricuspid", "cardiac", "septal", "fenestration"])
        
        if any(kw in combined_text for kw in ["heart", "ventricle", "apex", "atrial", "pacer", "pocket", "sigma", "pectoral", "chest", "pacemaker", "cardiac lead", "conduit", "fenestration", "coil"]):
            device["implant_location"] = "Heart"
            device["location_cui"] = "C0018787"
            
            if "brain" in combined_text or "central nervous system" in combined_text:
                device["preferred_name"] = "Vascular Shunt"
                device["cui"] = "C0011667"
            continue
            
        if "shunt" in combined_text:
            if is_cardiac_context and "brain" not in combined_text:
                device["implant_location"] = "Heart"
                device["location_cui"] = "C0018787"
                device["preferred_name"] = "Vascular Shunt"
                device["cui"] = "C0011667"
            else:
                device["implant_location"] = "Brain"
                device["location_cui"] = "C0018787"
            continue
            
        if any(kw in combined_text for kw in ["hip", "pelvis", "femoral", "acetabular", "arthroplasty", "coaxial", "ilium"]):
            if "left" in note_lower or "left" in loc.lower() or "lt" in loc.lower():
                device["implant_location"] = "Left Pelvis (Femoral Head)"
                device["location_cui"] = "C0030863"
            else:
                device["implant_location"] = "Right Pelvis (Femoral Head)"
                device["location_cui"] = "C0033446"
            continue

        if any(kw in combined_text for kw in ["knee", "patella", "tibia", "tkr", "tka"]):
            if "left" in note_lower or "left" in loc.lower() or "lt" in loc.lower():
                device["implant_location"] = "Left Knee"
                device["location_cui"] = "C0224855"
            else:
                device["implant_location"] = "Right Knee"
                device["location_cui"] = "C0224854"
            continue

        if loc not in ALLOWED_LOCATIONS:
            matched = next((allowed for allowed in ALLOWED_LOCATIONS if allowed.lower() in loc.lower()), None)
            if matched:
                device["implant_location"] = matched
            else:
                if "brain" in note_lower or "shunt" in name:
                    device["implant_location"] = "Brain"
                elif "abdomen" in note_lower or "mesh" in name or "graft" in name:
                    device["implant_location"] = "Abdomen"
                else:
                    device["implant_location"] = "Heart" 

    return final_result
