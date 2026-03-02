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
        }}
        .wa-status-connected {{ color: #00FF41; font-weight: bold; font-size: 1.4rem; }}
        .wa-status-loading {{ color: #D4AF37; animation: pulse 1.5s infinite; }}
        @keyframes pulse {{ 0% {{ opacity: 0.6; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.6; }} }}
        
        .wa-qr-hd-container {{
            background: white !important; 
            padding: 30px !important; 
            border-radius: 25px;
            display: inline-block;
            box-shadow: 0 0 30px rgba(255,255,255,0.8);
            border: 2px solid #ddd;
        }}
        .wa-qr-hd-container img {{
            image-rendering: -webkit-optimize-contrast;
            image-rendering: crisp-edges;
        }}
    </style>
    """

def render_whatsapp_page():
    lang = st.session_state.get('lang', 'ar')
    st.markdown(get_whatsapp_ui_css(lang), unsafe_allow_html=True)
    is_cloud = "/mount/" in __file__
    
    if 'wa_service' not in st.session_state:
        st.session_state.wa_service = WhatsAppService()
        st.session_state.wa_logs = []

    # Sidebar Tools
    with st.sidebar:
        st.markdown("---")
        if st.button("🔄 Clean Driver & Reset", key="cln_wa"):
            st.session_state.wa_service.close()
            st.session_state.wa_service = WhatsAppService()
            st.success("Clean Reset Done")
            st.rerun()

    st.markdown(f'<div class="wa-container">', unsafe_allow_html=True)
    st.markdown(f'<h1 style="color:#D4AF37; text-align:center;">{t("wa_title", lang)}</h1>', unsafe_allow_html=True)

    col_status, col_main = st.columns([1, 2.3])
    
    with col_status:
        st.markdown(f'<div class="wa-glass-card">', unsafe_allow_html=True)
        status = st.session_state.wa_service.get_status()
        
        if status == "Connected":
            st.markdown(f'<div style="text-align:center;"><span class="wa-status-connected">✅ {t("wa_online", lang)}</span></div>', unsafe_allow_html=True)
            if st.button(t("wa_disconnect", lang), use_container_width=True):
                st.session_state.wa_service.close()
                st.rerun()
        elif status == "Awaiting Login":
            st.markdown(f'Status: <span class="wa-status-loading">READY FOR SCAN</span>', unsafe_allow_html=True)
            qr_full_data = st.session_state.wa_service.get_qr_data_url()
            if qr_full_data:
                st.markdown('<div style="text-align:center; margin-top:20px;">', unsafe_allow_html=True)
                st.markdown('<div class="wa-qr-hd-container">', unsafe_allow_html=True)
                # Display direct data URL
                st.image(qr_full_data, width=300)
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                time.sleep(6) # Auto refresh to detect login
                st.rerun()
            else:
                st.warning("Fetching HD Code...")
                time.sleep(3)
                st.rerun()
        elif status == "Loading...":
            st.markdown('<span class="wa-status-loading">Engine Loading...</span>', unsafe_allow_html=True)
            time.sleep(3)
            st.rerun()
        else:
            if st.button(t("wa_launch_btn", lang), use_container_width=True):
                st.session_state.wa_service.start_driver(headless=is_cloud)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader(t('wa_step1_lbl', lang))
        raw_text = st.text_area(t("wa_paste_opt", lang), placeholder="Numbers here...")
        if raw_text:
            v_sa, v_ph, _ = validate_numbers(raw_text)
            st.session_state.wa_active_numbers = v_sa + v_ph
            st.success(f"Total valid: {len(st.session_state.wa_active_numbers)}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader(t('wa_step2_lbl', lang))
        msg = st.text_area("Message Text")
        st.markdown('</div>', unsafe_allow_html=True)

        if status == "Connected" and st.session_state.wa_active_numbers and msg:
            if st.button("🔥 START BROADCAST", use_container_width=True):
                st.info("Starting loop...")
    st.markdown('</div>', unsafe_allow_html=True)
