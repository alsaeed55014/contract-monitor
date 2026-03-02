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
        .wa-status-connected {{ color: #00FF41; font-weight: bold; font-size: 1.5rem; text-shadow: 0 0 10px rgba(0, 255, 65, 0.5); }}
        .wa-log-box {{
            font-family: 'Consolas', monospace;
            background: rgba(0,0,0,0.5);
            padding: 15px;
            border-radius: 12px;
            max-height: 200px;
            overflow-y: auto;
            color: #00FF41;
            font-size: 0.85rem;
            margin-top: 15px;
            border: 1px solid #333;
        }}
        .wa-qr-hd-box {{
            background: white !important; 
            padding: 25px !important; 
            border-radius: 20px;
            display: inline-block;
            box-shadow: 0 0 35px rgba(255,255,255,0.9);
            border: 5px solid #25D366;
        }}
    </style>
    """

def render_whatsapp_page():
    lang = st.session_state.get('lang', 'ar')
    st.markdown(get_whatsapp_ui_css(lang), unsafe_allow_html=True)
    is_cloud = "/mount/" in __file__
    
    # Initialize state for Pasha
    if 'wa_service' not in st.session_state:
        st.session_state.wa_service = WhatsAppService()
    if 'wa_logs' not in st.session_state: st.session_state.wa_logs = []
    if 'wa_running' not in st.session_state: st.session_state.wa_running = False
    if 'wa_sent_count' not in st.session_state: st.session_state.wa_sent_count = 0

    st.markdown(f'<div class="wa-container">', unsafe_allow_html=True)
    st.markdown(f'<h1 style="color:#D4AF37; text-align:center; font-family:Serif;">{t("wa_title", lang)}</h1>', unsafe_allow_html=True)

    status = st.session_state.wa_service.get_status()

    # --- TOP STATUS SECTION ---
    st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        if status == "Connected":
            st.markdown(f'<span class="wa-status-connected">✅ {t("wa_online", lang)}</span>', unsafe_allow_html=True)
        elif status == "Awaiting Login":
            st.warning(f"⚠️ {t('wa_ready', lang)}")
        else:
            st.error(f"❌ {t('wa_offline', lang)}")
    with c2:
        if status != "Disconnected":
            if st.button(t("wa_disconnect", lang), use_container_width=True):
                st.session_state.wa_service.close()
                st.rerun()
        else:
            if st.button(t("wa_launch_btn", lang), type="primary", use_container_width=True):
                with st.spinner("Launching Engine..."):
                    st.session_state.wa_service.start_driver(headless=is_cloud)
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- QR SCAN SECTION (Shown only if not connected) ---
    if status == "Awaiting Login":
        st.markdown('<div style="text-align:center; margin:30px 0;">', unsafe_allow_html=True)
        st.markdown('<div class="wa-qr-hd-box">', unsafe_allow_html=True)
        qr_hd = st.session_state.wa_service.get_qr_hd()
        if qr_hd:
            st.image(qr_hd, width=350)
            st.caption("Scan with your phone to start broadcasting")
            time.sleep(8)
            st.rerun()
        else:
            st.info("Generating Secure Code...")
            time.sleep(3)
            st.rerun()
        st.markdown('</div></div>', unsafe_allow_html=True)

    # --- MAIN CONTROLS (Only if Connected) ---
    if status == "Connected":
        col_input, col_msg = st.columns(2)
        
        with col_input:
            st.markdown(f'<div class="wa-glass-card">', unsafe_allow_html=True)
            st.subheader(t("wa_step1_lbl", lang))
            
            # File Upload Logic
            file_up = st.file_uploader(t("wa_upload_opt", lang), type=['xlsx', 'csv', 'txt'])
            raw_text = st.text_area(t("wa_paste_opt", lang), height=100, placeholder="054..., +63...")
            
            numbers_to_process = ""
            if file_up:
                if file_up.name.endswith('.xlsx'):
                    df = pd.read_excel(file_up)
                    # Try to find a column with numbers
                    phone_cols = [c for c in df.columns if any(kw in str(c).lower() for kw in ['phone', 'num', 'mob', 'هاتف', 'جوال'])]
                    if phone_cols: numbers_to_process = "\n".join(df[phone_cols[0]].astype(str).tolist())
                else:
                    numbers_to_process = file_up.read().decode('utf-8')
            elif raw_text:
                numbers_to_process = raw_text

            v_sa, v_ph, invalid = validate_numbers(numbers_to_process)
            all_valid = v_sa + v_ph
            
            if all_valid:
                st.success(f"✅ {len(v_sa)} Saudi | {len(v_ph)} Philippines")
                if invalid: st.warning(f"⚠️ Skipped {len(invalid)} invalid entries")
            
            st.markdown('</div>', unsafe_allow_html=True)

        with col_msg:
            st.markdown(f'<div class="wa-glass-card">', unsafe_allow_html=True)
            st.subheader(t("wa_step2_lbl", lang))
            message_body = st.text_area(t("wa_msg_body", lang), height=150)
            broadcast_delay = st.slider(t("wa_delay_lbl", lang), 2, 60, 5)
            st.markdown('</div>', unsafe_allow_html=True)

        # --- ACTION AREA ---
        st.markdown(f'<div class="wa-glass-card" style="text-align:center;">', unsafe_allow_html=True)
        if st.session_state.wa_running:
            if st.button(f"🛑 {t('wa_stop_btn', lang)}", type="primary", use_container_width=True):
                st.session_state.wa_running = False
                st.rerun()
        else:
            can_send = all_valid and message_body
            if st.button(f"🚀 {t('wa_start_btn', lang)}", disabled=not can_send, use_container_width=True):
                st.session_state.wa_running = True
                st.session_state.wa_sent_count = 0
                st.rerun()
        
        # Broadcast Loop Logic
        if st.session_state.wa_running and all_valid:
            progress_bar = st.progress(st.session_state.wa_sent_count / len(all_valid))
            
            if st.session_state.wa_sent_count < len(all_valid):
                current_phone = all_valid[st.session_state.wa_sent_count]
                st.write(f"Sending to: {current_phone}...")
                
                success, info = st.session_state.wa_service.send_message(current_phone, message_body)
                
                status_icon = "✅" if success else "❌"
                log_text = f"[{datetime.now().strftime('%H:%M:%S')}] {status_icon} {current_phone}: {info}"
                st.session_state.wa_logs.append(log_text)
                
                st.session_state.wa_sent_count += 1
                
                if st.session_state.wa_sent_count == len(all_valid):
                    st.session_state.wa_running = False
                    st.balloons()
                    st.success("Broadcast Completed!")
                
                time.sleep(broadcast_delay)
                st.rerun()

        # Logs
        if st.session_state.wa_logs:
            st.markdown('<div class="wa-log-box">', unsafe_allow_html=True)
            for entry in reversed(st.session_state.wa_logs):
                st.text(entry)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
