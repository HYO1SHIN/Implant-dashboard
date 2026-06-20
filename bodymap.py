import base64
import json
import streamlit as st
import streamlit.components.v1 as components

DEVELOPER_MODE = False 


LANDMARKS = {
    "brain": {"left": 50, "top": 11},
    "neck": {"left": 50, "top": 19},
    "cervical spine": {"left": 50, "top": 20},
    "thoracic spine": {"left": 50, "top": 25},
    "lumbar spine": {"left": 50, "top": 42},
    "heart": {"left": 59, "top": 28},
    "abdomen": {"left": 50, "top": 46},
    
    "right shoulder": {"left": 30, "top": 25},
    "left shoulder": {"left": 70, "top": 25},
    
    "right elbow": {"left": 26, "top": 40},
    "left elbow": {"left": 76, "top": 40},
    
    "right hand": {"left": 20, "top": 54},
    "left hand": {"left": 80, "top": 54},
    
    "right pelvis (femoral head)": {"left": 39, "top": 52},
    "left pelvis (femoral head)": {"left": 61, "top": 52},
    "right knee": {"left": 44, "top": 69},
    "left knee": {"left": 56, "top": 69},
    
    "right foot": {"left": 44, "top": 91},
    "left foot": {"left": 56, "top": 91}
}


def calculate_anatomy_coordinates(location_str):
    loc = str(location_str).lower().strip()
    
    if loc in LANDMARKS:
        return LANDMARKS[loc]
        
    for key in LANDMARKS:
        if key in loc:
            return LANDMARKS[key]
            
    return {"left": 50, "top": 46}


def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except Exception:
        return ""


def render_bodymap(devices, img_path):
    
    with st.expander("🛠️ 바디맵 입력 데이터 실시간 검증기 (디버거)", expanded=False):
        st.write(f"현재 백엔드로부터 넘겨받은 총 기기 개수: **{len(devices)}개**")
        if len(devices) > 0:
            debug_rows = []
            for idx, d in enumerate(devices, 1):
                debug_rows.append({
                    "번호": idx,
                    "기기명(device_name)": d.get("device_name"),
                    "분류된 위치(implant_location)": d.get("implant_location"),
                    "상태(status)": d.get("implant_status")
                })
            st.table(debug_rows)

    base64_img = get_base64_image(img_path)
    if not base64_img:
        st.error(f"💡 바디맵 배경 이미지를 로드하지 못했습니다. 경로를 확인해 주세요: {img_path}")
        return

    debug_box_html = ""
    script_html = ""
    if DEVELOPER_MODE:
        debug_box_html = '<div id="coord-reporter" style="position: absolute; top: 15px; right: 15px; background: #000; color: #00FF66; padding: 8px 16px; border-radius: 8px; font-family: monospace; font-size: 14px; font-weight: bold; z-index: 9999; border: 2px solid #00FF66;">⏱️ 마우스를 이미지 위로 올리세요</div>'
        script_html = "<script>setTimeout(function(){var c=document.getElementById('chrome-safe-map-container'),r=document.getElementById('coord-reporter');if(c&&r){c.addEventListener('mousemove',function(e){var rect=c.getBoundingClientRect(),x=Math.round(((e.clientX-rect.left)/rect.width)*100),y=Math.round(((e.clientY-rect.top)/rect.height)*100);if(x>=0&&x<=100&&y>=0&&y<=100){r.innerHTML='🎯 X: '+x+'% | Y: '+y+'%';}});}},150);</script>"


    grouped_map = {}
    
    for d in devices:
        if d.get("implant_status") != "CURRENT":
            continue
            
        loc_name = d.get("implant_location") or d.get("location") or "Unknown"
        loc_clean = loc_name.lower().strip()
        
        coords = calculate_anatomy_coordinates(loc_clean)
        coord_key = f"{coords['left']}_{coords['top']}"
        
        if coord_key not in grouped_map:
            grouped_map[coord_key] = {
                "display_name": loc_name.upper(),
                "left": coords["left"],
                "top": coords["top"],
                "device_list": []
            }
        
        grouped_map[coord_key]["device_list"].append(d)

    # 기본 베이스 HTML 빌드
    bodymap_html = f"""
    <style>
        .map-container {{ position: relative; width: 100%; max-width: 300px; margin: 0 auto; background: #1E293B; border-radius: 20px; padding: 15px; box-sizing: border-box; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
        .body-img {{ width: 100%; height: auto; display: block; border-radius: 12px; }}
        .body-node {{ position: absolute; transform: translate(-50%, -50%); cursor: pointer; z-index: 10; }}
        .pulse-core {{ width: 14px; height: 14px; border: 2px solid white; border-radius: 50%; box-shadow: 0 0 8px rgba(239, 68, 68, 0.8); }}
        .pulse-ring {{ border-radius: 30px; height: 28px; width: 28px; position: absolute; left: -10px; top: -10px; animation: pulsate 1.8s infinite ease-out; opacity: 0; }}
        @keyframes pulsate {{ 0% {{ transform: scale(0.1, 0.1); opacity: 0.0; }} 50% {{ opacity: 0.8; }} 100% {{ transform: scale(1.2, 1.2); opacity: 0.0; }} }}
        .map-tooltip {{ visibility: hidden; width: 280px; background-color: rgba(15, 23, 42, 0.96); color: #fff; padding: 14px; border-radius: 10px; position: absolute; z-index: 200; left: 25px; top: -40px; opacity: 0; transition: opacity 0.2s, transform 0.2s; font-size: 11px; font-family: system-ui; line-height: 1.5; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #475569; pointer-events: none; }}
        .body-node:hover .map-tooltip {{ visibility: visible; opacity: 1; transform: scale(1.02); }}
    </style>

    <div id="chrome-safe-map-container" class="map-container">
        <img class="body-img" src="data:image/png;base64,{base64_img}" alt="Body Map">
        {debug_box_html}
    """

    # 렌더링 루프 
    for key, group in grouped_map.items():
        node_color = "#EF4444" 
        
        tooltip_html = f"""
        <div class="map-tooltip">
            <b style="font-size:13px; color:#FCA5A5; display:block; margin-bottom:8px;">📍 {group['display_name']}</b>
        """
        
        for idx, d in enumerate(group["device_list"]):
            if idx > 0:
                tooltip_html += '<hr style="border: 0; border-top: 1px solid #334155; margin: 8px 0;">'
                
            safe_text = str(d.get("supporting_text", "")).replace('"', '&quot;').replace("'", "&apos;")
            status_txt = d.get("implant_status", "Unknown")
            
            tooltip_html += f"""
            <div style="margin-bottom: 2px;">
                <b style="color:#FFF; font-size:12px;">• {d.get('device_name')}</b> 
                <span style="color:#34D399; font-size:10px; font-weight:bold; margin-left:5px;">[{status_txt}]</span>
            </div>
            <div style="color:#94A3B8; font-size:10px; margin-left:8px;"><b>Generic:</b> {d.get('canonical_device_name','')}</div>
            <div style="color:#94A3B8; font-size:10px; margin-left:8px;"><b>Date:</b> {d.get('implant_date','')}</div>
            <div style="margin-top:4px; margin-left:8px; color:#CBD5E1; font-size:10px; font-style:italic; line-height:1.4;">
                "{safe_text}"
            </div>
            """
            
        tooltip_html += "</div>"
        
        bodymap_html += f"""
        <div class="body-node" style="left: {group['left']}%; top: {group['top']}%;">
            <div class="pulse-core" style="background: {node_color};"></div>
            <div class="pulse-ring" style="border-color: {node_color};"></div>
            {tooltip_html}
        </div>
        """

    bodymap_html += f"</div>{script_html}"
    components.html(bodymap_html, height=760, scrolling=False)