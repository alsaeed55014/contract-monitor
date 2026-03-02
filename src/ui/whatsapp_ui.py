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
    
    # Initialize Pasha's Service correctly
    if 'wa_service' not in st.session_state:
        st.session_state.wa_service = WhatsAppService()
    if 'wa_logs' not in st.session_state: st.session_state.wa_logs = []
    if 'wa_running' not in st.session_state: st.session_state.wa_running = False
    if 'wa_idx' not in st.session_state: st.session_state.wa_idx = 0

    st.markdown(f'<h1 style="color:#D4AF37; text-align:center;">جناح واتساب الفاخر 2026 🚀</h1>', unsafe_allow_html=True)

    # UI Section for Diagnostic Screenshot for Pasha
    with st.expander("🛠️ Pasha's Diagnostic Center"):
        if st.button("📸 Capture Diagnostic Screenshot"):
            img = st.session_state.wa_service.get_diagnostic_screenshot()
            if img: st.image(f"data:image/png;base64,{img}")
            else: st.warning("Browser Offline")

    # 1. Connection and Status
    status = st.session_state.wa_service.get_status()
    st.markdown('<div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:20px;">', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        if status == "Connected": st.success(f"✅ متصل بالواتساب يا باشا")
        elif status == "Awaiting Login": st.warning(f"⚠️ في انتظار المسح يا باشا")
        elif status == "Loading...": st.info(f"⏳ جاري تحميل المحرك... برجاء الانتظار دقيقة")
        else: st.error(f"❌ المحرك غير نشط حالياً")
    with c2:
        # Pasha can restart anytime
        if st.button("🔄 Restart & Fix Engine", type="primary", use_container_width=True):
            with st.spinner("Re-initializing Pasha's Engine..."):
                st.session_state.wa_service.close()
                ok, msg = st.session_state.wa_service.start_driver(headless=is_cloud)
                if ok: st.success("Pasha! System Ready")
                else: st.error(msg)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. QR Code (Only if waiting)
    if status == "Awaiting Login":
        st.markdown('<div style="text-align:center; padding:15px; background:white; border-radius:15px; margin-bottom:15px;">', unsafe_allow_html=True)
        qr = st.session_state.wa_service.get_qr_hd()
        if qr:
            st.image(qr, width=300)
            st.caption("Pasha! Please scan this code within 20 seconds")
            time.sleep(12)
            st.rerun()
        else:
            st.info("Pasha! Generating Ultra-HD QR Code...")
            time.sleep(5)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. Message Form (Forms for Pasha)
    st.markdown("---")
    col_input, col_msg = st.columns(2)
    with col_input:
        st.markdown("### 📝 إدارة المستلمين")
        txt_in = st.text_area("ألصق الأرقام هنا (Pasha Mode)", height=150, placeholder="054...")
        v_sa, v_ph, _ = validate_numbers(txt_in)
        all_v = v_sa + v_ph
        if all_v: st.success(f"المستلمون الجاهزون: {len(all_v)}")
    
    with col_msg:
        st.markdown("### ✉️ إنشاء الرسالة")
        msg_body = st.text_area("نص الرسالة النهائي", height=150)
        delay = st.slider("التأخير بين الرسائل (بالثواني)", 2, 60, 5)

    # 4. BROADCAST ACTION
    st.markdown("---")
    if st.session_state.wa_running:
        if st.button("🛑 إيقاف البث لـ معاليك يا باشا", type="primary", use_container_width=True):
            st.session_state.wa_running = False; st.rerun()
    else:
        # Button is enabled if Pasha is connected and has numbers
        pasha_ready = (status == "Connected") and len(all_v) > 0 and msg_body.strip() != ""
        if st.button(f"🚀 بدء البث الذكي لـ معاليك يا باشا 🔥", disabled=not pasha_ready, use_container_width=True):
            st.session_state.wa_running = True
            st.session_state.wa_idx = 0
            st.rerun()

    # 5. EXECUTION ENGINE
    if st.session_state.wa_running and all_v:
        # Pasha's progress indicator
        st.progress(st.session_state.wa_idx / len(all_v))
        if st.session_state.wa_idx < len(all_v):
            curr_target = all_v[st.session_state.wa_idx]
            st.info(f"⏳ جاري الإرسال لـ معاليك يا باشا: {curr_target}...")
            
            # Send using Pasha's keyboard emulation method
            ok, info = st.session_state.wa_service.send_message(curr_target, msg_body)
            
            log_icon = "✅" if ok else "❌"
            st.session_state.wa_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_icon} {curr_target}: {info}")
            st.session_state.wa_idx += 1
            
            if st.session_state.wa_idx == len(all_v):
                st.session_state.wa_running = False; st.balloons()
            
            time.sleep(delay)
            st.rerun()

    # 6. LOGS PANEL
    if st.session_state.wa_logs:
        st.markdown('<div style="background:rgba(0,0,0,0.8); padding:10px; border-radius:10px; color:#00FF41; max-height:200px; overflow-y:auto; font-family:monospace;">', unsafe_allow_html=True)
        for log in reversed(st.session_state.wa_logs):
            st.text(log)
        st.markdown('</div>', unsafe_allow_html=True)
