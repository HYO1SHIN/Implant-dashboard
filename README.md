# <p align="center">🩺 ImplantAtlas</p>
<p align="center">
  <strong>LLM-Powered Implantable Medical Device Registry & Visualization Platform</strong><br>
  <em>
  Hyowon Shin
  <br>
  M.S. Candidate, Graduate School of AI·Software, Sogang University
  <br><br>
  From Unstructured Clinical Notes to Interactive Device Intelligence
  </em>
</p>


---

## 🌐 Live Demo

🚀 **Experience the interactive dashboard live right now:** 👉 **[https://implant-dashboard-scx5vbr9e7ndaw5jbaukye.streamlit.app/](https://implant-dashboard-scx5vbr9e7ndaw5jbaukye.streamlit.app/)**

---

## 💡 Clinical Motivation

Modern healthcare systems contain vast amounts of implant-related information hidden within unstructured, fragmented clinical notes. Manual review of years of documentation compromises clinical workflow efficiency and patient safety. 

`<ImplantAtlas>` solves this by transforming fragmented medical prose into structured, actionable **Device Intelligence**, enabling clinicians to grasp a patient's complete implant history within seconds.

---

## ✨ Key Features

### 🧠 1. LLM-based Device Extraction
Automatically parses free-text clinical notes to isolate genuine implantable device entities and extracts:
* `Device Name` & `Canonical Generic Concepts`
* `Implant / Explant Dates`
* `Anatomical Implant Location`
* `Supporting Evidence (provenance)`

### ⏳ 2. Longitudinal Lifecycle Tracking
Maintains strict chronological fidelity for patient history.
* Maps complete device lineage (<kbd>Implantation</kbd> ➡️ <kbd>Replacement</kbd> ➡️ <kbd>Removal</kbd>).
* Tracks active (`CURRENT`) vs explanted (`NOT CURRENT`) device states.
* Enforces a *Device Lifecycle Merging Rule* to handle continuous historical timelines without entity duplication.

### 📚 3. Medical Ontology Integration (UMLS)
Standardizes free-text terminology by linking extracted devices to the **Unified Medical Language System (UMLS)**:
* Retrieves Unique Concept Unique Identifiers (<kbd>CUI</kbd>) and Preferred Names.
* Filters via Semantic Types (e.g., *Medical Device*, *Manufactured Object*).
* Cross-references with **SNOMED CT** codes for global interoperability.

### 🔍 4. FDA GUDID Enrichment
Links standardized entities with the **FDA Global Unique Device Identification Database (GUDID)** via ontology-guided fuzzy matching to uncover critical hardware specifications:
* Manufacturer & Brand Details
* **🧲 MRI Safety Status** (Essential for pre-imaging screening)
* FDA Submission & Pre-market Approval Records

### ⚖️ 5. LLM-as-a-Judge Validation Framework
Utilizes a secondary LLM pipeline step acting as a clinical reviewer to audit extraction quality:
* Eliminates clinical hallucinations.
* Aggressively filters out **Family History** (e.g., *Mother's pacemaker*) and **Future/Planned Procedures**.

### 📊 6. Interactive Clinical Dashboard
Generates a highly intuitive, multi-dimensional visualization layer:
* **📋 Device Summary Table:** Quick registry of active and historical implants.
* **📈 Lifetime Device Timeline:** Interactive tracking of hardware chronologies.
* **🧍 Anatomical Body Map:** Scatter-mapped 2D coordinate node engine utilizing 19 predefined anatomical standard zones with hover-based metadata exploration.

---

## 🛠️ Technology Stack

| Category | Technologies Used |
| :--- | :--- |
| **Backend & Core** | `Python` |
| **Frontend UI / UX** | `Streamlit` |
| **Visualization Engine** | `Plotly Engine` |
| **LLM Infrastructure** | `Groq Cloud API` / `Ollama Option` |
| **AI Foundations** | `Llama 3.3 (70B-Versatile)` / `Llama 3.1 (8B-Instant)` / `Qwen 2.5` |
| **Knowledge Bases** | `UMLS Terminology API` / `FDA GUDID (Fuzzy Match Processor)` |
| **Architecture Framework** | `LLM-as-a-Judge Validation` |

---

## 🔄 System Architecture Flow

```text
[Unstructured Clinical Note]
            │
            ▼
[Step 1: Raw LLM Extraction] ────► [Step 2: LLM Reviewer Audit] (Filters Family History)
                                                │
                                                ▼
[Step 4: FDA GUDID Match] ◄──── [Step 3: UMLS Ontology Mapping] (Resolves CUIs)
            │
            ▼
[Interactive Dashboard Layer] ───► (Summary Table / Timeline / 19-Zone Body Map)
```

## 🇰🇷 국문 요약 (Project Overview in Korean)

### 📢 비정형 의무기록을 시각화된 이식형 의료기기 정보로 변환하는 임상 decision support AI 플랫폼

**ImplantAtlas**는 병원 전자의무기록(EMR) 내에 정형화되지 않은 상태로 흩어져 있는 임상 텍스트(Clinical Notes)로부터 환자의 체내 삽입형 의료기기(Implantable Medical Devices) 정보를 자동 추출하는 대규모 언어 모델(LLM) 기반의 임상 의사결정 지원 플랫폼입니다. 

추출된 데이터는 글로벌 의료 온톨로지 표준인 **UMLS(Unified Medical Language System)** 및 미국 **FDA GUDID(Global Unique Device Identification Database)** 지식베이스와 실시간으로 연계 및 확장되어, 의료진에게 구조화된 **Device Registry(기기 이력 현황), Timeline(생애주기 흐름), 19개 구역 표준 Anatomical Body Map(인체 매핑)** 시각화 레이어를 즉각적으로 제공합니다.

---

### 🎯 핵심 아키텍처 및 기능

* **LLM 기반 임상 데이터 정밀 추출:** 비정형 의무기록을 실시간 파싱하여 기기명(Device Name), 상세 규격(Size), 이식일(Implant Date) 뿐만 아니라 기기의 현재 활성화 여부(`CURRENT` / `NOT CURRENT`) 및 데이터 신뢰성을 증명할 임상적 근거 문맥(`supporting_text`)을 정밀하게 추출합니다.
* **하드웨어 생애주기 추적 및 의미론적 병합 (Lifecycle Merging):** 환자의 장기적인 타임라인 상에서 발생하는 기기의 이식, 교체(Replacement), 제거(Removal) 이력을 시간 순으로 추적합니다. 동일한 기기 슬롯에서 발생하는 다발성 이벤트를 하나의 역사로 융합 처리하여 데이터의 중복 생성을 방지합니다.
* **임상 루프 검증 시스템 (LLM-as-a-Judge):** 1단계 추출 결과를 2단계 LLM Reviewer 가드레일을 통해 재검증함으로써 인공지능의 불완전한 환각(Hallucination) 현상을 원천 차단합니다. 특히 환자 본인의 이력이 아닌 **가족력**(*어머니의 인공심박동기 이력 등*)이나 **미래 수술 계획** 문장을 완벽하게 식별하여 필터링합니다.
* **다중 지식베이스 맵핑 및 환자 안전 시각화:** 추출된 텍스트를 UMLS 표준 개념 ID(<kbd>CUI</kbd>) 및 SNOMED CT 코드로 표준화하고, FDA GUDID 데이터와의 지식 그래프 통합(Fuzzy Matching)을 수행합니다. 이를 통해 임상 현장에서 가장 치명적인 안전 가이드인 **🧲 MRI 촬영 안전성 정보(MRI Safety Status)**를 대시보드 상에서 1초 만에 직관적으로 식별할 수 있도록 지원합니다.

---

### 🚀 프로젝트의 의의

환자의 수많은 비정형 임상 기록 속에 파편화되어 숨겨져 있던 의료기기 정보를 일목요연한 **Device Intelligence**로 자율 변환함으로써, 의료진의 기록 탐색 및 검토 시간을 획기적으로 단축시킵니다. 나아가 교차 검증된 정확한 이식물 족보를 제공함으로써 환자 인계 및 응급 처치, MRI 영상 검사 시의 임상적 오류를 방지하고 환자의 안전성을 극대화하는 것에 본 프로젝트의 핵심 의의가 있습니다.
