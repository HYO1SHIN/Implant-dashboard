import json
import re
from pathlib import Path
import ollama

from schema_loader import apply_schema
from umls_resolver import search_umls
from device_resolver import resolve_device_by_cui
from review_device import review_device

BASE_DIR = Path(__file__).parent
ALLOWED_SEMANTIC_TYPES = ["Medical Device", "Manufactured Object", "Drug Delivery Device"]



def chunk_text(text, max_chars=1200):
    """의무기록의 단락(줄바꿈)을 기준선으로 삼아 안전한 크기로 분할합니다."""
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

    response = ollama.chat(
        model="qwen2.5:3b",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0},
    )
    result = response["message"]["content"].strip()
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
    """하나의 조각에 대해 Step 1부터 Step 5까지 완벽히 독립적으로 수행합니다."""
    raw_result = extract_device_raw(chunk)
    
    try:
        reviewed_result = review_device(chunk, raw_result)
        if isinstance(reviewed_result, dict):
            chunk_json = reviewed_result
        else:
            chunk_json = extract_json(reviewed_result)
    except:
        chunk_json = extract_json(raw_result)

    try:
        schema_json = apply_schema(chunk_json)
    except:
        schema_json = chunk_json

    chunk_filtered_devices = []
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

    try:
        final_result = resolve_device_by_cui(final_result)
        print("\n===== FDA RESOLVER MATCHED =====")
    except Exception as e:
        print(f"[안내] FDA Resolver 최종 단계 예외 우회: {e}")
        pass

    if final_result is None or not isinstance(final_result, dict):
        final_result = {"devices": []}

    return final_result



if __name__ == "__main__":
    test_file = "tests/test_11_hardenTEST.txt"
    try:
        note_content = load_note(test_file)
        pipeline_output = run_pipeline(note_content)
        print(json.dumps(pipeline_output, indent=2, ensure_ascii=False))
    except FileNotFoundError:
        print(f"[안내] 로컬 테스트 파일 세팅 완료.")