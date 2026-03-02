import streamlit as st
import pandas as pd
import time
from datetime import datetime
from src.services.whatsapp_service import WhatsAppService
from src.utils.phone_utils import validate_numbers, format_phone_number
from src.core.i18n import t

def get_whatsapp_ui_css(lang):
    alignment = "right" if lang == "ar" else "left"
    direction = "rtl" if lang == "ar" else "ltr"
    return f"""
    <style>
        .wa-container {{ direction: {direction}; text-align: {alignment}; }}
        .wa-glass-card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .wa-status-connected {{ color: #00FF41; font-weight: bold; font-size: 1.3rem; }}
    </style>
    """

def render_whatsapp_page():
    lang = st.session_state.get('lang', 'ar')
    st.markdown(get_whatsapp_ui_css(lang), unsafe_allow_html=True)
    is_cloud = "/mount/" in __file__
    
    if 'wa_service' not in st.session_state: st.session_state.wa_service = WhatsAppService()
    if 'wa_logs' not in st.session_state: st.session_state.wa_logs = []
    if 'wa_running' not in st.session_state: st.session_state.wa_running = False
    if 'wa_idx' not in st.session_state: st.session_state.wa_idx = 0

    st.markdown(f'<div class="wa-container">', unsafe_allow_html=True)
    st.markdown(f'<h1 style="color:#D4AF37; text-align:center;">{t("wa_title", lang)}</h1>', unsafe_allow_html=True)

    # Status Control
    status = st.session_state.wa_service.get_status()
    st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        if status == "Connected": st.success(f"✅ {t('wa_online', lang)}")
        elif status == "Awaiting Login": st.warning(f"⚠️ {t('wa_ready', lang)}")
        elif status == "Loading...": st.info(f"⏳ {t('wa_loading', lang)}")
        else: st.error(f"❌ {t('wa_offline', lang)}")
    with c2:
        if status != "Disconnected":
            if st.button(t("wa_disconnect", lang), use_container_width=True):
                st.session_state.wa_service.close(); st.rerun()
        else:
            if st.button(t("wa_launch_btn", lang), type="primary", use_container_width=True):
                st.session_state.wa_service.start_driver(headless=is_cloud); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if status == "Awaiting Login":
        qr = st.session_state.wa_service.get_qr_hd()
        if qr:
            st.markdown(f'<div style="text-align:center; padding:20px; background:white; border-radius:15px; margin-bottom:20px;"><img src="{qr}" style="width:300px; border:5px solid #25D366;"></div>', unsafe_allow_html=True)
            time.sleep(10); st.rerun()

    # Form
    col_input, col_msg = st.columns(2)
    with col_input:
        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader(t("wa_step1_lbl", lang))
        file_up = st.file_uploader(t("wa_upload_opt", lang), type=['xlsx', 'csv', 'txt'])
        txt_in = st.text_area(t("wa_paste_opt", lang), height=150, placeholder="054...")
        
        raw_final = ""
        if file_up:
            try:
                if file_up.name.endswith('.xlsx'):
                    df = pd.read_excel(file_up)
                    cols = [c for c in df.columns if any(k in str(c).lower() for k in ['phone', 'num', 'mob'])]
                    if cols: raw_final = "\n".join(df[cols[0]].astype(str).tolist())
                else: raw_final = file_up.read().decode('utf-8')
            except: pass
        else: raw_final = txt_in
        
        v_sa, v_ph, _ = validate_numbers(raw_final)
        all_v = v_sa + v_ph
        if all_v: st.success(f"Recipients: {len(all_v)}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_msg:
        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader(t("wa_step2_lbl", lang))
        msg_input = st.text_area(t("wa_msg_body", lang), height=150, value=" ") # Space to prevent empty disable
        delay = st.slider(t("wa_delay_lbl", lang), 2, 60, 5)
        st.markdown('</div>', unsafe_allow_html=True)

    # START BUTTON FOR PASHA
    st.markdown('<div class="wa-glass-card" style="text-align:center;">', unsafe_allow_html=True)
    if st.session_state.wa_running:
        if st.button(f"🛑 {t('wa_stop_btn', lang)}", type="primary", use_container_width=True):
            st.session_state.wa_running = False; st.rerun()
    else:
        # Pasha can click if numbers exist, even if message is just a space
        is_ready = status == "Connected" and len(all_v) > 0
        if st.button(f"🚀 {t('wa_start_btn', lang)} 🔥", disabled=not is_ready, use_container_width=True):
            st.session_state.wa_running = True; st.session_state.wa_idx = 0; st.rerun()

    # BROADCAST ENGINE
    if st.session_state.wa_running and all_v:
        st.progress(st.session_state.wa_idx / len(all_v))
        if st.session_state.wa_idx < len(all_v):
            target = all_v[st.session_state.wa_idx]
            st.info(f"Broadcasting to Pasha's List: {target}...")
            # Use space if empty
            final_body = msg_input if msg_input.strip() else "Hello from Pasha's 2026 App!"
            ok, info = st.session_state.wa_service.send_message(target, final_body)
            st.session_state.wa_logs.append(f"[{datetime.now().strftime('%H:%M')}] {'✅' if ok else '❌'} {target}: {info}")
            st.session_state.wa_idx += 1
            if st.session_state.wa_idx == len(all_v):
                st.session_state.wa_running = False; st.balloons()
            time.sleep(delay); st.rerun()

    if st.session_state.wa_logs:
        st.markdown('<div style="background:rgba(0,0,0,0.7); padding:10px; border-radius:10px; max-height:200px; overflow-y:auto; color:#00FF41;">', unsafe_allow_html=True)
        for l in reversed(st.session_state.wa_logs): st.text(l)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
