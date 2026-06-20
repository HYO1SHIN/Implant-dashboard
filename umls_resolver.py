import requests
import pandas as pd
import os
import streamlit as st


API_KEY = os.environ.get("UMLS_API_KEY")

if not API_KEY:
    try:
        API_KEY = st.secrets["UMLS_API_KEY"]
    except:
        API_KEY = ""

BASE_URL = "https://uts-ws.nlm.nih.gov"


def get_semantic_type(cui):
    try:
        url = (
            BASE_URL +
            f"/rest/content/current/CUI/{cui}"
        )
        params = {
            "apiKey": API_KEY
        }
        r = requests.get(
            url,
            params=params,
            timeout=10
        )
        data = r.json()
        semantic_types = (
            data
            .get("result", {})
            .get("semanticTypes", [])
        )
        if len(semantic_types) == 0:
            return ""
        return semantic_types[0].get(
            "name",
            ""
        )
    except:
        return ""


def get_cui_detail(cui):
    result = {
        "semantic_type":"",
        "synonyms":[],
        "snomed_id":""
    }
    try:

        content_url = (
            BASE_URL +
            f"/rest/content/current/CUI/{cui}"
        )
        params = {
            "apiKey": API_KEY
        }
        r = requests.get(
            content_url,
            params=params,
            timeout=10
        )
        data = r.json()
        semantic_types = (
            data
            .get("result", {})
            .get("semanticTypes", [])
        )
        if len(semantic_types) > 0:
            result["semantic_type"] = semantic_types[0].get(
                "name",
                ""
            )


        atom_url = (
            BASE_URL +
            f"/rest/content/current/CUI/{cui}/atoms"
        )
        r2 = requests.get(
            atom_url,
            params=params,
            timeout=10
        )
        atom_data = r2.json()
        atoms = atom_data.get(
            "result",
            []
        )

        synonyms = []
        for atom in atoms[:50]:
            name = atom.get(
                "name",
                ""
            )
            if (
                name
                and
                name not in synonyms
            ):
                synonyms.append(name)

            root = atom.get(
                "rootSource",
                ""
            )
            if root == "SNOMEDCT_US":
                code = atom.get(
                    "code",
                    ""
                )
                if code:
                    result["snomed_id"] = code.split("/")[-1]

        result["synonyms"] = synonyms
        return result

    except Exception as e:
        print("DETAIL ERROR:", cui)
        print(e)
        return result


def choose_best_candidate(results):
    candidates = []
    for item in results[:20]:
        cui = item.get(
            "ui",
            ""
        )
        if cui in ["", "NONE"]:
            continue

        semantic_type = get_semantic_type(cui)
        candidates.append({
            "cui": cui,
            "name": item.get("name", ""),
            "semantic_type": semantic_type
        })

    preferred_types = [
        "Medical Device",
        "Manufactured Object"
    ]

    for ptype in preferred_types:
        for c in candidates:
            if c["semantic_type"] == ptype:
                return c

    for c in candidates:
        if c["semantic_type"] not in [
            "Therapeutic or Preventive Procedure",
            "Diagnostic Procedure",
            "Temporal Concept"
        ]:
            return c

    if len(candidates) > 0:
        return candidates[0]
    return None

def search_umls(term):
    if pd.isna(term):
        return None

    term = str(term).strip()
    if len(term) < 2:
        return None

    search_url = (
        BASE_URL +
        "/rest/search/current"
    )
    params = {
        "string": term,
        "apiKey": API_KEY,
        "pageNumber": 1,
        "searchType": "words"
    }

    try:
        r = requests.get(
            search_url,
            params=params,
            timeout=10
        )
        data = r.json()
        results = (
            data
            .get("result", {})
            .get("results", [])
        )

        if len(results) == 0:
            return {"cui":"NO_MATCH"}

        best = choose_best_candidate(results)
        if best is None:
            return {"cui":"NO_MATCH"}

        detail = get_cui_detail(best["cui"])
        return {
            "cui": best["cui"],
            "preferred_name": best["name"],
            "semantic_type": detail.get("semantic_type", ""),
            "synonyms": detail.get("synonyms", []),
            "snomed_id": detail.get("snomed_id", "")
        }

    except Exception as e:
        print("UMLS ERROR:", term)
        print(e)
        return {"cui":"ERROR"}