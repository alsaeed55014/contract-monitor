import streamlit as st
import pandas as pd
import time
from datetime import datetime
from src.services.whatsapp_service import WhatsAppService
from src.utils.phone_utils import validate_numbers, format_phone_number
from src.core.i18n import t

def render_whatsapp_page():
    lang = st.session_state.get('lang', 'ar')
    is_ar = lang == 'ar'
    is_cloud = "/mount/" in __file__
    
    if 'wa_service' not in st.session_state:
        st.session_state.wa_service = WhatsAppService()
    else:
        # Check if the existing service object is outdated (missing attachment_path in send_message)
        import inspect
        sig = inspect.signature(st.session_state.wa_service.send_message)
        if 'attachment_path' not in sig.parameters:
            st.session_state.wa_service = WhatsAppService()
    if 'wa_logs' not in st.session_state: st.session_state.wa_logs = []
    if 'wa_running' not in st.session_state: st.session_state.wa_running = False
    if 'wa_idx' not in st.session_state: st.session_state.wa_idx = 0
    if 'wa_data' not in st.session_state: st.session_state.wa_data = None

    st.markdown('<div class="programmer-signature-neon">By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)

    # === Bilingual Labels ===
    lbl = {
        'connected': "✅ متصل! جاهز للإرسال" if is_ar else "✅ Connected! Ready to send",
        'awaiting': "⚠️ الباركود جاهز، امسح من واتساب" if is_ar else "⚠️ QR Ready, scan from WhatsApp",
        'loading': "⏳ جاري التحميل..." if is_ar else "⏳ Loading...",
        'stopped': "❌ المحرك متوقف" if is_ar else "❌ Engine Stopped",
        'start_engine': "🔄 تشغيل المحرك" if is_ar else "🔄 Start Engine",
        'full_reset': "🗑️ إعادة تعيين" if is_ar else "🗑️ Full Reset",
        'starting': "جاري التشغيل... (30 ثانية)" if is_ar else "Starting... (30 sec)",
        'resetting': "جاري المسح والإعادة..." if is_ar else "Resetting...",
        'refresh_qr': "🔄 تحديث الباركود" if is_ar else "🔄 Refresh QR",
        'verify': "✅ تم المسح - تحقق" if is_ar else "✅ Scanned - Verify",
        'verifying': "جاري التحقق... (30 ثانية)" if is_ar else "Verifying... (30 sec)",
        'connected_ok': "🎉 تم الاتصال بنجاح!" if is_ar else "🎉 Connected successfully!",
        'not_connected': "❌ لم يتم الاتصال. جرب إعادة التعيين" if is_ar else "❌ Not connected. Try Full Reset",
        'qr_loading': "⏳ جاري توليد الباركود..." if is_ar else "⏳ Generating QR...",
        'tab_manual': "🔢 أرقام يدوية" if is_ar else "🔢 Manual Numbers",
        'tab_excel': "📊 ملف إكسل" if is_ar else "📊 Excel File",
        'paste_numbers': "ألصق الأرقام هنا" if is_ar else "Paste numbers here",
        'ready_count': "جاهز لـ {} رقم" if is_ar else "Ready for {} numbers",
        'upload_excel': "ارفع ملف الإكسل" if is_ar else "Upload Excel file",
        'loaded_count': "تم تحميل {} عامل ✅" if is_ar else "Loaded {} workers ✅",
        'delete_file': "🗑️ حذف الملف" if is_ar else "🗑️ Delete File",
        'msg_title': "### ✍️ نص الرسالة" if is_ar else "### ✍️ Message Text",
        'msg_label': "اكتب رسالتك" if is_ar else "Write your message",
        'attach': "📎 إرفاق ملف (اختياري)" if is_ar else "📎 Attach file (optional)",
        'attached': "📎 مرفق: {} ({} KB)" if is_ar else "📎 Attached: {} ({} KB)",
        'delay': "مهلة الإرسال (ثانية)" if is_ar else "Send delay (seconds)",
        'stop': "🛑 إيقاف" if is_ar else "🛑 Stop",
        'sent_done': "تم الارسال ✅" if is_ar else "Sent ✅",
        'send': "📨 ارسال ({})" if is_ar else "📨 Send ({})",
        'sending': "⏳ إرسال إلى: {} ({})..." if is_ar else "⏳ Sending to: {} ({})...",
        'log_title': "#### 📄 سجل الإرسال" if is_ar else "#### 📄 Send Log",
        'delete_log': "🗑️ مسح السجل" if is_ar else "🗑️ Clear Log",
        'diag': "🛠️ أدوات التشخيص" if is_ar else "🛠️ Diagnostics",
        'screenshot': "📸 لقطة شاشة" if is_ar else "📸 Screenshot",
        'batch_size': "استراحة بعد (عدد الرسائل)" if is_ar else "Pause after (messages)",
        'batch_delay': "مدة الاستراحة (دقائق)" if is_ar else "Pause duration (minutes)",
        'pausing': "⏳ استراحة مؤقتة... متبقي: {}" if is_ar else "⏳ Pausing... remaining: {}",
        'next_msg_in': "⏳ الرسالة القادمة خلال: {}" if is_ar else "⏳ Next message in: {}",
        'settings_title': "#### ⚙️ إعدادات الإرسال" if is_ar else "#### ⚙️ Sending Settings",
        'batch_help': "0 = بدون استراحة" if is_ar else "0 = No pause",
        'download_template': "📥 تحميل نموذج إكسل" if is_ar else "📥 Download Excel Template",
    }

    # 1. Connection Status
    status = st.session_state.wa_service.get_status()
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        if status == "Connected": st.success(lbl['connected'])
        elif status == "Awaiting Login": st.warning(lbl['awaiting'])
        elif status == "Loading...": st.info(lbl['loading'])
        else:
            st.error(lbl['stopped'])
            if getattr(st.session_state.wa_service, 'last_error', ''):
                st.code(st.session_state.wa_service.last_error, language=None)
    with c2:
        if st.button(lbl['start_engine'], type="primary", use_container_width=True):
            with st.spinner(lbl['starting']):
                st.session_state.wa_service.close()
                ok, msg = st.session_state.wa_service.start_driver(headless=is_cloud, force_clean=False)
                if ok: st.toast(f"✅ {msg}")
                else: st.error(f"❌ {msg}")
                st.rerun()
    with c3:
        if st.button(lbl['full_reset'], use_container_width=True):
            with st.spinner(lbl['resetting']):
                st.session_state.wa_service.close()
                ok, msg = st.session_state.wa_service.start_driver(headless=is_cloud, force_clean=True)
                if ok: st.toast(f"✅ {msg}")
                else: st.error(f"❌ {msg}")
                st.rerun()

    # 2. QR CODE SECTION (DO NOT MODIFY)
    if status == "Awaiting Login":
        qr_b64 = st.session_state.wa_service.get_qr_hd()
        if qr_b64:
            src = qr_b64 if qr_b64.startswith("data:") else f"data:image/png;base64,{qr_b64}"
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
            st.info(lbl['qr_loading'])
        
        b1, b2 = st.columns(2)
        with b1:
            if st.button(lbl['refresh_qr'], use_container_width=True):
                st.rerun()
        with b2:
            if st.button(lbl['verify'], use_container_width=True, type="primary"):
                with st.spinner(lbl['verifying']):
                    connected = st.session_state.wa_service.wait_for_connection(timeout=30)
                if connected:
                    st.toast(lbl['connected_ok'])
                    st.balloons()
                else:
                    st.error(lbl['not_connected'])
                st.rerun()

    # 3. INPUT + BROADCAST (Only when Connected)
    if status == "Connected":
        st.markdown("---")
        t_manual, t_xl = st.tabs([lbl['tab_manual'], lbl['tab_excel']])
        
        manual_list = []
        with t_manual:
            txt = st.text_area(lbl['paste_numbers'], height=100)
            manual_list, _, _ = validate_numbers(txt)
            if manual_list:
                st.success(lbl['ready_count'].format(len(manual_list)))
                if st.session_state.get('wa_last_manual_count', 0) != len(manual_list) or txt != st.session_state.get('wa_last_txt', ''):
                    st.session_state.wa_done = False
                    st.session_state.wa_last_manual_count = len(manual_list)
                    st.session_state.wa_last_txt = txt

        with t_xl:
            uploaded = st.file_uploader(lbl['upload_excel'], type=["xlsx"], key=st.session_state.get('wa_upload_key', 'xl_0'))
            if uploaded:
                df = pd.read_excel(uploaded)
                # Reset if it's a new upload (even if count is the same)
                if st.session_state.get('wa_last_uploaded_name') != uploaded.name:
                    st.session_state.wa_done = False
                    st.session_state.wa_last_uploaded_name = uploaded.name
                st.session_state.wa_data = df
                xl_col1, xl_col2 = st.columns([3, 1])
                with xl_col1:
                    st.success(lbl['loaded_count'].format(len(df)))
                with xl_col2:
                    if st.button(lbl['delete_file'], use_container_width=True, key="del_xl"):
                        st.session_state.wa_data = None
                        st.session_state.wa_done = False
                        old_key = st.session_state.get('wa_upload_key', 'xl_0')
                        st.session_state.wa_upload_key = 'xl_1' if old_key == 'xl_0' else 'xl_0'
                        st.rerun()
            elif st.session_state.wa_data is not None:
                # Show delete button even if uploader is empty but data exists
                xl_col1, xl_col2 = st.columns([3, 1])
                with xl_col1:
                    st.info(lbl['loaded_count'].format(len(st.session_state.wa_data)))
                with xl_col2:
                    if st.button(lbl['delete_file'], use_container_width=True, key="del_xl2"):
                        st.session_state.wa_data = None
                        st.session_state.wa_done = False
                        old_key = st.session_state.get('wa_upload_key', 'xl_0')
                        st.session_state.wa_upload_key = 'xl_1' if old_key == 'xl_0' else 'xl_0'
                        st.rerun()
            
            # --- Download Template Section ---
            cols = ["الاسم", "رقم الجوال", "السيرة الذاتية", "الجنسيه", "الجنس", "العمر", "المدينة", 
                    "الوظيفه المطلوبه", "الخبرة في هذا المجال", "مهارات اخرى", "الخبرة", 
                    "هل يمكنك العمل خارج المدينة", "هل انت جاهز للعمل فورا", "هل معك عائلته", 
                    "رقم الاقامة", "عدد مرات نقل الكفالة"]
            template_df = pd.DataFrame(columns=cols)
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                template_df.to_excel(writer, index=False)
            
            st.download_button(
                label=lbl['download_template'],
                data=output.getvalue(),
                file_name="whatsapp_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        final_targets = []
        if manual_list:
            for n in manual_list:
                final_targets.append({'phone': n, 'name': 'Customer', 'cv': ''})
        elif st.session_state.wa_data is not None:
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
                        # Capture ALL columns dynamically
                        target_data = {str(col): str(row[col]) for col in df.columns}
                        target_data.update({
                            'phone': phone,
                            'name': str(row[c_name]) if c_name else "Client",
                            'cv': str(row[c_cv]) if c_cv else ""
                        })
                        final_targets.append(target_data)

        st.markdown(lbl['msg_title'])
        
        # LTR for English messages
        st.markdown("""
        <style>
        div[data-testid="stTextArea"] textarea {
            direction: ltr !important;
            text-align: left !important;
            font-family: 'Inter', sans-serif !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        default_msg = """Hello {Name},

We hope you are well.

You previously contacted us regarding job opportunities, and we would appreciate it if you are still interested and available for work.

Please let us know if you are still interested in working.

Link to your profile: {CV}

Sincerely,
Abu Fahd"""
        msg_body = st.text_area(lbl['msg_label'], height=250, value=default_msg)
        
        # Attachment
        attachment = st.file_uploader(lbl['attach'], 
                                      type=["png","jpg","jpeg","gif","bmp","webp",
                                            "pdf","doc","docx","xls","xlsx","ppt","pptx",
                                            "mp4","avi","mov","mkv","mp3","wav","ogg",
                                            "zip","rar","7z","txt","csv"],
                                      key="wa_attachment")
        if attachment:
            st.success(lbl['attached'].format(attachment.name, round(attachment.size/1024, 1)))
        
        st.markdown(lbl['settings_title'])
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            delay = st.number_input(lbl['delay'], min_value=5, max_value=600, value=15, disabled=st.session_state.wa_running)
        with col_s2:
            batch_size = st.number_input(lbl['batch_size'], min_value=0, max_value=1000, value=0, help=lbl['batch_help'], disabled=st.session_state.wa_running)
        with col_s3:
            batch_delay_mins = st.number_input(lbl['batch_delay'], min_value=1, max_value=60, value=1, disabled=st.session_state.wa_running)
            batch_delay = int(batch_delay_mins * 60)

        # Smart detect target changes
        current_fp = ",".join([t['phone'] for t in final_targets]) if final_targets else ""
        if current_fp != st.session_state.get('wa_sent_fingerprint', ''):
            st.session_state.wa_done = False

        # Send / Stop
        btn1, btn2, btn3 = st.columns([1, 1, 2])
        with btn1:
            if st.session_state.wa_running:
                if st.button(lbl['stop'], type="primary", use_container_width=True):
                    st.session_state.wa_running = False; st.rerun()
            else:
                ready = len(final_targets) > 0 and msg_body.strip() != ""
                if st.session_state.get('wa_done', False) and current_fp == st.session_state.get('wa_sent_fingerprint', ''):
                    st.button(lbl['sent_done'], disabled=True, use_container_width=True)
                else:
                    if st.button(lbl['send'].format(len(final_targets)), disabled=not ready, use_container_width=True, type="primary"):
                        st.session_state.wa_running = True
                        st.session_state.wa_idx = 0
                        st.session_state.wa_done = False
                        st.session_state.wa_sent_fingerprint = current_fp
                        st.rerun()

        if st.session_state.wa_running and final_targets:
            # Save attachment to temp file if exists
            temp_path = None
            if attachment:
                import tempfile
                suffix = os.path.splitext(attachment.name)[1]
                t_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                t_file.write(attachment.getvalue())
                t_file.close()
                temp_path = t_file.name

            st.progress(st.session_state.wa_idx / len(final_targets))
            if st.session_state.wa_idx < len(final_targets):
                trg = final_targets[st.session_state.wa_idx]
                p, n, v = trg['phone'], trg['name'], trg['cv']
                
                # Intelligent dynamic replacement for ALL columns
                final_msg = msg_body
                for key, val in trg.items():
                    # Support both {Key} and {key} and various Arabic variations
                    final_msg = final_msg.replace("{" + key + "}", val)
                    final_msg = final_msg.replace("{" + key.lower() + "}", val)
                
                # Traditional fallbacks for Name and CV (if placeholders weren't exact match)
                final_msg = final_msg.replace("{Name}", n).replace("{name}", n).replace("{الاسم}", n).replace("{CV}", v).replace("{cv}", v).replace("{السيرة}", v)
                
                st.info(lbl['sending'].format(n, p))
                
                # Call send_message with temp_path
                ok, log = st.session_state.wa_service.send_message(p, final_msg, attachment_path=temp_path)
                
                icon = "✅" if ok else "❌"
                st.session_state.wa_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {icon} {n}: {log}")
                st.session_state.wa_idx += 1
                
                if st.session_state.wa_idx == len(final_targets):
                    st.session_state.wa_running = False
                    st.session_state.wa_done = True
                    # Clean up temp file
                    if temp_path and os.path.exists(temp_path):
                        try: os.remove(temp_path)
                        except: pass
                    st.balloons()
                    st.rerun()
                else:
                    def format_time(seconds):
                        m, s = divmod(seconds, 60)
                        if m > 0:
                            return f"{m} دقيقة و {s} ثانية" if is_ar else f"{m}m {s}s"
                        return f"{s} ثانية" if is_ar else f"{s}s"

                    if batch_size > 0 and st.session_state.wa_idx % batch_size == 0:
                        wait_ph = st.empty()
                        for i in range(batch_delay, 0, -1):
                            if not st.session_state.wa_running: break
                            wait_ph.warning(lbl['pausing'].format(format_time(i)))
                            time.sleep(1)
                        wait_ph.empty()
                    else:
                        wait_ph = st.empty()
                        for i in range(delay, 0, -1):
                            if not st.session_state.wa_running: break
                            wait_ph.info(lbl['next_msg_in'].format(format_time(i)))
                            time.sleep(1)
                        wait_ph.empty()
                    
                    if st.session_state.wa_running:
                        st.rerun()
            
            # Clean up temp file if stopped or finished early
            if not st.session_state.wa_running and temp_path and os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass

        # Logs
        if st.session_state.wa_logs:
            log_h, log_del = st.columns([3, 1])
            with log_h:
                st.markdown(lbl['log_title'])
            with log_del:
                if st.button(lbl['delete_log'], use_container_width=True):
                    st.session_state.wa_logs = []
                    st.session_state.wa_done = False
                    st.rerun()
            for l in reversed(st.session_state.wa_logs):
                st.text(l)

    # Diagnostic
    if status not in ["Connected", "Awaiting Login"]:
        with st.expander(lbl['diag']):
            if st.button(lbl['screenshot']):
                img = st.session_state.wa_service.get_diagnostic_screenshot()
                if img: st.image(f"data:image/png;base64,{img}")
