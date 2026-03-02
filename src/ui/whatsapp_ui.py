import streamlit as st
import pandas as pd
import time
import re
from datetime import datetime
from src.services.whatsapp_service import WhatsAppService
from src.utils.phone_utils import validate_numbers, format_phone_number
from src.core.i18n import t

def render_whatsapp_page():
    lang = st.session_state.get('lang', 'ar')
    is_cloud = "/mount/" in __file__
    
    if 'wa_service' not in st.session_state:
        st.session_state.wa_service = WhatsAppService()
    if 'wa_logs' not in st.session_state: st.session_state.wa_logs = []
    if 'wa_running' not in st.session_state: st.session_state.wa_running = False
    if 'wa_idx' not in st.session_state: st.session_state.wa_idx = 0
    if 'wa_data' not in st.session_state: st.session_state.wa_data = None

    # LUXURY SIGNATURE
    st.markdown('<div class="programmer-signature-neon">Masterpiece By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)
    st.markdown(f'<h1 style="color:#D4AF37; text-align:center; font-family:Cairo, sans-serif;">🚀 خبير الواتساب العالمي لـ معاليك 2026</h1>', unsafe_allow_html=True)

    # 1. Connection and Status
    status = st.session_state.wa_service.get_status()
    st.markdown('<div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:15px; border:1px solid rgba(212,175,55,0.3); margin-bottom:20px;">', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        if status == "Connected": st.success(f"✅ معاليك متصل وجاهز للإرسال!")
        elif status == "Awaiting Login": st.warning(f"⚠️ الباركود جاهز.. يرجى المسح يا باشا")
        elif status == "Loading...": st.info(f"⏳ جاري تجهيز المحرك العالمي لـ معاليك...")
        else: st.error(f"❌ المحرك متوقف حالياً")
    with c2:
        if st.button("🔄 Restart Pasha Engine", type="primary", use_container_width=True):
            with st.spinner("Re-launching Global Engine..."):
                st.session_state.wa_service.close()
                ok, msg = st.session_state.wa_service.start_driver(headless=is_cloud)
                if ok: st.toast("✅ Engine Ready!")
                else: st.error(msg)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. SCAN HUB (Ultra HD QR Isolation)
    if status == "Awaiting Login":
        st.markdown("""
        <style>
        .qr-pasha-container { 
            background: white !important; 
            padding: 40px !important; 
            border-radius: 30px !important; 
            box-shadow: 0 0 50px rgba(255,255,255,0.5) !important; 
            display: flex; justify-content: center; align-items: center; 
            margin: 20px auto; max-width: 450px; border: 10px solid #D4AF37;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="qr-pasha-container">', unsafe_allow_html=True)
        qr_base64 = st.session_state.wa_service.get_qr_hd()
        if qr_base64:
            st.image(f"data:image/png;base64,{qr_base64}", width=300)
            st.markdown('</div>', unsafe_allow_html=True)
            st.info("Pasha! Scan now... Auto-Refresh in 12s")
            time.sleep(12); st.rerun()
        else:
            st.info("Generating QR... Please wait 5s")
            time.sleep(5); st.rerun()
        
    # 3. Input Form
    if status == "Connected":
        st.markdown("---")
        t_manual, t_xl = st.tabs(["🔢 أرقام يدوية", "📊 ملف إكسل (تصدير البرنامج)"])
        
        manual_list = []
        with t_manual:
            txt_nums = st.text_area("ألصق الأرقام هنا (Pasha Style)", height=100, placeholder="+20...")
            manual_list, _, _ = validate_numbers(txt_nums)
            if manual_list: st.success(f"جاهز لـ {len(manual_list)} رقم")

        with t_xl:
            uploaded = st.file_uploader("ارفع الملف الذهبي لـ معاليك", type=["xlsx"])
            if uploaded:
                df = pd.read_excel(uploaded)
                st.session_state.wa_data = df
                st.success(f"تم تحميل {len(df)} عامل بنجاح يا باشا ✅")
        
        # Target Extraction Logic
        final_targets = []
        if uploaded and st.session_state.wa_data is not None:
            df = st.session_state.wa_data
            def find_c(keys):
                for c in df.columns:
                    if any(k in str(c).lower() for k in keys): return c
                return None
            c_name = find_c(["اسم", "name", "полное"])
            c_phone = find_c(["واتساب", "رقم", "هاتف", "phone", "جوال"])
            c_cv = find_c(["سيرة", "cv", "resume", "link"])
            
            for _, row in df.iterrows():
                phone = format_phone_number(row[c_phone]) if c_phone else None
                if phone:
                    final_targets.append({
                        'phone': phone,
                        'name': str(row[c_name]) if c_name else "Client",
                        'cv': str(row[c_cv]) if c_cv else ""
                    })
        elif manual_list:
            for n in manual_list:
                final_targets.append({'phone': n, 'name': 'Pasha Customer', 'cv': ''})

        # Message Preview
        st.markdown("### ✍️ نص الرسالة القوي")
        st.info("💡 استخدم {الاسم} لاسم العامل و {السيرة} لرابط سيرته الذاتية")
        msg_body = st.text_area("اكتب رسالتك لـ معاليك هنا", height=150, 
                               value="مرحبا {الاسم},\nهذه رسالة من مجموعة السعيد الوزان.\nرابط ملفك: {السيرة}")
        delay = st.slider("مهلة الإرسال (ثانية)", 5, 120, 15)

        # START ACTION
        st.markdown("---")
        if st.session_state.wa_running:
            if st.button("🛑 إيقاف فوري لـ معاليك", type="primary", use_container_width=True):
                st.session_state.wa_running = False; st.rerun()
        else:
            ready = len(final_targets) > 0 and msg_body.strip() != ""
            if st.button(f"🔥 بدء البث الشامل لـ {len(final_targets)} مستلم يا باشا 🚀", disabled=not ready, use_container_width=True):
                st.session_state.wa_running = True
                st.session_state.wa_idx = 0
                st.rerun()

        # RUNNER
        if st.session_state.wa_running and final_targets:
            st.progress(st.session_state.wa_idx / len(final_targets))
            if st.session_state.wa_idx < len(final_targets):
                trg = final_targets[st.session_state.wa_idx]
                p = trg['phone']
                n = trg['name']
                v = trg['cv']
                
                final_msg = msg_body.replace("{الاسم}", n).replace("{name}", n).replace("{السيرة}", v).replace("{cv}", v)
                
                st.info(f"⏳ جاري الإرسال لـ معاليك: {n} ({p})...")
                ok, log = st.session_state.wa_service.send_message(p, final_msg)
                
                icon = "✅" if ok else "❌"
                st.session_state.wa_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {icon} {n}: {log}")
                st.session_state.wa_idx += 1
                
                if st.session_state.wa_idx == len(final_targets):
                    st.session_state.wa_running = False; st.balloons()
                
                time.sleep(delay)
                st.rerun()

        # LOGS
        if st.session_state.wa_logs:
            with st.expander("📄 أرشيف الإرسال اللحظي لـ معاليك", expanded=True):
                st.markdown('<div style="background:rgba(0,0,0,0.8); padding:10px; border-radius:10px; color:#00FF41; max-height:300px; overflow-y:auto; font-family:monospace;">', unsafe_allow_html=True)
                for log_text in reversed(st.session_state.wa_logs):
                    st.text(log_text)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Diagnostic Tool for Pasha if not connected
        with st.expander("🛠️ Pasha's Diagnostic Center"):
            if st.button("📸 Capture Diagnostic Screenshot"):
                img = st.session_state.wa_service.get_diagnostic_screenshot()
                if img: st.image(f"data:image/png;base64,{img}")
                else: st.warning("Browser Offline")
