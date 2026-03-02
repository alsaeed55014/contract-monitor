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

    st.markdown(f'<h1 style="color:#D4AF37; text-align:center;">جناح واتساب الفاخر 2026 🚀</h1>', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:center; color:#888; margin-bottom:20px;">{"نظام البث الذكي لـ معاليك يا باشا" if lang == "ar" else "Smart Broadcast for Pasha"}</div>', unsafe_allow_html=True)

    # 1. Connection and Status
    status = st.session_state.wa_service.get_status()
    st.markdown('<div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:20px; border:1px solid rgba(212,175,55,0.2);">', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        if status == "Connected": st.success(f"✅ متصل بالواتساب يا باشا")
        elif status == "Awaiting Login": st.warning(f"⚠️ في انتظار المسح يا باشا")
        elif status == "Loading...": st.info(f"⏳ جاري تحميل المحرك... برجاء الانتظار دقيقة")
        else: st.error(f"❌ المحرك غير نشط حالياً")
    with c2:
        if st.button("🔄 Restart & Fix Engine", type="primary", use_container_width=True):
            with st.spinner("Re-initializing Pasha's Engine..."):
                st.session_state.wa_service.close()
                ok, msg = st.session_state.wa_service.start_driver(headless=is_cloud)
                if ok: st.success("Pasha! System Ready")
                else: st.error(msg)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. QR Code
    if status == "Awaiting Login":
        st.markdown('<div style="text-align:center; padding:15px; background:white; border-radius:15px; margin-bottom:15px;">', unsafe_allow_html=True)
        qr = st.session_state.wa_service.get_qr_hd()
        if qr:
            st.image(qr, width=300)
            st.caption("Pasha! Please scan this code")
            time.sleep(10); st.rerun()
        else:
            st.info("Generating QR Code...")
            time.sleep(5); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. Input Management (EXCEL SUPPORT)
    st.markdown("---")
    tab_bulk, tab_excel = st.tabs(["🔢 إدخال يدوي", "📊 رفع ملف Excel (Pasha Mode)"])
    
    with tab_bulk:
        txt_in = st.text_area("ألصق الأرقام هنا", height=120, placeholder="054...")
        manual_nums, _, _ = validate_numbers(txt_in)
        if manual_nums: st.caption(f"جاهز للإرسال لـ {len(manual_nums)} رقم")

    with tab_excel:
        uploaded_file = st.file_uploader("ارفع ملف الإكسل المصدر من البرنامج يا باشا", type=["xlsx"])
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                st.session_state.wa_data = df
                st.dataframe(df.head(), use_container_width=True)
                st.success(f"تم تحميل {len(df)} عامل من الملف يا باشا ✅")
            except Exception as e:
                st.error(f"خطأ في قراءة الملف: {e}")

    # 4. Message Design
    st.markdown("### ✉️ تصميم الرسالة الذكية")
    msg_help = "Pasha! Use {name} for worker name and {cv} for resume link."
    msg_help_ar = "يا باشا! استخدم {الاسم} لاسم العامل و {السيرة} لرابط السيرة الذاتية."
    st.info(msg_help_ar if lang == 'ar' else msg_help)
    
    msg_body = st.text_area("نص الرسالة (يدعم التاغات الذكية)", height=150, 
                           value="Hello {الاسم},\nWelcome to Pasha Group.\nYour CV: {السيرة}" if lang == 'ar' else "Hello {name},\nWelcome to Pasha Group.\nYour CV: {cv}")
    delay = st.slider("التأخير بين الرسائل (ثواني)", 5, 120, 15)

    # 5. PREVIEW & RUN
    st.markdown("---")
    
    # Identify final targets
    final_targets = []
    if uploaded_file and st.session_state.wa_data is not None:
        # Excel Mode
        df = st.session_state.wa_data
        # Simple mapping
        def find_c(keys):
            for c in df.columns:
                if any(k in str(c).lower() for k in keys): return c
            return None
        
        c_name = find_c(["اسم", "name", "full name"])
        c_phone = find_c(["هاتف", "phone", "جوال", "whatsapp"])
        c_cv = find_c(["سيرة", "cv", "resume", "link"])
        
        for _, row in df.iterrows():
            phone = format_phone_number(row[c_phone]) if c_phone else None
            if phone:
                final_targets.append({
                    'phone': phone,
                    'name': str(row[c_name]) if c_name else "",
                    'cv': str(row[c_cv]) if c_cv else ""
                })
    else:
        # Manual Mode
        for n in manual_nums:
            final_targets.append({'phone': n, 'name': 'Pasha Customer', 'cv': ''})

    if st.session_state.wa_running:
        if st.button("🛑 إيقاف البث فوراً", type="primary", use_container_width=True):
            st.session_state.wa_running = False; st.rerun()
    else:
        ready = (status == "Connected") and len(final_targets) > 0 and msg_body.strip() != ""
        if st.button(f"🚀 بدء البث لـ {len(final_targets)} مستلم بضغطة واحدة يا باشا 🔥", disabled=not ready, use_container_width=True):
            st.session_state.wa_running = True
            st.session_state.wa_idx = 0
            st.rerun()

    # 6. ENGINE EXECUTION
    if st.session_state.wa_running and final_targets:
        st.progress(st.session_state.wa_idx / len(final_targets))
        if st.session_state.wa_idx < len(final_targets):
            target = final_targets[st.session_state.wa_idx]
            curr_phone = target['phone']
            curr_name = target['name']
            curr_cv = target['cv']
            
            # Smart Replacement
            final_msg = msg_body.replace("{name}", curr_name).replace("{الاسم}", curr_name).replace("{cv}", curr_cv).replace("{السيرة}", curr_cv)
            
            st.info(f"⏳ جاري الإرسال لـ {curr_name} ({curr_phone})...")
            ok, info = st.session_state.wa_service.send_message(curr_phone, final_msg)
            
            # Logs
            log_icon = "✅" if ok else "❌"
            st.session_state.wa_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_icon} {curr_name}: {info}")
            st.session_state.wa_idx += 1
            
            if st.session_state.wa_idx == len(final_targets):
                st.session_state.wa_running = False; st.balloons()
            
            time.sleep(delay)
            st.rerun()

    # 7. LOGS
    if st.session_state.wa_logs:
        with st.expander("📄 سجل الإرسال التفصيلي لـ معاليك", expanded=True):
            st.markdown('<div style="background:rgba(0,0,0,0.8); padding:10px; border-radius:10px; color:#00FF41; max-height:300px; overflow-y:auto; font-family:monospace;">', unsafe_allow_html=True)
            for log in reversed(st.session_state.wa_logs):
                st.text(log)
            st.markdown('</div>', unsafe_allow_html=True)
