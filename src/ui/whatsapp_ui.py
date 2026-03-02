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
            border-radius: 24px;
            padding: 25px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            margin-bottom: 20px;
            transition: all 0.3s ease;
            direction: {direction};
        }}
        .wa-status-connected {{ color: #00FF41; font-weight: bold; text-shadow: 0 0 10px rgba(0, 255, 65, 0.5); }}
        .wa-status-disconnected {{ color: #FF3131; font-weight: bold; text-shadow: 0 0 10px rgba(255, 49, 49, 0.5); }}
        .wa-status-loading {{ color: #D4AF37; animation: pulse 1.5s infinite; }}
        @keyframes pulse {{ 0% {{ opacity: 0.6; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.6; }} }}
        .wa-log {{
            font-family: 'Consolas', monospace;
            font-size: 0.85rem;
            background: rgba(0,0,0,0.5);
            padding: 15px;
            border-radius: 12px;
            max-height: 250px;
            overflow-y: auto;
            color: #aaa;
            direction: ltr;
        }}
        .wa-qr-container {{
            background: white;
            padding: 20px;
            border-radius: 20px;
            display: inline-block;
            box-shadow: 0 0 20px rgba(212,175,55,0.3);
        }}
    </style>
    """

def render_whatsapp_page():
    lang = st.session_state.get('lang', 'ar')
    st.markdown(get_whatsapp_ui_css(lang), unsafe_allow_html=True)
    is_cloud = "/mount/" in __file__
    
    st.markdown(f'<div class="wa-container">', unsafe_allow_html=True)
    
    st.markdown(f'''<div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #D4AF37; font-family: 'Cinzel', serif;">{t('wa_title', lang)}</h1>
        <p style="color: #888;">{t('wa_subtitle', lang)}</p>
    </div>''', unsafe_allow_html=True)
    
    if 'wa_service' not in st.session_state:
        st.session_state.wa_service = WhatsAppService()
        st.session_state.wa_running = False
        st.session_state.wa_logs = []
        st.session_state.wa_sent = 0
        st.session_state.wa_total = 0
        st.session_state.wa_active_numbers = []

    col_status, col_main = st.columns([1, 2.5])
    
    with col_status:
        st.markdown(f'<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader(t('wa_status_lbl', lang))
        
        try:
            status = st.session_state.wa_service.get_status()
        except:
            status = "Disconnected"
        
        if status == "Connected":
            st.markdown(f'<div style="text-align:center;"><span class="wa-status-connected" style="font-size:1.5rem;">{t("wa_online", lang)}</span></div>', unsafe_allow_html=True)
            if st.button(t("wa_disconnect", lang), use_container_width=True):
                st.session_state.wa_service.close()
                st.rerun()
        elif status == "Awaiting Login":
            st.markdown(f'Status: <span class="wa-status-loading">{t("wa_ready", lang)}</span>', unsafe_allow_html=True)
            qr_b64 = st.session_state.wa_service.get_qr_base64()
            if qr_b64:
                st.markdown('<div style="text-align:center;" class="wa-qr-container">', unsafe_allow_html=True)
                st.image(f"data:image/png;base64,{qr_b64}", width=250)
                st.markdown('</div>', unsafe_allow_html=True)
                time.sleep(5)
                st.rerun()
            else:
                st.warning("Generating QR...")
                time.sleep(2)
                st.rerun()
        elif status == "Loading...":
            st.markdown(f'Status: <span class="wa-status-loading">{t("wa_loading", lang)}</span>', unsafe_allow_html=True)
            time.sleep(3)
            st.rerun()
        else:
            st.markdown(f'Status: <span class="wa-status-disconnected">{t("wa_offline", lang)}</span>', unsafe_allow_html=True)
            if st.button(t("wa_launch_btn", lang), use_container_width=True):
                with st.spinner(t("extracting", lang)):
                    headless_mode = True if is_cloud else False
                    st.session_state.wa_service.start_driver(headless=headless_mode)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader(t('wa_step1_lbl', lang))
        upload_type = st.radio(t("wa_input_method", lang), [t("wa_paste_opt", lang), t("wa_upload_opt", lang)], horizontal=True)
        
        raw_input = ""
        if upload_type == t("wa_paste_opt", lang):
            raw_input = st.text_area(t("wa_paste_opt", lang), height=100, placeholder="054...")
        else:
            uploaded_file = st.file_uploader(t("wa_upload_opt", lang), type=["xlsx", "txt", "csv"])
            if uploaded_file:
                raw_input = "File Uploaded" # Placeholder for logic

        if raw_input:
            v_sa, v_ph, invalid = validate_numbers(raw_input)
            st.session_state.wa_active_numbers = v_sa + v_ph
            st.success(f"{t('wa_saudi', lang)}: {len(v_sa)} | {t('wa_philippines', lang)}: {len(v_ph)}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader(t('wa_step2_lbl', lang))
        msg_text = st.text_area(t("wa_msg_body", lang), height=100)
        delay = st.slider(t("wa_delay_lbl", lang), 2, 60, 5)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader(t('wa_step3_lbl', lang))
        if st.session_state.wa_running:
            if st.button(t("wa_stop_btn", lang), type="primary", use_container_width=True):
                st.session_state.wa_running = False
                st.rerun()
        else:
            if st.button(t("wa_start_btn", lang), use_container_width=True):
                if status == "Connected" and st.session_state.wa_active_numbers and msg_text:
                    st.session_state.wa_running = True
                    st.rerun()
        
        if st.session_state.wa_running:
            # Broadcast Loop logic
            st.info("Broadcasting...")
            st.session_state.wa_running = False # Temporary
            
        if st.session_state.wa_logs:
            st.markdown('<div class="wa-log">', unsafe_allow_html=True)
            for l in reversed(st.session_state.wa_logs): st.write(l)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
