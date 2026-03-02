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
            padding: 25px !important; 
            border-radius: 20px;
            display: inline-block;
            box-shadow: 0 0 35px rgba(255,255,255,0.9);
            border: 1px solid #eee;
        }}
        .wa-qr-hd-container img {{
            image-rendering: pixelated;
            image-rendering: crisp-edges;
        }}
    </style>
    """

def render_whatsapp_page():
    lang = st.session_state.get('lang', 'ar')
    st.markdown(get_whatsapp_ui_css(lang), unsafe_allow_html=True)
    is_cloud = "/mount/" in __file__
    
    # ADVANCED AUTO-FIX: Force refresh if object is stale
    if 'wa_service' not in st.session_state or not hasattr(st.session_state.wa_service, 'get_qr_data_url'):
        if 'wa_service' in st.session_state:
            try: st.session_state.wa_service.close()
            except: pass
        st.session_state.wa_service = WhatsAppService()
        st.session_state.wa_logs = []
        st.session_state.wa_active_numbers = []

    with st.sidebar:
        st.markdown("---")
        if st.button("🧼 Deep Clean Factory Reset", key="clean_btn_final"):
            st.session_state.wa_service.close()
            del st.session_state['wa_service']
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
            st.markdown(f'Status: <span class="wa-status-loading">SCAN QR NOW</span>', unsafe_allow_html=True)
            
            # Safe call with error handling
            qr_hd = None
            try: qr_hd = st.session_state.wa_service.get_qr_data_url()
            except: pass
            
            if qr_hd:
                st.markdown('<div style="text-align:center; margin-top:20px;">', unsafe_allow_html=True)
                st.markdown('<div class="wa-qr-hd-container">', unsafe_allow_html=True)
                st.image(qr_hd, width=280)
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                time.sleep(5)
                st.rerun()
            else:
                st.warning("QR Code is generating... please wait")
                time.sleep(3)
                st.rerun()
        elif status == "Loading...":
            st.markdown('<span class="wa-status-loading">Loading WhatsApp Web...</span>', unsafe_allow_html=True)
            time.sleep(3)
            st.rerun()
        else:
            if st.button(t("wa_launch_btn", lang), use_container_width=True):
                with st.spinner("Connecting to Server..."):
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
            st.success(f"Recipients: {len(st.session_state.wa_active_numbers)}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader(t('wa_step2_lbl', lang))
        msg = st.text_area("Message Content")
        st.markdown('</div>', unsafe_allow_html=True)

        if status == "Connected" and st.session_state.wa_active_numbers and msg:
            if st.button("🚀 EXECUTE BROADCAST", use_container_width=True):
                st.info("Broadcast sequence starting...")
    st.markdown('</div>', unsafe_allow_html=True)
