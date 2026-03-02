import streamlit as st
import pandas as pd
import time
from datetime import datetime
from src.services.whatsapp_service import WhatsAppService
from src.utils.phone_utils import validate_numbers, format_phone_number
from src.core.i18n import t

def render_whatsapp_page():
    lang = st.session_state.get('lang', 'ar')
    is_cloud = "/mount/" in __file__
    
    if 'wa_service' not in st.session_state: st.session_state.wa_service = WhatsAppService()
    if 'wa_logs' not in st.session_state: st.session_state.wa_logs = []
    if 'wa_running' not in st.session_state: st.session_state.wa_running = False
    if 'wa_idx' not in st.session_state: st.session_state.wa_idx = 0

    st.markdown(f'<h1 style="color:#D4AF37; text-align:center;">{t("wa_title", lang)} 🚀</h1>', unsafe_allow_html=True)

    status = st.session_state.wa_service.get_status()

    # Diagnostic Tool for Pasha (Top Right)
    with st.expander("🛠️ Pasha's Diagnostic Center"):
        if st.button("📸 Capture Diagnostic Screenshot"):
            img = st.session_state.wa_service.get_diagnostic_screenshot()
            if img: st.image(f"data:image/png;base64,{img}")
            else: st.warning("Browser Offline")

    # Status Card
    c1, c2 = st.columns([2, 1])
    with c1:
        if status == "Connected": st.success(f"✅ {t('wa_online', lang)}")
        elif status == "Awaiting Login": st.warning(f"⚠️ {t('wa_ready', lang)}")
        else: st.info(f"⏳ {t('wa_loading', lang)}")
    with c2:
        if st.button("🔄 Reset / Start", type="primary", use_container_width=True):
            st.session_state.wa_service.close()
            st.session_state.wa_service.start_driver(headless=is_cloud)
            st.rerun()

    if status == "Awaiting Login":
        qr = st.session_state.wa_service.get_qr_hd()
        if qr:
            st.markdown(f'<div style="text-align:center; padding:10px; background:white; border-radius:10px; margin-bottom:10px;"><img src="{qr}" style="width:250px; border:2px solid #25D366;"></div>', unsafe_allow_html=True)
            time.sleep(10); st.rerun()

    # Message Form
    st.markdown("---")
    col_input, col_msg = st.columns(2)
    with col_input:
        txt_in = st.text_area("Paste Numbers (Pasha Mode)", height=150, placeholder="054...")
        v_sa, v_ph, _ = validate_numbers(txt_in)
        all_v = v_sa + v_ph
        if all_v: st.success(f"Recipients Ready: {len(all_v)}")
    
    with col_msg:
        msg_body = st.text_area("Final Message Content", height=150)
        delay = st.slider("Safe Delay (Seconds)", 2, 60, 5)

    # ACTION AREA
    if st.session_state.wa_running:
        if st.button(f"🛑 STOP FOR PASHA", type="primary", use_container_width=True):
            st.session_state.wa_running = False; st.rerun()
    else:
        active = (status == "Connected") and (len(all_v) > 0) and (msg_body.strip() != "")
        if st.button(f"🚀 {t('wa_start_btn', lang)} 🔥", disabled=not active, use_container_width=True):
            st.session_state.wa_running = True; st.session_state.wa_idx = 0; st.rerun()

    # SENDING ENGINE
    if st.session_state.wa_running and all_v:
        st.progress(st.session_state.wa_idx / len(all_v))
        if st.session_state.wa_idx < len(all_v):
            target = all_v[st.session_state.wa_idx]
            st.info(f"⏳ Pasha's Broadcast: {target} (Sending...)")
            
            ok, info = st.session_state.wa_service.send_message(target, msg_body)
            log_icon = "✅" if ok else "❌"
            st.session_state.wa_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_icon} {target}: {info}")
            st.session_state.wa_idx += 1
            
            if st.session_state.wa_idx == len(all_v):
                st.session_state.wa_running = False; st.balloons()
            time.sleep(delay); st.rerun()

    if st.session_state.wa_logs:
        st.markdown('<div class="wa-log-box" style="background:rgba(0,0,0,0.8); padding:10px; border-radius:10px; color:#00FF41; max-height:200px; overflow-y:auto; font-family:monospace;">', unsafe_allow_html=True)
        for l in reversed(st.session_state.wa_logs): st.text(l)
        st.markdown('</div>', unsafe_allow_html=True)
