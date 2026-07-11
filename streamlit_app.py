import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from pathlib import Path
from collections import defaultdict  

from llm_extract import run_pipeline
from bodymap import render_bodymap

st.set_page_config(
    page_title="Implant Device Registry",
    layout="wide"
)

st.title("🏥 Implantable Device Registry & Tracking System")

st.markdown(
    """
Input a clinical note to seamlessly integrate LLM, UMLS, and FDA databases,
enabling real-time synchronization of a standardized longitudinal timeline and an anatomical patient bodymap.
"""
)

note = st.text_area("Enter Clinical Note", height=250)

if st.button("Execute Pipeline"):
    if not note.strip():
        st.warning("Enter Clinical Note.")
    else:
        with st.spinner("Analyzing LLM & Querying Medical Knowledge Graph..."):
            result = run_pipeline(note)

        st.success("Patient Data Successfully Normalized")
        devices = result.get("devices", [])

        col_left, col_right = st.columns([1.1, 0.9])

        with col_left:
            st.subheader("📋 Device Summary")
            st.write(f"Detected Implantable Device History : {len(devices)}")

            if len(devices) > 0:
                rows = []
                for d in devices:
                    loc_candidate = d.get("implant_location") or d.get("location") or "Unknown"
                    rows.append({
                        "Device": d.get("device_name", ""),
                        "Generic Concept": d.get("preferred_name") or d.get("canonical_device_name", ""),
                        "Status": d.get("implant_status", ""),
                        "Date": d.get("implant_date", ""),
                        "Implant Site": loc_candidate,
                        "MRI Safety": d.get("MRISafetyStatus", "Unknown")
                    })

                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)

                st.subheader("Patient Device Timeline")
                timeline_devices = []
                for d in devices:
                    year = str(d.get("implant_date", "")).strip()
                    try:
                        year = int(year[:4])
                    except:
                        continue

                    timeline_devices.append({
                        "year": year,
                        "device": d.get("device_name", ""),
                        "canonical": d.get("canonical_device_name", ""),
                        "status": d.get("implant_status", ""),
                        "location": d.get("implant_location") or d.get("location") or "Unknown",
                        "text": d.get("supporting_text", "")
                    })

                timeline_devices = sorted(timeline_devices, key=lambda x: x["year"])

                if len(timeline_devices) > 0:
                    years = [x["year"] for x in timeline_devices]
                    start_year, end_year = min(years) - 1, max(years) + 1
                    year_range = end_year - start_year
                    if year_range == 0: year_range = 2; start_year -= 1; end_year += 1

                    timeline_html = f"""
                    <style>
                        .tl-container {{ background: #F8FAFC; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; height: 320px; font-family: system-ui; position: relative; }}
                        .tl-axis {{ position: absolute; top: 120px; left: 10%; right: 10%; height: 5px; background: #64748B; border-radius: 4px; }}
                        .tl-node {{ position: absolute; top: 110px; transform: translateX(-50%); cursor: pointer; }} /* 💡 top 고정: 선 위에 점 하나만 생성 */
                        .tl-dot {{ width: 18px; height: 18px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.15); transition: 0.2s; }}
                        .tl-dot.current {{ background: #2563EB; }}
                        .tl-node:hover .tl-dot.current {{ transform: scale(1.3); background: #1D4ED8; }}
                        .tl-dot.not-current {{ background: #EF4444; }}
                        .tl-node:hover .tl-dot.not-current {{ transform: scale(1.3); background: #DC2626; }}
                        
                        /* 툴팁 내부 다중 데이터 스택 */
                        .tl-tooltip {{ visibility: hidden; width: 280px; max-height: 240px; overflow-y: auto; background: #0F172A; color: white; border-radius: 8px; padding: 12px; position: absolute; z-index: 100; bottom: 30px; left: 50%; transform: translateX(-50%); opacity: 0; transition: 0.2s; font-size: 11px; line-height: 1.4; box-shadow: 0 4px 15px rgba(0,0,0,0.2); pointer-events: none; }}
                        .tl-tooltip::after {{ content: ""; position: absolute; top: 100%; left: 50%; margin-left: -5px; border-width: 5px; border-style: solid; border-color: #0F172A transparent transparent transparent; }}
                        .tl-node:hover .tl-tooltip {{ visibility: visible; opacity: 1; transform: translateX(-50%) translateY(-5px); }}
                    </style>
                    <div class="tl-container">
                        <b style="color:#1E3A8A; font-size:14px; display:block; margin-bottom:15px;">Linear Proportional History</b>
                        <div style="position:relative; height:200px;">
                            <div class="tl-axis"></div>
                    """
                    
                    grouped_by_year = defaultdict(list)
                    for item in timeline_devices:
                        grouped_by_year[item["year"]].append(item)

                    for cur_year in sorted(grouped_by_year.keys()):
                        items = grouped_by_year[cur_year]
                        
                        left = 10 + (80 * (cur_year - start_year) / year_range)
                        
                        has_current = any(x["status"] == "CURRENT" for x in items)
                        status_class = "current" if has_current else "not-current"
                        
                        tooltip_stacked_html = ""
                        for idx, item in enumerate(items):
                            safe_text = item['text'].replace('"', '&quot;').replace("'", "&apos;")
                            status_badge_color = "#34D399" if item["status"] == "CURRENT" else "#FCA5A5"
                            
                            if idx > 0:
                                tooltip_stacked_html += '<hr style="border: 0; border-top: 1px dashed #334155; margin: 8px 0;">'
                            
                            tooltip_stacked_html += f"""
                            <div class="stacked-item">
                                <b style="color:#60A5FA; font-size:12px; display:block; margin-bottom:4px;">{item['device']}</b>
                                <b>Concept:</b> {item['canonical']}<br>
                                <b>Status:</b> <span style="color: {status_badge_color}; font-weight: bold;">{item['status']}</span><br>
                                <b>Location:</b> {item['location']}<br>
                                <div style="margin-top:4px; color:#94A3B8; font-style:italic; font-size:10px;">"{safe_text}"</div>
                            </div>
                            """

                        timeline_html += f"""
                        <div class="tl-node" style="left: {left}%;">
                            <div class="tl-dot {status_class}"></div>
                            <div class="tl-tooltip">
                                {tooltip_stacked_html}
                            </div>
                            <div style="margin-top:8px; font-weight:bold; font-size:12px; color:#334155; text-align:center;">{cur_year}</div>
                        </div>
                        """
                        
                    timeline_html += "</div></div>"
                    components.html(timeline_html, height=340, scrolling=False)

        with col_right:
            st.subheader("🗺️ Live Anatomy Bodymap")

            LOCAL_IMG_PATH = Path(r"C:\Users\신효원\Desktop\생성형AI수업\DATA\implant_dashboard\assets\body_front.png")
            RELATIVE_IMG_PATH = Path(__file__).parent / "assets" / "body_front.png"
            CURRENT_DIR_IMG_PATH = Path(__file__).parent / "body_front.png"
            
            if LOCAL_IMG_PATH.exists():
                img_path = str(LOCAL_IMG_PATH)
            elif RELATIVE_IMG_PATH.exists():
                img_path = str(RELATIVE_IMG_PATH)
            else:
                img_path = str(CURRENT_DIR_IMG_PATH)
                
            render_bodymap(devices, img_path)
