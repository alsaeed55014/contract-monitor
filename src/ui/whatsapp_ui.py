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
    
    if 'wa_service' not in st.session_state:
        st.session_state.wa_service = WhatsAppService()
    if 'wa_logs' not in st.session_state: st.session_state.wa_logs = []
    if 'wa_running' not in st.session_state: st.session_state.wa_running = False
    if 'wa_idx' not in st.session_state: st.session_state.wa_idx = 0
    if 'wa_data' not in st.session_state: st.session_state.wa_data = None

    st.markdown('<div class="programmer-signature-neon">By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#D4AF37; text-align:center; font-family:Cairo;">🚀 جناح واتساب لـ معاليك 2026</h1>', unsafe_allow_html=True)

    # 1. Connection
    status = st.session_state.wa_service.get_status()
    c1, c2 = st.columns([2, 1])
    with c1:
        if status == "Connected": st.success("✅ متصل يا باشا! جاهز للإرسال")
        elif status == "Awaiting Login": st.warning("⚠️ الباركود جاهز، امسح من واتساب الموبيل يا باشا")
        elif status == "Loading...": st.info("⏳ جاري التحميل...")
        else: st.error("❌ المحرك متوقف - اضغط إعادة تشغيل")
    with c2:
        if st.button("🔄 إعادة تشغيل المحرك", type="primary", use_container_width=True):
            with st.spinner("جاري إعادة التشغيل..."):
                st.session_state.wa_service.close()
                ok, msg = st.session_state.wa_service.start_driver(headless=is_cloud)
                if ok: st.toast("✅ جاهز!")
                else: st.error(msg)
                st.rerun()

    # 2. QR CODE SECTION
    if status == "Awaiting Login":
        # Instructions for Pasha
        st.markdown("""
        <div style="background:rgba(212,175,55,0.1); padding:15px; border-radius:15px; border:1px solid rgba(212,175,55,0.3); margin:10px 0;">
            <h4 style="color:#D4AF37; margin:0 0 10px 0; font-family:Cairo;">📱 طريقة المسح الصحيحة يا باشا:</h4>
            <ol style="color:#EEE; font-family:Cairo; margin:0; padding-right:20px;">
                <li>افتح تطبيق <b>واتساب</b> على الموبيل</li>
                <li>اذهب إلى <b>الإعدادات</b> ← <b>الأجهزة المرتبطة</b></li>
                <li>اضغط <b>"ربط جهاز"</b></li>
                <li>وجّه الكاميرا على الباركود أدناه</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        # Display QR
        qr_b64 = st.session_state.wa_service.get_qr_hd()
        if qr_b64:
            if qr_b64.startswith("data:"):
                src = qr_b64
            else:
                src = f"data:image/png;base64,{qr_b64}"
            
            st.markdown(f"""
            <div style="
                background: #FFFFFF;
                padding: 25px;
                border-radius: 20px;
                max-width: 420px;
                margin: 15px auto;
                text-align: center;
                box-shadow: 0 0 40px rgba(255,255,255,0.4);
            ">
                <img src="{src}" 
                     style="
                        width: 350px; 
                        height: 350px; 
                        image-rendering: pixelated;
                        image-rendering: crisp-edges;
                     " />
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("⏳ جاري توليد الباركود...")
        
        # TWO BUTTONS - No auto refresh!
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔄 تحديث الباركود", use_container_width=True):
                st.rerun()
        with b2:
            if st.button("✅ تم المسح - تحقق من الاتصال", use_container_width=True, type="primary"):
                # Wait a moment for WhatsApp to process the connection
                time.sleep(3)
                new_status = st.session_state.wa_service.get_status()
                if new_status == "Connected":
                    st.toast("🎉 تم الاتصال بنجاح يا باشا!")
                else:
                    st.warning(f"الحالة الحالية: {new_status}. جاري المحاولة مرة أخرى...")
                    time.sleep(5)
                st.rerun()

    # 3. INPUT + BROADCAST (Only when Connected)
    if status == "Connected":
        st.markdown("---")
        t_manual, t_xl = st.tabs(["🔢 أرقام يدوية", "📊 ملف إكسل"])
        
        manual_list = []
        with t_manual:
            txt = st.text_area("ألصق الأرقام هنا", height=100)
            manual_list, _, _ = validate_numbers(txt)
            if manual_list: st.success(f"جاهز لـ {len(manual_list)} رقم")

        with t_xl:
            uploaded = st.file_uploader("ارفع ملف الإكسل", type=["xlsx"])
            if uploaded:
                df = pd.read_excel(uploaded)
                st.session_state.wa_data = df
                st.success(f"تم تحميل {len(df)} عامل ✅")
        
        final_targets = []
        if uploaded and st.session_state.wa_data is not None:
            df = st.session_state.wa_data
            def find_c(keys):
                for c in df.columns:
                    if any(k in str(c).lower() for k in keys): return c
                return None
            c_name = find_c(["اسم", "name"])
            c_phone = find_c(["واتساب", "رقم", "هاتف", "phone", "جوال"])
            c_cv = find_c(["سيرة", "cv", "resume", "link"])
            for _, row in df.iterrows():
                if c_phone:
                    raw_p = str(row[c_phone]).strip()
                    phone = format_phone_number(raw_p)
                    if not phone: phone = format_phone_number("".join(raw_p.split()))
                    if phone:
                        final_targets.append({
                            'phone': phone,
                            'name': str(row[c_name]) if c_name else "Client",
                            'cv': str(row[c_cv]) if c_cv else ""
                        })
        elif manual_list:
            for n in manual_list:
                final_targets.append({'phone': n, 'name': 'Customer', 'cv': ''})

        st.markdown("### ✍️ نص الرسالة")
        st.info("💡 {الاسم} = اسم العامل، {السيرة} = رابط ملفه")
        msg_body = st.text_area("اكتب رسالتك", height=150,
                               value="مرحبا {الاسم},\nهذه رسالة من مجموعة السعيد الوزان.\nرابط ملفك: {السيرة}")
        delay = st.slider("مهلة الإرسال (ثانية)", 5, 120, 15)

        st.markdown("---")
        if st.session_state.wa_running:
            if st.button("🛑 إيقاف", type="primary", use_container_width=True):
                st.session_state.wa_running = False; st.rerun()
        else:
            ready = len(final_targets) > 0 and msg_body.strip() != ""
            if st.button(f"🚀 بدء البث لـ {len(final_targets)} مستلم 🔥", disabled=not ready, use_container_width=True):
                st.session_state.wa_running = True
                st.session_state.wa_idx = 0
                st.rerun()

        if st.session_state.wa_running and final_targets:
            st.progress(st.session_state.wa_idx / len(final_targets))
            if st.session_state.wa_idx < len(final_targets):
                trg = final_targets[st.session_state.wa_idx]
                p, n, v = trg['phone'], trg['name'], trg['cv']
                final_msg = msg_body.replace("{الاسم}", n).replace("{name}", n).replace("{السيرة}", v).replace("{cv}", v)
                st.info(f"⏳ إرسال إلى: {n} ({p})...")
                ok, log = st.session_state.wa_service.send_message(p, final_msg)
                icon = "✅" if ok else "❌"
                st.session_state.wa_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {icon} {n}: {log}")
                st.session_state.wa_idx += 1
                if st.session_state.wa_idx == len(final_targets):
                    st.session_state.wa_running = False; st.balloons()
                time.sleep(delay); st.rerun()

        if st.session_state.wa_logs:
            with st.expander("📄 سجل الإرسال", expanded=True):
                for l in reversed(st.session_state.wa_logs): st.text(l)

    if status not in ["Connected", "Awaiting Login"]:
        with st.expander("🛠️ أدوات التشخيص"):
            if st.button("📸 لقطة شاشة"):
                img = st.session_state.wa_service.get_diagnostic_screenshot()
                if img: st.image(f"data:image/png;base64,{img}")
