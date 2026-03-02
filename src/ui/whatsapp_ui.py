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
            direction: {direction};
        }}
        .wa-status-connected {{ color: #00FF41; font-weight: bold; font-size: 1.4rem; text-shadow: 0 0 10px rgba(0, 255, 65, 0.5); }}
        .wa-status-loading {{ color: #D4AF37; animation: pulse 1.5s infinite; }}
        @keyframes pulse {{ 0% {{ opacity: 0.6; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.6; }} }}
        
        /* QR Code Enhancement for High-Speed Scanning */
        .wa-qr-box {{
            background: white !important; 
            padding: 40px !important; /* Increased White Space (Quiet Zone) */
            border-radius: 30px;
            display: inline-block;
            box-shadow: 0 0 40px rgba(255,255,255,0.7);
            border: 5px solid #f0f0f0;
        }}
        .wa-qr-box img {{
            image-rendering: pixelated; /* Makes the barcode dots sharper */
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

    # Sidebar Reset Button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Reset WhatsApp Engine", key="reset_wa_glob_2"):
        st.session_state.wa_service.close()
        st.session_state.wa_service = WhatsAppService()
        st.sidebar.success("Engine Re-initialized")
        st.rerun()

    st.markdown(f'<div class="wa-container">', unsafe_allow_html=True)
    st.markdown(f'''<div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #D4AF37;">{t('wa_title', lang)}</h1>
        <p style="color: #888;">{t('wa_subtitle', lang)}</p>
    </div>''', unsafe_allow_html=True)

    col_status, col_main = st.columns([1, 2.3])
    
    with col_status:
        st.markdown(f'<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader(t('wa_status_lbl', lang))
        
        status = st.session_state.wa_service.get_status()
        
        if status == "Connected":
            st.markdown(f'<div style="text-align:center;"><span class="wa-status-connected">✅ {t("wa_online", lang)}</span></div>', unsafe_allow_html=True)
            if st.button(t("wa_disconnect", lang), use_container_width=True):
                st.session_state.wa_service.close()
                st.rerun()
        elif status == "Awaiting Login":
            st.markdown(f'Status: <span class="wa-status-loading">{t("wa_ready", lang)}</span>', unsafe_allow_html=True)
            qr_b64 = st.session_state.wa_service.get_qr_base64()
            if qr_b64:
                st.markdown('<div style="text-align:center; margin-top:15px;">', unsafe_allow_html=True)
                st.markdown('<div class="wa-qr-box">', unsafe_allow_html=True)
                # Displaying QR larger (320px) with sharp rendering
                st.image(f"data:image/png;base64,{qr_b64}", width=320)
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.caption("Point your phone at this QR code. It will auto-refresh when connected.")
                time.sleep(5)
                st.rerun()
            else:
                st.warning("QR Code generating... please wait")
                time.sleep(3)
                st.rerun()
        elif status == "Loading...":
            st.markdown(f'Status: <span class="wa-status-loading">{t("wa_loading", lang)}</span>', unsafe_allow_html=True)
            time.sleep(3)
            st.rerun()
        else:
            st.markdown(f'Status: <span class="wa-status-disconnected">{t("wa_offline", lang)}</span>', unsafe_allow_html=True)
            if st.button(t("wa_launch_btn", lang), use_container_width=True):
                with st.spinner("Starting Secure Engine..."):
                    st.session_state.wa_service.start_driver(headless=is_cloud)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        # Standard Main Section
        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader(t('wa_step1_lbl', lang))
        raw_text = st.text_area(t("wa_paste_opt", lang), placeholder="054..., +63...")
        if raw_text:
            v_sa, v_ph, invalid = validate_numbers(raw_text)
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
        if status == "Connected" and st.session_state.wa_active_numbers and msg_text:
            if st.button(t("wa_start_btn", lang), use_container_width=True):
                # We'll implement actual loop in next step if this works
                st.info("Broadcast engine sequence ready!")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
