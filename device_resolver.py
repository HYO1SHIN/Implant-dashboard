from pathlib import Path
import pandas as pd
from rapidfuzz import fuzz, process


LOCAL_DATA_DIR = Path(r"C:\Users\신효원\Desktop\생성형AI수업\DATA\implant_dashboard\data")
RELATIVE_DATA_DIR = Path(__file__).parent / "data"
CURRENT_DIR = Path(__file__).parent

if LOCAL_DATA_DIR.exists():
    DATA_DIR = LOCAL_DATA_DIR
elif RELATIVE_DATA_DIR.exists():
    DATA_DIR = RELATIVE_DATA_DIR
else:
    DATA_DIR = CURRENT_DIR

print(f"🚀 Load implant DB chunks from: {DATA_DIR}")

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
    print(f"✅ 조각 병합 성공! 총 복원 행(Rows): {len(device_db)}")
else:
    ORIGINAL_CSV = DATA_DIR / "implantable_device_master_cui.csv"
    if ORIGINAL_CSV.exists():
        device_db = pd.read_csv(str(ORIGINAL_CSV), dtype=str, low_memory=False)
        print(f"✅ 원본 파일 직접 로드 성공! 행(Rows): {len(device_db)}")
    else:
        raise FileNotFoundError(
            f"데이터 조각(master_part_*.csv) 또는 원본 파일이 경로에 존재하지 않습니다: {DATA_DIR}"
        )


def clean_text(text):
    if pd.isna(text):
        return ""
    return str(text).lower().strip()


target_cols = ["productCodeName", "brandName", "normalized_device", "MRISafetyStatus"]
for col in target_cols:
    if col in device_db.columns:
        device_db[col] = device_db[col].fillna("").astype(str).str.strip()


def create_lookup_and_list(df, col_name):
    if col_name in df.columns:
        valid_df = df[df[col_name] != ""].drop_duplicates(subset=[col_name])
        lookup_dict = dict(
            zip(valid_df[col_name], valid_df.to_dict(orient="records"))
        )
        unique_list = list(lookup_dict.keys())
        return lookup_dict, unique_list
    return {}, []


product_lookup, product_list = create_lookup_and_list(
    device_db, "productCodeName"
)
brand_lookup, brand_list = create_lookup_and_list(device_db, "brandName")
normalized_lookup, normalized_list = create_lookup_and_list(
    device_db, "normalized_device"
)


def build_candidates(device_name, canonical_name, preferred_name, synonyms):
    candidates = []
    for term in [canonical_name, preferred_name, device_name]:
        if not term:
            continue
        term = clean_text(term)
        if term not in candidates:
            candidates.append(term)

    if isinstance(synonyms, list):
        for syn in synonyms:
            syn = clean_text(syn)
            if syn and syn not in candidates:
                candidates.append(syn)
    return candidates


def fill_device_info(device, row, method, score):
    device["PrimaryDI"] = row.get("PrimaryDI", "")
    device["submissionNumber"] = row.get("submissionNumber", "")
    device["manufacturer"] = row.get("companyName", "")
    device["brand_name"] = row.get("brandName", "")
    device["device_description"] = row.get("productCodeName", "")
    device["MRISafetyStatus"] = row.get("MRISafetyStatus", "")

    device["resolve_method"] = method
    device["similarity_score"] = round(float(score), 1)


def get_best_match(candidate, choices):
    if not candidate or not choices:
        return None
    return process.extractOne(candidate, choices, scorer=fuzz.token_set_ratio)


def resolve_device_by_product(device_json):
    devices = device_json.get("devices", [])

    for device in devices:
        device_name = clean_text(device.get("device_name", ""))
        canonical_name = clean_text(device.get("canonical_device_name", ""))
        preferred_name = clean_text(device.get("preferred_name", ""))
        synonyms = device.get("synonyms", [])

        candidates = build_candidates(
            device_name, canonical_name, preferred_name, synonyms
        )

        best_row = None
        best_score = 0
        best_method = "UNRESOLVED"

        if product_list:
            for candidate in candidates:
                result = get_best_match(candidate, product_list)
                if result is None:
                    continue

                matched_text, score = result[0], result[1]
                if score > best_score:
                    best_row = product_lookup.get(matched_text)
                    best_score = score
                    best_method = "PRODUCTCODE"

        # BRAND 매칭 (1단계 점수가 80점 미만일 때만 실행)
        if best_score < 80 and brand_list:
            for candidate in candidates:
                result = get_best_match(candidate, brand_list)
                if result is None:
                    continue

                matched_text, score = result[0], result[1]
                if score > best_score:
                    best_row = brand_lookup.get(matched_text)
                    best_score = score
                    best_method = "BRAND"

        # NORMALIZED 매칭 (2단계 점수까지 80점 미만일 때만 실행)
        if best_score < 80 and normalized_list:
            for candidate in candidates:
                result = get_best_match(candidate, normalized_list)
                if result is None:
                    continue

                matched_text, score = result[0], result[1]
                if score > best_score:
                    best_row = normalized_lookup.get(matched_text)
                    best_score = score
                    best_method = "NORMALIZED"

        # 최소 임계값 70점 이상일 때만 저장
        if best_row is not None and best_score >= 70:
            fill_device_info(device, best_row, best_method, best_score)
        else:
            device["resolve_method"] = "UNRESOLVED"
            device["similarity_score"] = round(float(best_score), 1)

    return device_json


resolve_device_by_cui = resolve_device_by_product