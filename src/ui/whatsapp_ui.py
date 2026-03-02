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

    # Title removed for Pasha

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

    # 2. QR Code (Ultra-High Contrast for Pasha)
    if status == "Awaiting Login":
        st.markdown("""
            <style>
                .pasha-qr-container {
                    background: #FFFFFF !important;
                    padding: 30px !important;
                    border-radius: 20px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    border: 8px solid #D4AF37;
                    margin: 20px auto;
                    width: fit-content;
                }
            </style>
        """, unsafe_allow_html=True)
        
        qr = st.session_state.wa_service.get_qr_hd()
        if qr:
            st.markdown('<div class="pasha-qr-container">', unsafe_allow_html=True)
            st.image(qr, width=350)
            st.markdown('<div style="color:#000; font-weight:bold; margin-top:10px;">باشا! يرجى المسح الآن 🤳</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Progress bar for refresh
            count = st.empty()
            for i in range(15, 0, -1):
                count.caption(f"سيتم تحديث الرمز خلال {i} ثانية...")
                time.sleep(1)
            st.rerun()
        else:
            st.info("⏳ جاري توليد رمز الدخول... برجاء الانتظار ثواني")
            time.sleep(5); st.rerun()

    # 3. Input Management
    st.markdown("---")
    tab_bulk, tab_excel = st.tabs(["🔢 إدخال يدوي", "📊 رفع ملف Excel (Pasha Mode)"])
    
    manual_nums = []
    with tab_bulk:
        txt_in = st.text_area("ألصق الأرقام هنا", height=120, placeholder="054...")
        manual_nums, _, _ = validate_numbers(txt_in)
        if manual_nums: st.caption(f"جاهز للإرسال لـ {len(manual_nums)} رقم")

    uploaded_df = None
    with tab_excel:
        uploaded_file = st.file_uploader("ارفع ملف الإكسل المصدر من البرنامج يا باشا", type=["xlsx"])
        if uploaded_file:
            try:
                uploaded_df = pd.read_excel(uploaded_file)
                st.session_state.wa_data = uploaded_df
                st.success(f"تم تحميل {len(uploaded_df)} عامل من الملف يا باشا ✅")
            except Exception as e:
                st.error(f"خطأ في قراءة الملف: {e}")

    # 4. Identification of Targets
    final_targets = []
    
    if uploaded_file and st.session_state.wa_data is not None:
        df = st.session_state.wa_data
        # Ultra-Robust Column Mapping for Pasha
        def find_pasha_col(keys):
            for c in df.columns:
                c_str = str(c).lower()
                if any(k in c_str for k in keys): return c
            return None
        
        c_name = find_pasha_col(["اسم", "name", "полное"])
        c_phone = find_pasha_col(["هاتف", "phone", "جوال", "whatsapp", "واتساب", "رقم"])
        c_cv = find_pasha_col(["سيرة", "cv", "resume", "link", "سيره"])
        
        for _, row in df.iterrows():
            if c_phone:
                raw_p = str(row[c_phone]).strip()
                phone = format_phone_number(raw_p)
                if not phone: # Attempt second cleanup
                    phone = format_phone_number("".join(raw_p.split()))
                    
                if phone:
                    final_targets.append({
                        'phone': phone,
                        'name': str(row[c_name]) if c_name else "Client",
                        'cv': str(row[c_cv]) if c_cv else ""
                    })
    elif manual_nums:
        for n in manual_nums:
            final_targets.append({'phone': n, 'name': 'Pasha Customer', 'cv': ''})

    # 5. Message Design
    st.markdown("---")
    st.markdown("### ✉️ تصميم الرسالة الذكية")
    msg_help_ar = "يا باشا! سيتم تبديل {الاسم} باسم العامل، و {السيرة} برابط ملفه تلقائياً."
    st.info(msg_help_ar)
    
    msg_body = st.text_area("نص الرسالة (يدعم التاغات الذكية)", height=150, 
                           value="Hello {الاسم},\n\nGreetings.\nYou previously contacted us regarding employment opportunities. Are you still actively looking for work at this time?\n\nBest regards,\nAbu Fahd")
    
    # NEW: File Attachment Support for Pasha
    st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
    attached_file = st.file_uploader("📎 إضافة مرفق (صور، PDF، مستندات، أو إكسل)", type=["pdf", "jpg", "png", "docx", "jpeg", "xlsx", "xls"])
    
    delay = st.slider("التأخير بين الرسائل (ثواني)", 5, 120, 15)

    # 6. ACTION
    st.markdown("---")
    if st.session_state.wa_running:
        if st.button("🛑 إيقاف البث فوراً يا باشا", type="primary", use_container_width=True):
            st.session_state.wa_running = False; st.rerun()
    else:
        btn_label = f"🚀 بدء البث لـ {len(final_targets)} مستلم بضغطة واحدة يا باشا 🔥"
        is_ready = (status == "Connected") and len(final_targets) > 0 and msg_body.strip() != ""
        if st.button(btn_label, disabled=not is_ready, use_container_width=True):
            st.session_state.wa_running = True
            st.session_state.wa_idx = 0
            st.rerun()

    # 7. ENGINE
    if st.session_state.wa_running and final_targets:
        st.progress(st.session_state.wa_idx / len(final_targets))
        if st.session_state.wa_idx < len(final_targets):
            target = final_targets[st.session_state.wa_idx]
            curr_phone = target['phone']
            curr_name = target['name']
            curr_cv = target['cv']
            
            final_msg = msg_body.replace("{name}", curr_name).replace("{الاسم}", curr_name).replace("{cv}", curr_cv).replace("{السيرة}", curr_cv)
            
            # Temporary file handling for Pasha's attachment
            tmp_path = None
            if attached_file:
                import tempfile
                import os
                suffix = os.path.splitext(attached_file.name)[1]
                t_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                t_file.write(attached_file.getvalue())
                t_file.close()
                tmp_path = t_file.name

            st.info(f"⏳ جاري الإرسال لـ معاليك (الرقم الحالي: {curr_phone})...")
            ok, info = st.session_state.wa_service.send_message(curr_phone, final_msg, file_path=tmp_path)
            
            # Cleanup temp file
            if tmp_path and os.path.exists(tmp_path):
                try: os.unlink(tmp_path)
                except: pass
            
            log_icon = "✅" if ok else "❌"
            st.session_state.wa_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_icon} {curr_name}: {info}")
            st.session_state.wa_idx += 1
            
            if st.session_state.wa_idx == len(final_targets):
                st.session_state.wa_running = False; st.balloons()
            
            time.sleep(delay)
            st.rerun()

    # 8. LOGS
    if st.session_state.wa_logs:
        with st.expander("📄 سجل الإرسال التفصيلي لـ معاليك", expanded=True):
            lc1, lc2 = st.columns([3, 1])
            with lc2:
                if st.button("🗑️ مسح السجل", use_container_width=True):
                    st.session_state.wa_logs = []
                    st.rerun()
            
            st.markdown('<div style="background:rgba(0,0,0,0.8); padding:10px; border-radius:10px; color:#00FF41; max-height:300px; overflow-y:auto; font-family:monospace;">', unsafe_allow_html=True)
            for log in reversed(st.session_state.wa_logs):
                st.text(log)
            st.markdown('</div>', unsafe_allow_html=True)
