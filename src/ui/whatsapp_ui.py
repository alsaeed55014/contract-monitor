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
        .wa-status-connected {{ color: #00FF41; font-weight: bold; font-size: 1.5rem; text-shadow: 0 0 10px rgba(0, 255, 65, 0.5); }}
        .wa-log-box {{
            font-family: 'Consolas', monospace;
            background: rgba(0,0,0,0.8);
            padding: 15px; border-radius: 12px;
            max-height: 250px; overflow-y: auto; color: #00FF41;
            font-size: 0.9rem; line-height: 1.4;
        }}
    </style>
    """

def render_whatsapp_page():
    lang = st.session_state.get('lang', 'ar')
    st.markdown(get_whatsapp_ui_css(lang), unsafe_allow_html=True)
    is_cloud = "/mount/" in __file__
    
    # PASHA'S AUTO-HEAL LOGIC: Check if object is old or missing 'send_message'
    if 'wa_service' not in st.session_state or not hasattr(st.session_state.wa_service, 'send_message'):
        if 'wa_service' in st.session_state:
            try: st.session_state.wa_service.close()
            except: pass
        st.session_state.wa_service = WhatsAppService()
    
    if 'wa_logs' not in st.session_state: st.session_state.wa_logs = []
    if 'wa_running' not in st.session_state: st.session_state.wa_running = False
    if 'wa_sent_idx' not in st.session_state: st.session_state.wa_sent_idx = 0

    st.markdown(f'<div class="wa-container">', unsafe_allow_html=True)
    st.markdown(f'<h1 style="color:#D4AF37; text-align:center;">{t("wa_title", lang)}</h1>', unsafe_allow_html=True)

    status = st.session_state.wa_service.get_status()

    # --- Header Control ---
    st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        if status == "Connected": st.markdown(f'<span class="wa-status-connected">✅ {t("wa_online", lang)}</span>', unsafe_allow_html=True)
        elif status == "Awaiting Login": st.warning(f"⚠️ {t('wa_ready', lang)}")
        else: st.error(f"❌ {t('wa_offline', lang)}")
    with c2:
        if status != "Disconnected":
            if st.button(t("wa_disconnect", lang), use_container_width=True):
                st.session_state.wa_service.close()
                st.rerun()
        else:
            if st.button(t("wa_launch_btn", lang), type="primary", use_container_width=True):
                st.session_state.wa_service.start_driver(headless=is_cloud)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if status == "Awaiting Login":
        qr = st.session_state.wa_service.get_qr_hd()
        if qr:
            st.markdown(f'<div style="text-align:center;"><div style="background:white; padding:20px; display:inline-block; border-radius:15px; border:5px solid #25D366;"><img src="{qr}" style="width:300px;"></div></div>', unsafe_allow_html=True)
            time.sleep(10); st.rerun()
        else:
            st.info("Preparing QR Data..."); time.sleep(4); st.rerun()

    if status == "Connected":
        # Form
        col_input, col_msg = st.columns(2)
        all_nums = []
        with col_input:
            st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
            st.subheader(t("wa_step1_lbl", lang))
            txt_in = st.text_area(t("wa_paste_opt", lang), placeholder="054..., +66...", height=150)
            v_sa, v_ph, _ = validate_numbers(txt_in)
            all_nums = v_sa + v_ph
            if all_nums: st.success(f"Recipients: {len(all_nums)}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_msg:
            st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
            st.subheader(t("wa_step2_lbl", lang))
            msg_body = st.text_area(t("wa_msg_body", lang), height=150)
            delay = st.slider(t("wa_delay_lbl", lang), 2, 60, 5)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="wa-glass-card" style="text-align:center;">', unsafe_allow_html=True)
        if st.session_state.wa_running:
            if st.button(f"🛑 {t('wa_stop_btn', lang)}", type="primary", use_container_width=True):
                st.session_state.wa_running = False
                st.rerun()
        else:
            if st.button(f"🚀 {t('wa_start_btn', lang)}", disabled=not (all_nums and msg_body), use_container_width=True):
                st.session_state.wa_running = True
                st.session_state.wa_sent_idx = 0
                st.rerun()

        if st.session_state.wa_running and all_nums:
            st.progress(st.session_state.wa_sent_idx / len(all_nums))
            if st.session_state.wa_sent_idx < len(all_nums):
                curr = all_nums[st.session_state.wa_sent_idx]
                st.write(f"Broadcasting to Pasha's list: {curr}...")
                
                # SAFE CALL
                success, info = st.session_state.wa_service.send_message(curr, msg_body)
                
                icon = "✅" if success else "❌"
                st.session_state.wa_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {icon} {curr}: {info}")
                st.session_state.wa_sent_idx += 1
                
                if st.session_state.wa_sent_idx == len(all_nums):
                    st.session_state.wa_running = False; st.balloons()
                
                time.sleep(delay); st.rerun()

        if st.session_state.wa_logs:
            st.markdown('<div class="wa-log-box">', unsafe_allow_html=True)
            for l in reversed(st.session_state.wa_logs): st.text(l)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
