import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime
# WhatsAppService is imported lazily inside render_whatsapp_page() to avoid blocking app startup with selenium
from src.utils.phone_utils import validate_numbers, format_phone_number, save_to_local_desktop, render_pasha_export_button
from src.core.i18n import t
from src.config import WA_HISTORY_FILE, WA_TEMPLATES_FILE
from src.ui.styles import get_base64_image
import random

# --- Smart Message Templates (Updated 2026-03-20) ---
SMART_TEMPLATES = {
    "intro": [
        "I hope you are doing well.",
        "I hope this message finds you in good health.",
        "Wishing you a productive day ahead.",
        "Hope you're having a great start to your day.",
        "Trust you are doing well today."
    ],
    "body_start": [
        "We are actively matching candidates with the latest job opportunities with us",
        "Our HR team is currently evaluating candidates for various job opportunities with us",
        "We are in the process of reviewing profiles for several job opportunities with us",
        "We are currently evaluating candidates for various job opportunities with us",
        "Our team is actively scouting for talent for new job opportunities with us"
    ],
    "body_end": [
        ", and we'd love to know if you are still looking for a position.",
        ". Based on your background, we would like to confirm your current availability.",
        ", and we are interested in checking if you are still seeking a new role.",
        ". Since you expressed interest before, we wanted to touch base regarding your status.",
        ", and we'd appreciate an update on whether you are still open to new opportunities."
    ],
    "closing": [
        "YES – Proceed with me\nNO – I am not available at the moment\n\nIf you are not currently seeking opportunities, we would highly appreciate it if you could share this message with a friend or colleague who may be looking for employment.\nPlease confirm by replying:",
        "YES – Proceed with me\nNO – Not available right now\n\nIf you are not currently seeking opportunities, we would highly appreciate it if you could share this message with a friend or colleague who may be looking for employment\nPlease confirm by replying:",
        "YES – Proceed with me\nNO – Not interested at this time\n\nIf you are not currently seeking opportunities, we would highly appreciate it if you could share this message with a friend or colleague who may be looking for employment.\nPlease confirm by replying:",
        "YES – Proceed with me\nNO – I have another job\n\nIf you are not currently seeking opportunities, we would highly appreciate it if you could share this message with a friend or colleague who may be looking for employment\nPlease confirm by replying:",
        "YES – Proceed with me\nNO – Don't proceed\n\nIf you are not currently seeking opportunities, we would highly appreciate it if you could share this message with a friend or colleague who may be looking for employment.\nPlease confirm by replying:"
    ],
    "final_call": [
        "We will be moving forward shortly, so your quick response is highly appreciated.",
        "We look forward to hearing from you at your earliest convenience.",
        "The selection process is moving fast, so please get back to us as soon as possible.",
        "To ensure you don't miss out, please let us know your status shortly.",
        "We look forward to your prompt response."
    ]
}

def load_templates():
    default_templates = {
        "smart": SMART_TEMPLATES,
        "custom": {
            "Default Template": {
                "body": "Hello {Name},\n\nI hope you are doing well.\n\nWe are currently evaluating candidates for various job opportunities with us, and we'd love to know if you are still looking for a position.\n\nKindly respond with:\nYES – I am interested and available\nNO – I am not available right now\n\nIf you are not currently seeking opportunities, we would highly appreciate it if you could share this message with a friend or colleague who may be looking for employment.\n\nBest regards,\nAbu Fahd\nHR Manager",
                "is_smart": True,
                "job_title": ""
            }
        }
    }
    if os.path.exists(WA_TEMPLATES_FILE):
        try:
            with open(WA_TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Migration: Convert old string templates to dicts if necessary
                if "custom" in data:
                    for k, v in data["custom"].items():
                        if isinstance(v, str):
                            data["custom"][k] = {"body": v, "is_smart": False, "job_title": ""}
                return data
        except:
            return default_templates
    return default_templates

def save_templates(templates):
    try:
        with open(WA_TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False, indent=4)
    except:
        pass

def generate_smart_message(name, cv_link, custom_job=""):
    templates = load_templates().get("smart", SMART_TEMPLATES)
    
    # 🛡️ تنويع التحية
    greetings = ["Hello", "Hi", "Greetings", "Dear"]
    greet = random.choice(greetings)
    
    intro = random.choice(templates.get("intro", [""]))
    b_start = random.choice(templates.get("body_start", [""]))
    b_end = random.choice(templates.get("body_end", [""]))
    closing = random.choice(templates.get("closing", [""]))
    final_call = random.choice(templates.get("final_call", [""]))
    
    # Handle custom job title injection beautifully
    job_part = f" - {custom_job}" if custom_job.strip() else ""
    full_body = f"{b_start}{job_part}{b_end}"
    
    # 🛡️ تبديل هيكلية الرسالة بشكل عشوائي (Shuffling sections)
    sections = [intro, full_body, closing, final_call]
    # random.shuffle(sections) # Not always good as it might break logical flow
    
    # Randomize line breaks (one or two)
    lb = "\n" if random.random() > 0.5 else "\n\n"
    
    msg = f"{greet} {name},{lb}{intro}{lb}{full_body}{lb}{closing}{lb}{final_call}{lb}"
    
    # Logic: If CV exists, add CV link. If not, omit it.
    if cv_link and str(cv_link).lower() != 'nan' and str(cv_link).strip() != '':
        msg += f"Link to your profile: {cv_link}\n\n"
    
    # 🛡️ تنويع التوقيع
    signatures = [
        "Best regards,\nAbu Fahd\nHR Manager",
        "Kind regards,\nAbu Fahd\nHR Manager",
        "With respect,\nAbu Fahd\nHR Manager",
        "Sincerely,\nAbu Fahd\nHR Manager"
    ]
    msg += random.choice(signatures)
    
    # 🛡️ عشوائية المسافات والرموز التعبيرية
    if random.random() > 0.7:
        msg = msg.replace(".", " .").replace("!", " ! ")
        
    return msg

def load_wa_history():
    if os.path.exists(WA_HISTORY_FILE):
        try:
            with open(WA_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_wa_history(history_set):
    try:
        with open(WA_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(history_set), f, ensure_ascii=False)
    except:
        pass

def render_whatsapp_page():
    from src.services.whatsapp_service import WhatsAppService
    from src.services.wa_worker_manager import WAWorkerManager
    lang = st.session_state.get('lang', 'ar')
    is_ar = lang == 'ar'
    is_cloud = "/mount/" in __file__

    # ── مدير العامل الخلفي ──
    if 'wa_worker_mgr' not in st.session_state:
        st.session_state.wa_worker_mgr = WAWorkerManager()
    mgr: WAWorkerManager = st.session_state.wa_worker_mgr

    # للوضع القديم (المتزامن) نبقيه للتوافق
    if 'wa_service' not in st.session_state or st.session_state.wa_service is None:
        st.session_state.wa_service = WhatsAppService()
    else:
        try:
            import inspect
            sig = inspect.signature(st.session_state.wa_service.send_message)
            if 'attachment_path' not in sig.parameters:
                st.session_state.wa_service = WhatsAppService()
        except Exception:
            st.session_state.wa_service = WhatsAppService()

    if 'wa_logs' not in st.session_state: st.session_state.wa_logs = []
    if 'wa_running' not in st.session_state: st.session_state.wa_running = False
    if 'wa_idx' not in st.session_state: st.session_state.wa_idx = 0
    if 'wa_data' not in st.session_state: st.session_state.wa_data = None
    if 'wa_history' not in st.session_state: st.session_state.wa_history = load_wa_history()
    if 'wa_review_targets' not in st.session_state: st.session_state.wa_review_targets = []
    if 'wa_messages' not in st.session_state: st.session_state.wa_messages = [""]

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
        'msg_label': "اكتب رسالتك" if is_ar else "Write your message",
        'attach': "📎 إرفاق ملف (اختياري)" if is_ar else "📎 Attach file (optional)",
        'attached': "📎 مرفق: {} ({} KB)" if is_ar else "📎 Attached: {} ({} KB)",
        'delay': "مهلة الإرسال (ثانية)" if is_ar else "Send delay (seconds)",
        'stop': "🛑 إيقاف" if is_ar else "🛑 Stop",
        'sent_done': "تم الإرسال ✅" if is_ar else "Sent ✅",
        'send': "📨 إرسال ({})" if is_ar else "📨 Send ({})",
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
        'sent_count': "تم إرسال" if is_ar else "Sent",
        'remaining_count': "متبقي" if is_ar else "Remaining",
        'review_section': "📋 مراجعة قائمة الأرقام" if is_ar else "📋 Review Numbers List",
        'col_name': "الاسم" if is_ar else "Name",
        'col_phone': "الجوال" if is_ar else "Phone",
        'col_status': "أرسل؟" if is_ar else "Sent?",
        'col_action': "حذف" if is_ar else "Delete",
        'total_pending': "بانتظار الإرسال: {}" if is_ar else "Pending: {}",
        'total_ready': "الإجمالي الجاهز: {}" if is_ar else "Total Ready: {}",
        'uncheck_all': "🔄 إرجاع الكل لقائمة الإرسال" if is_ar else "🔄 Return all to Sending List",
        'dups_removed': "⚠️ تم حذف {} رقم مكرر من القائمة" if is_ar else "⚠️ Removed {} duplicate numbers",
        'add_msg': "+ إضافة رسالة" if is_ar else "+ Add Message",
        'msg_num': "رسالة {}" if is_ar else "Message {}",
        'remove_msg': "🗑️" if is_ar else "🗑️",
        'smart_msg': "🤖 تفعيل الرسائل الذكية (AI)" if is_ar else "🤖 Enable Smart Messages (AI)",
        'smart_msg_help': "سيتم إنشاء رسائل تلقائية بأسلوب مختلف لكل عميل لتجنب الحظر." if is_ar else "Generates unique variations for each message to avoid ban.",
        'job_title_label': "اسم الوظيفة (اختياري)" if is_ar else "Job Title (Optional)",
        'job_title_placeholder': "مثال: Driver, Nurse..." if is_ar else "e.g. Driver, Nurse...",
        'wa_templates_title': t('wa_templates_title', lang),
        'wa_save_as_template': t('wa_save_as_template', lang),
        'wa_template_name': t('wa_template_name', lang),
        'wa_manage_templates': t('wa_manage_templates', lang),
        'wa_use_template': t('wa_use_template', lang),
        'wa_delete_template': t('wa_delete_template', lang),
        'wa_placeholders_guide': t('wa_placeholders_guide', lang),
    }

    # === Mode Selection ===
    wa_mode = st.radio(
        "اختر الوضع" if is_ar else "Select Mode",
        ["📱 واتساب ماركتنج (2026)" if is_ar else "📱 WhatsApp Marketing (2026)", 
         "🏢 واتساب للعملاء" if is_ar else "🏢 WhatsApp for Employers"],
        horizontal=True,
        key="wa_mode_selection"
    )

    if wa_mode == ("🏢 واتساب للعملاء" if is_ar else "🏢 WhatsApp for Employers"):
        # === WhatsApp Marketing for Employers (from Bengali Supply) ===
        st.markdown(f'### 🏢 {"واتساب ماركتنج للعملاء" if is_ar else "WhatsApp Marketing for Employers"}')

        # ──────────────────────────────────────────────────────────────
        # 🔌 قسم الاتصال والباركود (نفس واتساب ماركتنج)
        # ──────────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown(f"#### 📡 {'حالة الاتصال' if is_ar else 'Connection Status'}")

        status_emp = st.session_state.wa_service.get_status()
        ec1, ec2, ec3 = st.columns([2, 1, 1])
        with ec1:
            if   status_emp == "Connected":     st.success(lbl['connected'])
            elif status_emp == "Awaiting Login": st.warning(lbl['awaiting'])
            elif status_emp == "Loading...":     st.info(lbl['loading'])
            else:
                st.error(lbl['stopped'])
                if getattr(st.session_state.wa_service, 'last_error', ''):
                    with st.expander("🔍 " + ("تفاصيل الخطأ" if is_ar else "Error Details"), expanded=True):
                        st.code(st.session_state.wa_service.last_error, language=None)
        with ec2:
            if st.button(lbl['start_engine'], type="primary", width='stretch', key="emp_start_engine"):
                with st.spinner(lbl['starting']):
                    if st.session_state.wa_service is None:
                        st.session_state.wa_service = WhatsAppService()
                    if hasattr(st.session_state.wa_service, 'close'):
                        try: st.session_state.wa_service.close()
                        except Exception: pass
                    ok, msg = st.session_state.wa_service.start_driver(headless=is_cloud, force_clean=False)
                    if ok:
                        st.toast(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        with ec3:
            if st.button(lbl['full_reset'], width='stretch', key="emp_full_reset",
                         help="سيتم مسح بيانات تسجيل الدخول بالكامل. ستحتاج لمسح الباركود مرة أخرى." if is_ar else "This will clear all login data. You'll need to scan the QR again."):
                with st.spinner(lbl['resetting']):
                    if st.session_state.wa_service is None:
                        st.session_state.wa_service = WhatsAppService()
                    if hasattr(st.session_state.wa_service, 'close'):
                        try: st.session_state.wa_service.close()
                        except Exception: pass
                    ok, msg = st.session_state.wa_service.start_driver(headless=is_cloud, force_clean=True)
                    if ok:
                        st.toast(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

        # ── QR Code ──
        if status_emp == "Awaiting Login":
            qr_b64 = st.session_state.wa_service.get_qr_hd()
            if qr_b64:
                src = qr_b64 if qr_b64.startswith("data:") else f"data:image/png;base64,{qr_b64}"
                st.markdown(
                    f'<div style="background:#FFFFFF;padding:25px;border-radius:20px;max-width:420px;'
                    f'margin:15px auto;text-align:center;box-shadow:0 0 40px rgba(255,255,255,0.4);">'
                    f'<img src="{src}" style="width:350px;height:350px;image-rendering:pixelated;image-rendering:crisp-edges;" />'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.info(lbl['qr_loading'])

            qb1, qb2 = st.columns(2)
            with qb1:
                if st.button(lbl['refresh_qr'], width='stretch', key="emp_refresh_qr"):
                    st.rerun()
            with qb2:
                if st.button(lbl['verify'], width='stretch', type="primary", key="emp_verify"):
                    with st.spinner(lbl['verifying']):
                        connected = st.session_state.wa_service.wait_for_connection(timeout=30)
                    if connected:
                        st.toast(lbl['connected_ok'])
                        st.balloons()
                    else:
                        st.error(lbl['not_connected'])
                    st.rerun()

        # ── إذا لم يتصل، أوقف ولا تكمل (إلا إذا كان الإرسال جاري بالفعل) ──
        if status_emp != "Connected" and not st.session_state.get('wa_running', False):
            st.info("💡 " + ("قم بتشغيل المحرك ومسح الباركود أولاً للبدء بالإرسال." if is_ar else "Start the engine and scan the QR code first to begin sending."))
            st.markdown("---")
            return

        st.markdown("---")
        # ──────────────────────────────────────────────────────────────

        # Data Source Selection
        st.markdown(f"#### {'مصدر البيانات' if is_ar else 'Data Source'}")
        data_source = st.radio(
            "اختر مصدر البيانات" if is_ar else "Select Data Source",
            ["من النظام (Bengali Supply)" if is_ar else "From System (Bengali Supply)", 
             "استيراد ملف Excel" if is_ar else "Import Excel File"],
            horizontal=True,
            key="wa_bengali_data_source"
        )
        
        target_phones = []
        target_names = []
        
        if data_source == ("من النظام (Bengali Supply)" if is_ar else "From System (Bengali Supply)"):
            # Import BengaliDataManager
            from src.data.bengali_manager import BengaliDataManager
            bm = BengaliDataManager()
            
            # Get all employers
            all_employers = bm.get_employers()
            
            if not all_employers:
                st.warning("⚠️ " + ("لا يوجد عملاء في النظام" if is_ar else "No employers in the system"))
            else:
                # Select employers to send to
                st.markdown(f"#### {'اختر العملاء للإرسال' if is_ar else 'Select Employers to Send'}")
                
                # Multi-select employers
                employer_options = [f"{e['name']} - {e.get('mobile', '')}" for e in all_employers]
                selected_employers = st.multiselect(
                    "العملاء" if is_ar else "Employers",
                    employer_options,
                    key="wa_bengali_employers"
                )
                
                if selected_employers:
                    # Extract phone numbers
                    for selection in selected_employers:
                        # Extract phone from selection
                        parts = selection.split(' - ')
                        if len(parts) > 1:
                            phone = parts[-1].strip()
                            name = parts[0].strip()
                            # Clean phone number
                            clean_phone = "".join(filter(str.isdigit, phone))
                            if clean_phone:
                                target_phones.append(clean_phone)
                                target_names.append(name)
                
                st.info(f"📊 {'تم اختيار' if is_ar else 'Selected'}: {len(target_phones)} {'عميل' if is_ar else 'employers'}")
        else:
            # Excel Import
            st.markdown(f"#### {'استيراد ملف Excel' if is_ar else 'Import Excel File'}")
            uploaded_file = st.file_uploader(
                "ارفع ملف Excel" if is_ar else "Upload Excel file",
                type=['xlsx', 'xls'],
                key="wa_bengali_excel_upload"
            )
            
            if uploaded_file:
                try:
                    df = pd.read_excel(uploaded_file)
                    st.success(f"✅ {'تم تحميل الملف بنجاح' if is_ar else 'File loaded successfully'}: {len(df)} {'صف' if is_ar else 'rows'}")
                    
                    # Show columns
                    st.write(f"**{'الأعمدة المتاحة' if is_ar else 'Available columns'}:**", list(df.columns))
                    
                    # Select name and phone columns
                    col1, col2 = st.columns(2)
                    with col1:
                        name_col = st.selectbox(
                            "عمود الاسم" if is_ar else "Name column",
                            df.columns.tolist(),
                            key="wa_bengali_name_col"
                        )
                    with col2:
                        phone_col = st.selectbox(
                            "عمود رقم الهاتف" if is_ar else "Phone column",
                            df.columns.tolist(),
                            key="wa_bengali_phone_col"
                        )
                    
                    if st.button("📥 " + ("استخراج البيانات" if is_ar else "Extract Data"), key="extract_bengali_data"):
                        for _, row in df.iterrows():
                            name = str(row[name_col]).strip()
                            phone = str(row[phone_col]).strip()
                            # Clean phone number
                            clean_phone = "".join(filter(str.isdigit, phone))
                            if clean_phone and name != 'nan':
                                target_phones.append(clean_phone)
                                target_names.append(name)
                        
                        st.success(f"✅ {'تم استخراج' if is_ar else 'Extracted'}: {len(target_phones)} {'عميل' if is_ar else 'employers'}")
                except Exception as e:
                    st.error(f"❌ {'خطأ في قراءة الملف' if is_ar else 'Error reading file'}: {str(e)}")
        
        if target_phones:
            # Message input (empty for manual writing)
            st.markdown(f"#### {'اكتب رسالتك' if is_ar else 'Write Your Message'}")
            custom_message = st.text_area(
                "الرسالة" if is_ar else "Message",
                placeholder="اكتب رسالتك هنا... استخدم {Name} لاسم العميل" if is_ar else "Write your message here... Use {Name} for customer name",
                height=200,
                key="wa_bengali_message"
            )
            
            # Random delay settings
            st.markdown(f"#### {'إعدادات التأخير العشوائي' if is_ar else 'Random Delay Settings'}")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                min_delay = st.number_input(
                    "الحد الأدنى (ثواني)" if is_ar else "Min delay (seconds)",
                    min_value=5,
                    max_value=300,
                    value=30,
                    key="wa_bengali_min_delay"
                )
            with col_d2:
                max_delay = st.number_input(
                    "الحد الأقصى (ثواني)" if is_ar else "Max delay (seconds)",
                    min_value=10,
                    max_value=600,
                    value=60,
                    key="wa_bengali_max_delay"
                )
            
            # Message variation settings
            st.markdown(f"#### {'إعدادات تغيير الرسالة' if is_ar else 'Message Variation Settings'}")
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                enable_variation = st.checkbox(
                    "تفعيل تغيير الصيغة" if is_ar else "Enable Message Variation",
                    value=True,
                    help="تغيير صيغة الرسالة كل 5 رسائل بنفس المعنى لتجنب الحظر"
                )
            with col_v2:
                variation_interval = st.number_input(
                    "تغيير كل (رسالة)" if is_ar else "Change every (messages)",
                    min_value=1,
                    max_value=20,
                    value=5,
                    key="wa_bengali_interval"
                )
            
            # Send button
            if st.button("📨 إرسال الرسائل" if is_ar else "📨 Send Messages", type="primary", key="send_bengali_wa"):
                if not custom_message:
                    st.error("❌ " + ("يرجى كتابة الرسالة أولاً" if is_ar else "Please write a message first"))
                elif not target_phones:
                    st.error("❌ " + ("لا يوجد أرقام هواتف صالحة" if is_ar else "No valid phone numbers"))
                else:
                    # Send messages
                    success_count = 0
                    fail_count = 0
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, (phone, name) in enumerate(zip(target_phones, target_names)):
                        status_text.text(f"{'جاري الإرسال إلى' if is_ar else 'Sending to'}: {name} ({i+1}/{len(target_phones)})")
                        
                        # Generate message variation
                        if enable_variation and (i + 1) % variation_interval == 0:
                            # Simple variation: change greeting and structure
                            variations = [
                                custom_message,
                                custom_message.replace("مرحبا", "أهلاً").replace("Hello", "Hi"),
                                custom_message.replace("،", ".").replace(",", "."),
                                custom_message.replace("\n\n", "\n"),
                                custom_message.replace(".", "...")
                            ]
                            message_to_send = variations[(i // variation_interval) % len(variations)]
                        else:
                            message_to_send = custom_message
                        
                        # Replace {Name} placeholder
                        message_to_send = message_to_send.replace("{Name}", name).replace("{name}", name)
                        
                        # Send message
                        success, msg = st.session_state.wa_service.send_message(phone, message_to_send)
                        
                        if success:
                            success_count += 1
                        else:
                            fail_count += 1
                            st.warning(f"⚠️ {name}: {msg}")
                        
                        progress_bar.progress((i + 1) / len(target_phones))
                        
                        # Random delay between messages (anti-ban)
                        if i < len(target_phones) - 1:  # Don't delay after last message
                            # Use uniform for more natural random delay
                            random_delay = int(random.uniform(min_delay, max_delay))
                            delay_text = f"⏳ {'تأخير عشوائي' if is_ar else 'Random delay'}: {random_delay} {'ثانية' if is_ar else 'seconds'}"
                            
                            for s_sec in range(random_delay, 0, -1):
                                status_text.text(f"{delay_text} ({s_sec}s)")
                                if s_sec % 10 == 0:
                                    st.session_state.wa_service.keep_alive()
                                time.sleep(1)
                            
                            # Anti-ban: Secondary random micro-rest (1-3 seconds)
                            micro_rest = random.uniform(1.0, 3.0)
                            time.sleep(micro_rest)
                            
                            # 🛡️ استراحة "تفكير" مفاجئة كل 3-6 رسائل لمحاكاة التعب البشري
                            if i > 0 and i % random.randint(3, 6) == 0:
                                stealth_break = random.uniform(6.0, 15.0)
                                st.toast("🛡️ " + ("استراحة تمويهية قصيرة..." if is_ar else "Short stealth break..."), icon="⏳")
                                time.sleep(stealth_break)
                    
                    status_text.empty()
                    progress_bar.empty()
                    
                    st.success(f"✅ {'تم الإرسال بنجاح' if is_ar else 'Sending completed'}: {success_count} {'رسالة' if is_ar else 'messages'}")
                    if fail_count > 0:
                        st.warning(f"⚠️ {'فشل' if is_ar else 'Failed'}: {fail_count}")
        return


    # === Original WhatsApp Marketing (2026) ===
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
                with st.expander("🔍 تفاصيل الخطأ التقني | Error Details", expanded=True):
                    st.code(st.session_state.wa_service.last_error, language=None)
                    st.info("💡 نصيحة: تأكد من إغلاق أي متصفح كروم مفتوح في الخلفية وحاول مرة أخرى." if is_ar else "💡 Tip: Make sure to close any background Chrome processes and try again.")
    with c2:
        if st.button(lbl['start_engine'], type="primary", width='stretch'):
            with st.spinner(lbl['starting']):
                if st.session_state.wa_service is None:
                    st.session_state.wa_service = WhatsAppService()
                if hasattr(st.session_state.wa_service, 'close'):
                    try: st.session_state.wa_service.close()
                    except Exception: pass
                ok, msg = st.session_state.wa_service.start_driver(headless=is_cloud, force_clean=False)
                if ok:
                    st.toast(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
    with c3:
        help_msg = "سيتم مسح بيانات تسجيل الدخول بالكامل. ستحتاج لمسح الباركود مرة أخرى." if is_ar else "This will clear all login data. You will need to scan the QR code again."
        if st.button(lbl['full_reset'], width='stretch', help=help_msg):
            with st.spinner(lbl['resetting']):
                if st.session_state.wa_service is None:
                    st.session_state.wa_service = WhatsAppService()
                if hasattr(st.session_state.wa_service, 'close'):
                    try: st.session_state.wa_service.close()
                    except Exception: pass
                ok, msg = st.session_state.wa_service.start_driver(headless=is_cloud, force_clean=True)
                if ok:
                    st.toast(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

    # 2. QR CODE SECTION
    if status == "Awaiting Login":
        qr_b64 = st.session_state.wa_service.get_qr_hd()
        if qr_b64:
            src = qr_b64 if qr_b64.startswith("data:") else f"data:image/png;base64,{qr_b64}"
            st.markdown(f'<div style="background: #FFFFFF; padding: 25px; border-radius: 20px; max-width: 420px; margin: 15px auto; text-align: center; box-shadow: 0 0 40px rgba(255,255,255,0.4);"><img src="{src}" style="width: 350px; height: 350px; image-rendering: pixelated; image-rendering: crisp-edges;" /></div>', unsafe_allow_html=True)
        else:
            st.info(lbl['qr_loading'])
        
        b1, b2 = st.columns(2)
        with b1:
            if st.button(lbl['refresh_qr'], width='stretch'):
                st.rerun()
        with b2:
            if st.button(lbl['verify'], width='stretch', type="primary"):
                with st.spinner(lbl['verifying']):
                    connected = st.session_state.wa_service.wait_for_connection(timeout=30)
                if connected:
                    st.toast(lbl['connected_ok'])
                    st.balloons()
                else:
                    st.error(lbl['not_connected'])
                st.rerun()

    # 3. INPUT + BROADCAST
    if status == "Connected" or st.session_state.get('wa_running', False):
        st.markdown("---")
        
        # --- 🏗️ Linear Layout: Images Top, Main Middle, Review Bottom ---
        top_branding = st.container()
        main_col = st.container()
        review_col = st.container()

        # (Branding images removed from here as requested, keeping current layout container)
        with top_branding:
            pass
        
        with review_col:
            if True:
                # --- 📋 Review Contacts Table (Moved under Send Button) ---
                if st.session_state.wa_review_targets:
                    pending_list = [trg for trg in st.session_state.wa_review_targets if not trg['is_sent']]
                    excluded_list = [trg for trg in st.session_state.wa_review_targets if trg['is_sent']]
                    
                    st.markdown("##### " + lbl['review_section'])
                    
                    # 1. READY LIST (Items NOT checked)
                    if pending_list:
                        with st.expander(f"📥 {lbl['total_pending'].format(len(pending_list))}", expanded=True):
                            to_delete = []
                            with st.container(height=350):
                                for i, trg in enumerate(st.session_state.wa_review_targets):
                                    if trg['is_sent']: continue
                                    r_c1, r_c2 = st.columns([4, 1])
                                    # Use simplified display for sidebar
                                    if r_c1.checkbox(f"{trg['name']} ({trg['phone'][-4:]})", value=False, key=f"trg_pending_{i}_{trg['phone']}"):
                                        st.session_state.wa_review_targets[i]['is_sent'] = True
                                        st.session_state.wa_history.add(trg['phone'])
                                        save_wa_history(st.session_state.wa_history)
                                        st.rerun()
                                    if r_c2.button("🗑️", key=f"trg_del_p_{i}_{trg['phone']}"):
                                        to_delete.append(i)
                            
                            if to_delete:
                                for idx in sorted(to_delete, reverse=True):
                                    deleted_item = st.session_state.wa_review_targets.pop(idx)
                                    if st.session_state.wa_data is not None and 'idx' in deleted_item:
                                        st.session_state.wa_data = st.session_state.wa_data.drop(deleted_item['idx'])
                                st.rerun()

                    # 2. EXCLUDED LIST (Items Checked)
                    if excluded_list:
                        with st.expander(f"✅ {lbl['review_section']} ({len(excluded_list)})", expanded=False):
                            if st.button(lbl['uncheck_all'], width='stretch', key="uncheck_all_side"):
                                for i in range(len(st.session_state.wa_review_targets)):
                                    st.session_state.wa_review_targets[i]['is_sent'] = False
                                st.session_state.wa_history = set()
                                save_wa_history(st.session_state.wa_history)
                                st.rerun()

                            with st.container(height=250):
                                for i, trg in enumerate(st.session_state.wa_review_targets):
                                    if not trg['is_sent']: continue
                                    r_c3, r_c4 = st.columns([4, 1])
                                    clean_id = trg['phone']
                                    if not r_c3.checkbox(f"{trg['name']} ({trg['phone'][-4:]})", value=True, key=f"trg_excl_{i}_{clean_id}"):
                                        st.session_state.wa_review_targets[i]['is_sent'] = False
                                        st.session_state.wa_history.discard(clean_id)
                                        save_wa_history(st.session_state.wa_history)
                                        st.rerun()
                                    if r_c4.button("🗑️", key=f"trg_del_e_{i}_{trg['phone']}"):
                                        deleted_item = st.session_state.wa_review_targets.pop(i)
                                        if st.session_state.wa_data is not None and 'idx' in deleted_item:
                                            st.session_state.wa_data = st.session_state.wa_data.drop(deleted_item['idx'])
                                        st.rerun()

        with main_col:
            # 🛡️ 2026 Anti-Ban Shield Guidance Banner
            with st.expander("🛡️ " + ("درع الحماية التلقائي وتجنب الحظر (Anti-Ban Shield 2026)" if is_ar else "Anti-Ban Shield & Safety Guide"), expanded=False):
                st.markdown("""
                <div style="background: rgba(0, 255, 136, 0.07); padding: 15px; border-radius: 12px; border: 1px solid rgba(0, 255, 136, 0.3); color: #e0e0e0;">
                    <h5 style="color: #00FF88; margin-top: 0;">✅ التقنيات المفعّلة حمايتها تلقائياً في النظام:</h5>
                    <ul style="font-size: 0.9rem; line-height: 1.6;">
                        <li><b>حقن الرموز غير المرئية (Zero-Width Fingerprinting):</b> يتم تغيير التوقيع المشفر لكل رسالة تلقائياً لمنع خوارزميات واتساب من اكتشاف التكرار.</li>
                        <li><b>دعم الـ Spintax:</b> يمكنك كتابة <code>{مرحباً|أهلاً|السلام عليكم}</code> وسيتم اختيار خيار عشوائي لكل مستلم.</li>
                        <li><b>الطباعة البشرية وتفاعل الماوس:</b> تحاكي حركة الماوس والتأخيرات البشرية العشوائية أثناء الكتابة.</li>
                        <li><b>تمويه أسماء المرفقات:</b> يتم تغيير اسم أي ملف مرفق تلقائياً لمنع اكتشاف بصمة الملفات المتكررة.</li>
                    </ul>
                    <hr style="border-color: rgba(255,255,255,0.1);">
                    <h5 style="color: #FFD700; margin-top: 5px;">⚠️ إرشادات هامة جداً لمنع حظر رقمك:</h5>
                    <ol style="font-size: 0.9rem; line-height: 1.6;">
                        <li><b>مهلة الإرسال:</b> احرص أن تكون المهلة بين <b>30 إلى 60 ثانية</b> على الأقل.</li>
                        <li><b>الاستراحة بين الدفعات:</b> فعّل استراحة (مثلاً: توقف 10 دقائق بعد كل 10 رسائل).</li>
                        <li><b>تدرج الإرسال (Warming Up):</b> للأرقام الجديدة، لا ترسل أكثر من 30-50 رسالة يومياً في البداية.</li>
                        <li><b>تجنب بلاغات السبام:</b> أضف في نهاية رسالتك جملة مثل: <i>(إذا كنت لا ترغب بتلقي الرسائل أرسل إلغاء)</i> لتجنب قيام المستلم بالضغط على زر "إبلاغ وحظر".</li>
                    </ol>
                </div>
                """, unsafe_allow_html=True)

            t_manual, t_xl = st.tabs([lbl['tab_manual'], lbl['tab_excel']])
            
            rebuild_review = False
            manual_list = []
            with t_manual:
                txt = st.text_area(lbl['paste_numbers'], height=100)
                manual_list, _, _ = validate_numbers(txt)
                if manual_list:
                    if st.session_state.get('wa_last_manual_count', 0) != len(manual_list) or txt != st.session_state.get('wa_last_txt', ''):
                        rebuild_review = True
                        st.session_state.wa_last_manual_count = len(manual_list)
                        st.session_state.wa_last_txt = txt

            with t_xl:
                uploaded = st.file_uploader(lbl['upload_excel'], type=["xlsx"], key=st.session_state.get('wa_upload_key', 'xl_0'))
                if uploaded:
                    df = pd.read_excel(uploaded)
                    if st.session_state.get('wa_last_uploaded_name') != uploaded.name:
                        rebuild_review = True
                        st.session_state.wa_last_uploaded_name = uploaded.name
                        st.session_state.wa_data = df
                    
                    xl_col1, xl_col2 = st.columns([3, 1])
                    display_count = len(st.session_state.wa_review_targets) if st.session_state.wa_review_targets else len(df)
                    with xl_col1: st.success(lbl['loaded_count'].format(display_count))
                    with xl_col2:
                        if st.button(lbl['delete_file'], width='stretch', key="del_xl"):
                            st.session_state.wa_data = None
                            st.session_state.wa_review_targets = []
                            st.session_state.wa_last_uploaded_name = None
                            st.session_state.wa_upload_key = 'xl_1' if st.session_state.get('wa_upload_key') == 'xl_0' else 'xl_0'
                            st.rerun()
                elif st.session_state.wa_data is not None:
                    xl_col1, xl_col2 = st.columns([3, 1])
                    display_count = len(st.session_state.wa_review_targets) if st.session_state.wa_review_targets else len(st.session_state.wa_data)
                    with xl_col1: st.info(lbl['loaded_count'].format(display_count))
                    with xl_col2:
                        if st.button(lbl['delete_file'], width='stretch', key="del_xl2"):
                            st.session_state.wa_data = None
                            st.session_state.wa_review_targets = []
                            st.session_state.wa_last_uploaded_name = None
                            st.session_state.wa_upload_key = 'xl_1' if st.session_state.get('wa_upload_key') == 'xl_0' else 'xl_0'
                            st.rerun()
            
            # Build review targets if data changed or list is empty but data exists
            if rebuild_review or (not st.session_state.wa_review_targets and (manual_list or st.session_state.wa_data is not None)):
                new_targets = []
                seen_in_current_file = set()
                dups_count = 0
                
                # Manual
                if manual_list:
                    for n in manual_list:
                        if n in seen_in_current_file: dups_count += 1; continue 
                        new_targets.append({'phone': n, 'name': 'Client', 'cv': '', 'is_sent': (n in st.session_state.wa_history)})
                        seen_in_current_file.add(n)
                # Excel
                if st.session_state.wa_data is not None:
                    df_curr = st.session_state.wa_data
                    def find_c(keys):
                        for c in df_curr.columns:
                            if any(k in str(c).lower() for k in keys): return c
                        return None
                    c_name = find_c(["اسم", "name"])
                    c_phone = find_c(["واتساب", "رقم", "هاتف", "phone", "جوال"])
                    c_cv = find_c(["سيرة", "cv", "resume", "link"])
                    
                    for idx, row in df_curr.iterrows():
                        raw_p = str(row[c_phone]).strip() if c_phone else ""
                        phone = format_phone_number(raw_p)
                        if not phone: phone = format_phone_number("".join(raw_p.split()))
                        
                        if phone:
                            if phone in seen_in_current_file: dups_count += 1; continue
                            target_data = {str(col): str(row[col]).strip() if pd.notna(row[col]) else "" for col in df_curr.columns}
                            target_data.update({'idx': idx, 'phone': phone, 'is_sent': (phone in st.session_state.wa_history)})
                            target_data['name'] = str(row[c_name]).strip() if (c_name and pd.notna(row[c_name])) else "عميل"
                            target_data['cv'] = str(row[c_cv]).strip() if (c_cv and pd.notna(row[c_cv])) else ""
                            new_targets.append(target_data)
                            seen_in_current_file.add(phone)
                
                if dups_count > 0: st.toast(lbl['dups_removed'].format(dups_count), icon="✂️")
                if new_targets:
                    st.session_state.wa_review_targets = new_targets
                    st.session_state.wa_done = False
                    st.rerun()
            
        # Consolidate Pending Targets for the rest of the application
        # Only recalculate if not currently running to avoid state issues
        if not st.session_state.wa_running:
            final_targets = [trg for trg in st.session_state.wa_review_targets if not trg['is_sent']]
        else:
            # Use active targets during sending to maintain consistency
            final_targets = st.session_state.get('wa_active_targets', [])

        
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

I hope you are doing well.

We are currently evaluating candidates for various job opportunities with us, and we'd love to know if you are still looking for a position.

A quick reply would be great:
YES – Proceed with me
NO – Don't proceed

If you are not currently seeking opportunities, we would highly appreciate it if you could share this message with a friend or colleague who may be looking for employment.

Best regards,
Abu Fahd
HR Manager"""
        
        # Smart Message Toggle
        is_smart = st.checkbox(lbl['smart_msg'], value=st.session_state.get('wa_smart_mode', False), help=lbl['smart_msg_help'], key="wa_smart_mode")
        
        # When Smart Mode is enabled, handle template logic
        if is_smart:
            sel_tpl_name = st.session_state.get('wa_selected_template_key')
            if sel_tpl_name:
                ct = load_templates().get("custom", {})
                active_tpl = ct.get(sel_tpl_name)
                if active_tpl and isinstance(active_tpl, dict) and active_tpl.get('is_smart'):
                    # If the selected template IS a smart one, prioritize its settings
                    if st.session_state.wa_messages[0] != active_tpl['body']:
                         st.session_state.wa_messages[0] = active_tpl['body']
                    if active_tpl.get('job_title') and not st.session_state.get('wa_custom_job'):
                         st.session_state.wa_custom_job = active_tpl['job_title']

        # Custom Job Title Input for Smart Mode
        custom_job = ""
        if is_smart:
            custom_job = st.text_input(lbl['job_title_label'], placeholder=lbl['job_title_placeholder'], key="wa_custom_job")
            st.session_state.wa_custom_job_val = custom_job # Store for sending logic
        
        # Initialize first message if empty
        if not st.session_state.wa_messages[0]:
            st.session_state.wa_messages[0] = default_msg
        
        # --- ⌨️ Message Input Logic ---
        if not is_smart:
            for i in range(len(st.session_state.wa_messages)):
                msg_col1, msg_col2 = st.columns([11, 1])
                with msg_col1:
                    label = lbl['msg_label'] if i == 0 else lbl['msg_num'].format(i + 1)
                    st.session_state.wa_messages[i] = st.text_area(label, height=250, value=st.session_state.wa_messages[i], key=f"wa_msg_{i}")
                with msg_col2:
                    if i > 0:
                        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
                        if st.button(lbl['remove_msg'], key=f"del_msg_{i}"):
                            st.session_state.wa_messages.pop(i)
                            st.rerun()

            # Add Message Button
            if st.button(lbl['add_msg'], key="add_msg_btn"):
                new_smart_msg = generate_smart_message("{Name}", "{CV}")
                st.session_state.wa_messages.append(new_smart_msg)
                st.rerun()
        else:
            # Preview of Smart Message
            st.info("💡 " + ("سيتم توليد رسالة فريدة لكل رقم تلقائياً عند بدء الإرسال." if is_ar else "A unique message will be generated for each number upon sending."))
            preview_msg = generate_smart_message("{Name}", "{CV}", custom_job=st.session_state.get('wa_custom_job_val', ''))
            st.text_area("معاينة الرسالة الذكية (Smart Message Preview)", value=preview_msg, height=250, disabled=True)
            
        # --- 📁 Templates Library Logic (Self-contained at start to avoid state conflicts) ---
        templates_data = load_templates()
        custom_templates = templates_data.get("custom", {})
        
        # Check if we should apply a template (button is triggered via rerun)
        # We handle the 'Apply' logic early if the button was clicked in the previous run
        # Note: Streamlit buttons return True ONLY in the run they were clicked.
        # But we can use on_click to be safer.


        # UI for Templates Library
        with st.expander(lbl['wa_templates_title']):
            if custom_templates:
                template_to_use = st.selectbox(lbl['wa_use_template'], options=list(custom_templates.keys()), key="wa_selected_template_key")
                
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    # Define the callback to avoid state modification error
                    def apply_template():
                        sel = st.session_state.wa_selected_template_key
                        tpl = custom_templates[sel]
                        if isinstance(tpl, dict):
                            st.session_state.wa_messages[0] = tpl['body']
                            st.session_state.wa_smart_mode = tpl.get('is_smart', False)
                            if tpl.get('job_title'):
                                st.session_state.wa_custom_job = tpl['job_title']
                                st.session_state.wa_custom_job_val = tpl['job_title']
                        else:
                            st.session_state.wa_messages[0] = tpl
                            st.session_state.wa_smart_mode = False
                        st.session_state.wa_msg_applied_toast = f"✅ {sel} applied!"

                    st.button(lbl['wa_use_template'], key="apply_template_btn", on_click=apply_template)
                
                if st.session_state.get('wa_msg_applied_toast'):
                    st.toast(st.session_state.wa_msg_applied_toast)
                    del st.session_state.wa_msg_applied_toast
            
            # Save Current Message as Template
            st.markdown("---")
            new_template_name = st.text_input(lbl['wa_template_name'], key="new_tpl_name")
            
            def save_current_as_template():
                name = st.session_state.new_tpl_name
                if name.strip():
                    # Save as the new dict format
                    templates_data["custom"][name] = {
                        "body": st.session_state.wa_messages[0],
                        "is_smart": st.session_state.wa_smart_mode,
                        "job_title": st.session_state.get('wa_custom_job', '')
                    }
                    save_templates(templates_data)
                    st.session_state.wa_msg_save_success = f"✅ {name} saved!"
                else:
                    st.session_state.wa_msg_save_error = "Please enter a template name"

            st.button(lbl['wa_save_as_template'], on_click=save_current_as_template)
            
            if st.session_state.get('wa_msg_save_success'):
                st.success(st.session_state.wa_msg_save_success)
                del st.session_state.wa_msg_save_success
            if st.session_state.get('wa_msg_save_error'):
                st.error(st.session_state.wa_msg_save_error)
                del st.session_state.wa_msg_save_error

            # Manage / Delete Templates
            if custom_templates:
                st.markdown("---")
                st.markdown(lbl['wa_manage_templates'])
                for t_name in list(custom_templates.keys()):
                    m_col1, m_col2 = st.columns([4, 1])
                    m_col1.text(t_name)
                    
                    def delete_tpl(name=t_name):
                        del templates_data["custom"][name]
                        save_templates(templates_data)

                    m_col2.button(lbl['wa_delete_template'], key=f"del_tpl_{t_name}", on_click=delete_tpl)
            st.info(lbl['wa_placeholders_guide'])

        # --- ⚙️ Smart Templates Components Editor ---
        with st.expander("🛠️ " + ("تعديل مكونات الرسائل الذكية" if is_ar else "Edit Smart Message Components")):
            templates_data = load_templates()
            smart_parts = templates_data.get("smart", SMART_TEMPLATES)
            changed_parts = False
            for part_key, part_list in smart_parts.items():
                st.markdown(f"**{part_key.replace('_', ' ').title()}**")
                new_list_str = st.text_area(f"Options for {part_key}", value="\n".join(part_list), height=100, key=f"smart_part_{part_key}")
                new_list = [line.strip() for line in new_list_str.split("\n") if line.strip()]
                if new_list != part_list:
                    smart_parts[part_key] = new_list
                    changed_parts = True
            if changed_parts:
                if st.button("💾 " + ("حفظ جميع التغييرات" if is_ar else "Save All Changes"), key="save_smart_parts"):
                    templates_data["smart"] = smart_parts
                    save_templates(templates_data)
                    st.toast("✅ Smart components updated!")
                    st.rerun()
        
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
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            delay = st.number_input(lbl['delay'], min_value=5, max_value=600, value=60, disabled=st.session_state.wa_running)
        with col_s2:
            batch_size = st.number_input(lbl['batch_size'], min_value=0, max_value=1000, value=10, help=lbl['batch_help'], disabled=st.session_state.wa_running)
        with col_s3:
            batch_delay_mins = st.number_input(lbl['batch_delay'], min_value=1, max_value=60, value=10, disabled=st.session_state.wa_running)
            batch_delay = int(batch_delay_mins * 60)
        with col_s4:
            msg_switch_threshold = st.number_input("تبديل الرسالة بعد" if is_ar else "Switch msg after", min_value=1, max_value=1000, value=1, disabled=st.session_state.wa_running)

        # Smart detect target changes
        current_fp = ",".join([trg['phone'] for trg in final_targets]) if final_targets else ""
        if current_fp != st.session_state.get('wa_sent_fingerprint', ''):
            st.session_state.wa_done = False

        # ══════════════════════════════════════════════════════════
        # 🚀 وضع الإرسال الخلفي - يعمل حتى بعد إغلاق المتصفح
        # ══════════════════════════════════════════════════════════
        worker_state = mgr.get_state()
        worker_status = worker_state.get("status", "not_started")
        worker_alive  = mgr.is_worker_alive()
        is_sending    = worker_alive and worker_status == "sending"

        # تحديث سجلات الإرسال من العامل الخلفي
        bg_logs = mgr.get_logs()
        if bg_logs:
            # دمج السجلات الجديدة فقط
            existing_phones_times = {(e.get('phone',''), e.get('time','')) for e in st.session_state.wa_logs if isinstance(e, dict)}
            for entry in bg_logs:
                key = (entry.get('phone',''), entry.get('time',''))
                if key not in existing_phones_times:
                    st.session_state.wa_logs.append(entry)
                    existing_phones_times.add(key)

        # ─── أزرار الإرسال / الإيقاف ───
        btn1, btn2, btn3 = st.columns([1, 1, 2])
        with btn1:
            if is_sending:
                if st.button(lbl['stop'], type="primary", width='stretch', key="bg_stop_btn"):
                    mgr.stop_worker()
                    st.session_state.wa_running = False
                    st.toast("🛑 " + ("تم إيقاف الإرسال" if is_ar else "Sending stopped"))
                    st.rerun()
            else:
                has_valid_msg = any(msg.strip() != "" for msg in st.session_state.wa_messages)
                ready = len(final_targets) > 0 and has_valid_msg

                if worker_status == "done" and current_fp == st.session_state.get('wa_sent_fingerprint', ''):
                    st.button(lbl['sent_done'], disabled=True, width='stretch')
                else:
                    if st.button(lbl['send'].format(len(final_targets)), disabled=not ready, width='stretch', type="primary", key="bg_send_btn"):
                        # ── حفظ المرفق في ملف مؤقت ──
                        temp_path = None
                        if attachment:
                            import tempfile
                            suffix = os.path.splitext(attachment.name)[1]
                            t_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix,
                                                                 dir=os.path.join(os.getcwd(), ".whatsapp_session"))
                            t_file.write(attachment.getvalue())
                            t_file.close()
                            temp_path = t_file.name
                            st.session_state.wa_temp_path = temp_path

                        # ── تشغيل العامل الخلفي ──
                        mgr.start_worker()
                        time.sleep(1.5)

                        # ── أرسل الوظيفة ──
                        job_id = mgr.send_job(
                            targets            = final_targets,
                            messages           = st.session_state.wa_messages,
                            delay              = delay,
                            batch_size         = int(batch_size),
                            batch_delay        = int(batch_delay),
                            is_smart           = bool(st.session_state.get('wa_smart_mode', False)),
                            custom_job         = st.session_state.get('wa_custom_job_val', ''),
                            attachment_path    = temp_path,
                            msg_switch_threshold = int(msg_switch_threshold),
                            start_from         = 0
                        )
                        st.session_state.wa_running = True
                        st.session_state.wa_done = False
                        st.session_state.wa_sent_fingerprint = current_fp
                        st.session_state.wa_active_job_id = job_id
                        st.toast("🚀 " + ("بدأ الإرسال في الخلفية! يمكنك إغلاق المتصفح" if is_ar else "Sending started in background! You can close the browser"), icon="✅")
                        st.rerun()

        # ─── بطاقة الحالة الخلفية ───
        if is_sending or worker_status in ("starting", "awaiting_login"):
            w_idx   = worker_state.get("current_idx", 0)
            w_total = worker_state.get("total", len(final_targets))
            w_name  = worker_state.get("current_name", "")
            w_phone = worker_state.get("current_phone", "")
            countdown = worker_state.get("countdown", 0)
            countdown_type = worker_state.get("countdown_type", "normal")

            countdown_icons = {
                "batch_break": "🛡️", "think_break": "🧠",
                "stealth_break": "🥷", "normal": "⏳"
            }
            c_icon = countdown_icons.get(countdown_type, "⏳")

            if countdown > 0:
                m, s = divmod(countdown, 60)
                time_str = f"{m}د {s}ث" if is_ar else f"{m}m {s}s"
                countdown_label = f"{c_icon} {'الانتظار بين الرسائل' if is_ar else 'Waiting'}: {time_str}"
            else:
                countdown_label = f"📤 {'جاري الإرسال' if is_ar else 'Sending'}..."

            sent_pct = (w_idx / w_total * 100) if w_total > 0 else 0

            st.markdown(f"""
            <div style="background:rgba(0,255,100,0.05);padding:16px;border-radius:14px;border:1.5px solid rgba(0,255,100,0.25);margin-bottom:12px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <span style="color:#00FF88;font-weight:700;font-size:1.05rem;">✅ {'تم الإرسال' if is_ar else 'Sent'}: {w_idx}</span>
                    <span style="color:#D4AF37;font-weight:700;font-size:1.05rem;">⌛ {'متبقٍ' if is_ar else 'Remaining'}: {w_total - w_idx}</span>
                </div>
                <div style="background:rgba(255,255,255,0.06);border-radius:8px;height:8px;margin-bottom:10px;overflow:hidden;">
                    <div style="background:linear-gradient(90deg,#00FF88,#D4AF37);height:100%;width:{sent_pct:.1f}%;transition:width 0.5s;"></div>
                </div>
                <div style="color:#aaa;font-size:0.85rem;display:flex;justify-content:space-between;">
                    <span>👤 {w_name} · 📱 {w_phone}</span>
                    <span>{countdown_label}</span>
                </div>
            </div>
            <div style="background:rgba(0,180,255,0.08);padding:10px 16px;border-radius:10px;border:1px solid rgba(0,180,255,0.2);text-align:center;margin-bottom:8px;">
                <span style="color:#00AAFF;font-weight:600;font-size:0.9rem;">
                    🟢 {'الإرسال يعمل في الخلفية — يمكنك إغلاق هذا التبويب بأمان' if is_ar else 'Sending runs in background — safe to close this tab'}
                </span>
            </div>
            """, unsafe_allow_html=True)

            st.progress(min(1.0, sent_pct / 100))

            # تحديث تلقائي كل 5 ثوان لعرض التقدم
            st.markdown("""
            <script>
            (function(){
                if(!window.__wa_bg_refresh){
                    window.__wa_bg_refresh = setInterval(function(){
                        if(document.hasFocus() || true){
                            // Trigger a lightweight Streamlit rerun via clicking a hidden element
                            var btns = window.parent.document.querySelectorAll('button[data-testid="baseButton-secondary"]');
                        }
                    }, 5000);
                }
            })();
            </script>
            """, unsafe_allow_html=True)

            time.sleep(4)
            st.rerun()

        elif worker_status == "done" and worker_alive:
            st.success("🎉 " + ("اكتمل الإرسال بنجاح!" if is_ar else "Sending completed successfully!"))
            st.balloons()
            st.session_state.wa_running = False
            st.session_state.wa_done = True

        elif worker_status == "error":
            st.error("❌ " + worker_state.get("error", "خطأ في الإرسال"))

        elif worker_status == "awaiting_login":
            st.warning("📱 " + ("يرجى مسح رمز QR من واتساب ثم الضغط تحقق" if is_ar else "Please scan QR code from WhatsApp then click Verify"))

        # 📄 Professional 2026 Log Section
        if st.session_state.wa_logs:
            st.markdown("---")
            with st.expander(lbl['log_title'], expanded=True):
                log_h, log_del = st.columns([3, 1])
                with log_del:
                    if st.button(lbl['delete_log'], width='stretch', key="clear_log_btn"):
                        st.session_state.wa_logs = []
                        st.session_state.wa_done = False
                        st.rerun()
                
                # Render logs in reverse (newest first)
                for entry in reversed(st.session_state.wa_logs):
                    # Fallback for old string-based logs if any exist during the transition
                    if isinstance(entry, str):
                        st.text(entry)
                        continue
                        
                    status_class = "status-success" if entry['ok'] else "status-error"
                    status_icon = "CHECK" if entry['ok'] else "ERROR" # Simplified icons or text
                    status_text = entry['status']
                    
                    # Modern Luxury Card Rendering
                    st.markdown(f"""
                    <div class="log-card">
                        <div class="log-info">
                            <div class="log-name">{entry['name']}</div>
                            <div class="log-phone">📱 {entry['phone']}</div>
                        </div>
                        <div class="log-status-group">
                            <div class="log-status">
                                <span class="status-badge {status_class}">{status_text}</span>
                                <span class="log-time">🕒 {entry['time']}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # Diagnostic
        if status not in ["Connected", "Awaiting Login"]:
            with st.expander(lbl['diag']):
                if st.button(lbl['screenshot']):
                    img = st.session_state.wa_service.get_diagnostic_screenshot()
                    if img: st.image(f"data:image/png;base64,{img}")
