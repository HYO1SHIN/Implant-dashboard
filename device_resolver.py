import re
from pathlib import Path
import pandas as pd
from rapidfuzz import fuzz, process

CURRENT_DIR = Path(__file__).parent
RELATIVE_DATA_DIR = CURRENT_DIR / "data"

if RELATIVE_DATA_DIR.exists():
    DATA_DIR = RELATIVE_DATA_DIR
else:
    DATA_DIR = CURRENT_DIR

print(f"Load implant DB chunks from: {DATA_DIR}")

chunk_list = []
for i in range(15):
    chunk_file = DATA_DIR / f"master_part_{i}.csv"
    if chunk_file.exists():
        chunk_df = pd.read_csv(str(chunk_file), dtype=str, low_memory=False)
        chunk_list.append(chunk_df)
    else:
        alt_chunk_file = CURRENT_DIR / f"master_part_{i}.csv"
        if alt_chunk_file.exists():
            chunk_df = pd.read_csv(str(alt_chunk_file), dtype=str, low_memory=False)
            chunk_list.append(chunk_df)

if chunk_list:
    device_db = pd.concat(chunk_list, ignore_index=True)
    print(f"조각 병합 성공! 총 복원 행(Rows): {len(device_db)}")
else:
    ORIGINAL_CSV = DATA_DIR / "implantable_device_master_cui.csv"
    if ORIGINAL_CSV.exists():
        device_db = pd.read_csv(str(ORIGINAL_CSV), dtype=str, low_memory=False)
        print(f"원본 파일 직접 로드 성공. 행(Rows): {len(device_db)}")
    else:
        raise FileNotFoundError(
            f"데이터 조각(master_part_*.csv) 또는 원본 파일이 경로에 존재하지 않습니다: {DATA_DIR}"
        )


def clean_text(text):
    if pd.isna(text):
        return ""
    return str(text).lower().strip()


target_cols = ["productCodeName", "brandName", "normalized_device", "MRISafetyStatus", "companyName"]
for col in target_cols:
    if col in device_db.columns:
        device_db[col] = device_db[col].fillna("").astype(str).str.strip()
    else:
        device_db[col] = ""

device_db["combined_anchor"] = (
    device_db["brandName"] + " " +
    device_db["productCodeName"] + " " +
    device_db["normalized_device"] + " " +
    device_db["companyName"]
).str.lower().str.replace(r'[^a-zA-Z0-9가-힣\s]', ' ', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip()

def calculate_mri_priority(status):
    st_lower = str(status).lower()
    if not st_lower or "labeling does not" in st_lower or "unknown" in st_lower:
        return 1
    return 0

device_db["mri_priority"] = device_db["MRISafetyStatus"].apply(calculate_mri_priority)

device_db = device_db.sort_values(by=["combined_anchor", "mri_priority"])
valid_db = device_db[device_db["combined_anchor"] != ""].drop_duplicates(subset=["combined_anchor"], keep="first")

compound_lookup = dict(zip(valid_db["combined_anchor"], valid_db.to_dict(orient="records")))
compound_list = list(compound_lookup.keys())


def fill_device_info(device, row, method, score):
    device["PrimaryDI"] = row.get("PrimaryDI", "")
    device["submissionNumber"] = row.get("submissionNumber", "")
    device["manufacturer"] = row.get("companyName", "")
    device["brand_name"] = row.get("brandName", "")
    device["device_description"] = row.get("productCodeName", "")
    device["MRISafetyStatus"] = row.get("MRISafetyStatus", "Unknown")

    device["resolve_method"] = method
    device["similarity_score"] = round(float(score), 1)


def resolve_device_by_product(device_json):
    if device_json is None or not isinstance(device_json, dict):
        return {"devices": []}

    devices = device_json.get("devices", [])

    for device in devices:
        d_name = clean_text(device.get("device_name", ""))
        c_name = clean_text(device.get("canonical_device_name", ""))
        p_name = clean_text(device.get("preferred_name", ""))
        s_text = clean_text(device.get("supporting_text", ""))
        
        search_query = f"{d_name} {c_name} {p_name} {s_text}".strip()
        if not search_query or not compound_list:
            device["resolve_method"] = "UNRESOLVED"
            device["similarity_score"] = 0.0
            continue

        results = process.extract(search_query, compound_list, scorer=fuzz.token_set_ratio, limit=5)
        
        if results:
            valid_matches = [r for r in results if r[1] >= 55]
            
            if valid_matches:
                best_row = None
                best_raw_score = 0
                max_effective_score = -1
                
                for matched_anchor, score, _ in valid_matches:
                    row = compound_lookup.get(matched_anchor)
                    mri_bonus = 15 if row.get("mri_priority") == 0 else 0
                    effective_score = score + mri_bonus
                    
                    if effective_score > max_effective_score:
                        max_effective_score = effective_score
                        best_raw_score = score
                        best_row = row
                
                if best_row is not None:
                    fill_device_info(device, best_row, "COMPOUND_RERANKED", best_raw_score)
                    continue

        device["resolve_method"] = "UNRESOLVED"
        device["similarity_score"] = round(float(results[0][1]), 1) if results else 0.0

    for device in devices:
        loc = str(device.get("implant_location", "")).strip().lower()
        name = str(device.get("device_name", "")).strip().lower()
        canon = str(device.get("canonical_device_name", "")).strip().lower()
        pref = str(device.get("preferred_name", "")).strip().lower()
        
        combined_loc_text = f"{loc} {name} {canon} {pref}"
        
        if any(kw in combined_loc_text for kw in ["heart", "ventricle", "apex", "atrial", "pacer", "pocket", "sigma", "pectoral", "chest", "pacemaker", "cardiac lead", "conduit", "fenestration", "contegra"]):
            device["implant_location"] = "Heart"
            continue
            
        if any(kw in combined_loc_text for kw in ["hip", "pelvis", "femoral", "acetabular", "arthroplasty", "coaxial", "ilium", "screw", "arthrex", "fixation"]):
            if "left" in combined_loc_text or "lt" in combined_loc_text:
                device["implant_location"] = "Left Pelvis (Femoral Head)"
            else:
                device["implant_location"] = "Right Pelvis (Femoral Head)"
            continue

        if any(kw in combined_loc_text for kw in ["knee", "patella", "tibia", "tkr", "tka"]):
            if "left" in combined_loc_text or "lt" in combined_loc_text:
                device["implant_location"] = "Left Knee"
            else:
                device["implant_location"] = "Right Knee"
            continue

        if any(kw in combined_loc_text for kw in ["brain", "hearing", "active", "middle ear", "cochlear", "shunt", "aesculap"]):
            device["implant_location"] = "Brain"
            continue

        if any(kw in combined_loc_text for kw in ["advance", "mesh", "biodesign", "abdomen", "urinary"]):
            device["implant_location"] = "Abdomen"
            continue

    return device_json


resolve_device_by_cui = resolve_device_by_product
