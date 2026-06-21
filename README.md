# LLM-Powered Implant-Dashboard
LLM-Powered Implantable Medical Device Registry and Visualization Platform (Graduate Project)

ImplantAtlas
From Unstructured Clinical Notes to Interactive Implant Device Intelligence

ImplantAtlas is an AI-powered clinical decision support platform that automatically extracts implantable medical device information from unstructured electronic medical records (EMR), enriches the extracted entities using UMLS and FDA GUDID knowledge bases, and transforms them into an interactive Device Registry, Timeline, and Body Map visualization.

The system is designed to help clinicians quickly understand a patient's complete implant history without manually reviewing years of fragmented clinical documentation.

Key Features
LLM-based Device Extraction

Automatically identifies implantable medical devices from free-text clinical notes and extracts:

Device Name
Canonical Device Name
Implant Date
Implant Status (CURRENT / NOT CURRENT)
Implant Location
Supporting Evidence
Longitudinal Device Tracking

Tracks both historical and currently implanted devices.

Supports:

Device replacement history
Explanted devices
Lifetime implant chronology
Medical Ontology Integration

Maps extracted devices to UMLS concepts and retrieves:

CUI
Preferred Name
Semantic Type
Synonyms
SNOMED CT references
FDA GUDID Enrichment

Links extracted devices with FDA GUDID records using ontology-guided fuzzy matching.

Provides:

Manufacturer
Brand Name
Device Description
MRI Safety Status
Submission Information
LLM Reviewer Validation

Applies an LLM-as-a-Judge framework to verify extraction quality and improve reliability.

The reviewer checks:

Missing devices
Hallucinated devices
Implant dates
Implant status consistency
Interactive Clinical Dashboard

Generates an intuitive visualization layer including:

Device Summary Table
Lifetime Device Timeline
Anatomical Body Map
Hover-based Metadata Exploration
Technology Stack
Python
Ollama
Qwen 2.5
Streamlit
Plotly
UMLS API
FDA GUDID
Fuzzy Matching
LLM-as-a-Judge
Clinical Motivation

Modern healthcare systems contain vast amounts of implant-related information hidden within unstructured clinical notes.

ImplantAtlas transforms fragmented documentation into structured device intelligence, enabling faster patient understanding, improved workflow efficiency, and enhanced patient safety.

ImplantAtlas
비정형 의무기록을 시각화된 이식형 의료기기 정보로 변환하는 AI 플랫폼

ImplantAtlas는 전자의무기록(EMR)에 기록된 비정형 임상 텍스트로부터 이식형 의료기기 정보를 자동 추출하고, UMLS 및 FDA GUDID 지식베이스와 연계하여 구조화된 Device Registry, Timeline, Body Map을 생성하는 AI 기반 임상 의사결정 지원 플랫폼입니다.

의료진이 수년간 누적된 기록을 직접 검토하지 않고도 환자의 전체 이식형 의료기기 이력을 빠르게 파악할 수 있도록 설계되었습니다.

주요 기능
LLM 기반 Device 추출

비정형 Clinical Note로부터 다음 정보를 자동 추출합니다.

Device Name
Canonical Device Name
Implant Date
Implant Status (CURRENT / NOT CURRENT)
Implant Location
Supporting Evidence
Lifetime Device Tracking

과거 및 현재 Device를 모두 추적합니다.

지원 기능:

Device 교체 이력
제거된 Device 관리
환자 생애주기 기반 Device Timeline
의료 온톨로지 연계

추출된 Device를 UMLS 개념과 연결하여 다음 정보를 제공합니다.

CUI
Preferred Name
Semantic Type
Synonym
SNOMED CT
FDA GUDID 메타데이터 결합

Ontology 기반 Fuzzy Matching을 이용하여 FDA GUDID 데이터와 연결합니다.

제공 정보:

제조사
제품명
Device Description
MRI Safety Status
Submission 정보
LLM Reviewer 검증

LLM-as-a-Judge 방식을 적용하여 추출 결과를 재검증합니다.

검증 항목:

누락 Device
잘못 추출된 Device
Implant Date
Implant Status
Interactive Dashboard

다음과 같은 시각화 기능을 제공합니다.

Device Summary Table
Lifetime Timeline
Anatomical Body Map
Hover 기반 상세 정보 조회
기술 스택
Python
Ollama
Qwen 2.5
Streamlit
Plotly
UMLS API
FDA GUDID
Fuzzy Matching
LLM-as-a-Judge
프로젝트 의의

ImplantAtlas는 의료기기 정보가 흩어져 있는 비정형 임상 기록을 구조화된 Device Intelligence로 변환하여, 의료진의 정보 탐색 시간을 줄이고 환자 안전성을 향상시키는 것을 목표로 합니다.
