import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime
from src.services.whatsapp_service import WhatsAppService
from src.utils.phone_utils import validate_numbers, format_phone_number, save_to_local_desktop, render_pasha_export_button
from src.core.i18n import t
from src.config import WA_HISTORY_FILE
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
        "We are currently proceeding with candidates for available job opportunities",
        "We are moving forward with selecting candidates for open job opportunities",
        "We are in the process of reviewing candidates for various job opportunities",
        "Our team is currently evaluating candidates for several job opportunities",
        "We are actively matching candidates with the latest job opportunities"
    ],
    "body_end": [
        ", and since you previously showed interest, we would like to confirm your availability.",
        ". Based on your previous interest, we want to check if you are still available.",
        ", and we're checking in to see if you're still interested and ready to work.",
        ". Since you expressed interest before, please let us know your current status.",
        ", and we'd love to know if you are still looking for a position."
    ],
    "closing": [
        "Please reply with one of the following:\nYES – I am interested and available\nNO – I am not available at the moment",
        "Kindly respond with:\nYES – Still interested and available\nNO – Not available right now",
        "Let us know your choice:\nYES – I want to proceed\nNO – Not interested at this time",
        "Please confirm by replying:\nYES – I am ready\nNO – I have another job",
        "A quick reply would be great:\nYES – Proceed with me\nNO – Don't proceed"
    ],
    "final_call": [
        "We will be moving forward shortly, so your quick response is highly appreciated.",
        "We are finalizing our list soon, so please get back to us as soon as possible.",
        "The selection process is moving fast, and we value your prompt reply.",
        "To ensure you don't miss out, please let us know your status shortly.",
        "We look forward to hearing from you at your earliest convenience."
    ]
}

def generate_smart_message(name, cv_link, custom_job=""):
    intro = random.choice(SMART_TEMPLATES["intro"])
    b_start = random.choice(SMART_TEMPLATES["body_start"])
    b_end = random.choice(SMART_TEMPLATES["body_end"])
    closing = random.choice(SMART_TEMPLATES["closing"])
    final_call = random.choice(SMART_TEMPLATES["final_call"])
    
    # Handle custom job title injection
    job_part = f" in {custom_job}" if custom_job.strip() else ""
    full_body = f"{b_start}{job_part}{b_end}"
    
    msg = f"Hello {name},\n\n{intro}\n\n{full_body}\n\n{closing}\n\n{final_call}\n\n"
    
    # Logic: If CV exists, add CV link. If not, omit it.
    if cv_link and str(cv_link).lower() != 'nan' and str(cv_link).strip() != '':
        msg += f"Link to your profile: {cv_link}\n\n"
    
    msg += "Best regards,\nAbu Fahd"
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
    lang = st.session_state.get('lang', 'ar')
    is_ar = lang == 'ar'
    is_cloud = "/mount/" in __file__
    
    if 'wa_service' not in st.session_state:
        st.session_state.wa_service = WhatsAppService()
    else:
        # Check if the existing service object is outdated (missing attachment_path in send_message)
        try:
            import inspect
            sig = inspect.signature(st.session_state.wa_service.send_message)
            if 'attachment_path' not in sig.parameters:
                st.session_state.wa_service = WhatsAppService()
        except:
            pass

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

    # 3. INPUT + BROADCAST
    if status == "Connected":
        st.markdown("---")
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
                # Show unique count if targets are already processed, otherwise show raw count
                display_count = len(st.session_state.wa_review_targets) if st.session_state.wa_review_targets else len(df)
                with xl_col1: st.success(lbl['loaded_count'].format(display_count))
                with xl_col2:
                    if st.button(lbl['delete_file'], use_container_width=True, key="del_xl"):
                        st.session_state.wa_data = None
                        st.session_state.wa_review_targets = []
                        st.session_state.wa_last_uploaded_name = None
                        st.session_state.wa_upload_key = 'xl_1' if st.session_state.get('wa_upload_key') == 'xl_0' else 'xl_0'
                        st.rerun()
            elif st.session_state.wa_data is not None:
                xl_col1, xl_col2 = st.columns([3, 1])
                # Show unique count if available
                display_count = len(st.session_state.wa_review_targets) if st.session_state.wa_review_targets else len(st.session_state.wa_data)
                with xl_col1: st.info(lbl['loaded_count'].format(display_count))
                with xl_col2:
                    if st.button(lbl['delete_file'], use_container_width=True, key="del_xl2"):
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
                    if n in seen_in_current_file:
                        dups_count += 1
                        continue 
                    
                    new_targets.append({
                        'phone': n, 'name': 'Client', 'cv': '', 
                        'is_sent': (n in st.session_state.wa_history)
                    })
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
                        # 1. Check for duplicates within the current input
                        if phone in seen_in_current_file:
                            dups_count += 1
                            continue # Totally remove duplicates as requested
                            
                        # 2. Build target data safely (Don't let Excel columns overwrite phone/name/cv)
                        # Load all columns first
                        target_data = {str(col): str(row[col]).strip() if pd.notna(row[col]) else "" for col in df_curr.columns}
                        
                        # Set essential keys (Overwriting the raw Excel values with cleaned/calculated ones)
                        target_data['idx'] = idx
                        target_data['phone'] = phone
                        target_data['name'] = str(row[c_name]).strip() if c_name else target_data.get('الاسم', "عميل")
                        target_data['cv'] = str(row[c_cv]).strip() if c_cv else target_data.get('السيرة', "")
                        
                        # 3. Check permanent history
                        target_data['is_sent'] = (phone in st.session_state.wa_history)
                        
                        new_targets.append(target_data)
                        seen_in_current_file.add(phone)
            
            if dups_count > 0:
                st.toast(lbl['dups_removed'].format(dups_count), icon="✂️")
            
            if new_targets:
                st.session_state.wa_review_targets = new_targets
                st.session_state.wa_done = False
                st.rerun()

        # --- 📋 Review Contacts Table ---
        if st.session_state.wa_review_targets:
            pending_list = [t for t in st.session_state.wa_review_targets if not t['is_sent']]
            excluded_list = [t for t in st.session_state.wa_review_targets if t['is_sent']]
            
            st.markdown("---")
            # 1. READY LIST (Items NOT checked)
            if pending_list:
                with st.expander(f"📥 {lbl['total_pending'].format(len(pending_list))}", expanded=True):
                    h1, h2, h3, h4 = st.columns([1, 4, 3, 1])
                    h1.markdown(f"**{lbl['col_status']}**")
                    h2.markdown(f"**{lbl['col_name']}**")
                    h3.markdown(f"**{lbl['col_phone']}**")
                    h4.markdown(f"**{lbl['col_action']}**")
                    
                    to_delete = []
                    for i, trg in enumerate(st.session_state.wa_review_targets):
                        if trg['is_sent']: continue
                        r1, r2, r3, r4 = st.columns([1, 4, 3, 1])
                        # Checkbox to Exclude (becomes true)
                        if r1.checkbox("", value=False, key=f"trg_pending_{i}_{trg['phone']}"):
                            st.session_state.wa_review_targets[i]['is_sent'] = True
                            st.session_state.wa_history.add(trg['phone'])
                            save_wa_history(st.session_state.wa_history)
                            st.rerun()
                        
                        r2.text(trg['name'])
                        r3.text(trg['phone'])
                        if r4.button("🗑️", key=f"trg_del_p_{i}_{trg['phone']}"):
                            to_delete.append(i)
                    
                    if to_delete:
                        for idx in sorted(to_delete, reverse=True):
                            deleted_item = st.session_state.wa_review_targets.pop(idx)
                            if st.session_state.wa_data is not None and 'idx' in deleted_item:
                                st.session_state.wa_data = st.session_state.wa_data.drop(deleted_item['idx'])
                        st.rerun()

            # 2. EXCLUDED LIST (Items Checked) - THIS IS THE LIST THE USER ASKED FOR
            if excluded_list:
                with st.expander(f"✅ {lbl['review_section']} (مرسلة أو مكررة: {len(excluded_list)})", expanded=True):
                    if st.button(lbl['uncheck_all'], use_container_width=True):
                        # Reset all is_sent in review list and history
                        for i in range(len(st.session_state.wa_review_targets)):
                            st.session_state.wa_review_targets[i]['is_sent'] = False
                        st.session_state.wa_history = set() # Clear history as requested to return all
                        save_wa_history(st.session_state.wa_history)
                        st.rerun()

                    h1, h2, h3, h4 = st.columns([1, 4, 3, 1])
                    h1.markdown(f"**{lbl['col_status']}**")
                    h2.markdown(f"**{lbl['col_name']}**")
                    h3.markdown(f"**{lbl['col_phone']}**")
                    h4.markdown(f"**{lbl['col_action']}**")
                    
                    to_delete_ex = []
                    for i, trg in enumerate(st.session_state.wa_review_targets):
                        if not trg['is_sent']: continue
                        r1, r2, r3, r4 = st.columns([1, 4, 3, 1])
                        # Uncheck to move to pending (becomes false)
                        # We use cleaned phone here to ensure history sync works
                        clean_id = trg['phone']
                        if not r1.checkbox("", value=True, key=f"trg_excl_{i}_{clean_id}"):
                            st.session_state.wa_review_targets[i]['is_sent'] = False
                            st.session_state.wa_history.discard(clean_id)
                            save_wa_history(st.session_state.wa_history)
                            st.rerun()
                        
                        r2.text(trg['name'])
                        r3.text(trg['phone'])
                        if r4.button("🗑️", key=f"trg_del_e_{i}_{trg['phone']}"):
                            to_delete_ex.append(i)
                    
                    if to_delete_ex:
                        for idx in sorted(to_delete_ex, reverse=True):
                            deleted_item = st.session_state.wa_review_targets.pop(idx)
                            if st.session_state.wa_data is not None and 'idx' in deleted_item:
                                st.session_state.wa_data = st.session_state.wa_data.drop(deleted_item['idx'])
                        st.rerun()
            
        # Consolidate Pending Targets for the rest of the application
        final_targets = [t for t in st.session_state.wa_review_targets if not t['is_sent']]

        
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
        
        # Smart Message Toggle
        is_smart = st.checkbox(lbl['smart_msg'], value=st.session_state.get('wa_smart_mode', False), help=lbl['smart_msg_help'], key="wa_smart_mode")
        
        # Custom Job Title Input for Smart Mode
        custom_job = ""
        if is_smart:
            custom_job = st.text_input(lbl['job_title_label'], placeholder=lbl['job_title_placeholder'], key="wa_custom_job")
            st.session_state.wa_custom_job_val = custom_job # Store for sending logic
        
        # Initialize first message if empty
        if not st.session_state.wa_messages[0]:
            st.session_state.wa_messages[0] = generate_smart_message("{Name}", "{CV}", custom_job=custom_job)
        
        # Render dynamic message fields
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
                # Generate a new smart variation for the added field
                new_smart_msg = generate_smart_message("{Name}", "{CV}")
                st.session_state.wa_messages.append(new_smart_msg)
                st.rerun()
        else:
            # Preview of Smart Message
            st.info("💡 " + ("سيتم توليد رسالة فريدة لكل رقم تلقائياً عند بدء الإرسال." if is_ar else "A unique message will be generated for each number upon sending."))
            preview_msg = generate_smart_message("{Name}", "{CV}", custom_job=st.session_state.get('wa_custom_job_val', ''))
            st.text_area("معاينة الرسالة الذكية (Smart Message Preview)", value=preview_msg, height=250, disabled=True)
            
            # Ensure ready logic works in smart mode
            has_valid_msg = True 
        
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
                # Check if at least one message is not empty
                has_valid_msg = any(msg.strip() != "" for msg in st.session_state.wa_messages)
                ready = len(final_targets) > 0 and has_valid_msg
                if st.session_state.get('wa_done', False) and current_fp == st.session_state.get('wa_sent_fingerprint', ''):
                    st.button(lbl['sent_done'], disabled=True, use_container_width=True)
                else:
                    if st.button(lbl['send'].format(len(final_targets)), disabled=not ready, use_container_width=True, type="primary"):
                        st.session_state.wa_running = True
                        st.session_state.wa_idx = 0
                        st.session_state.wa_done = False
                        st.session_state.wa_sent_fingerprint = current_fp
                        # CRITICAL: Store a STABLE copy of targets to avoid "shrinking list" bug
                        st.session_state.wa_active_targets = list(final_targets)
                        
                        # Initialize message rotation state
                        st.session_state.wa_msg_index = 0
                        st.session_state.wa_msg_sent_count = 0
                        
                        st.rerun()

        if st.session_state.wa_running and st.session_state.get('wa_active_targets'):
            active_targets = st.session_state.wa_active_targets
            
            # Save attachment to temp file ONCE at the start of the batch
            if attachment and not st.session_state.get('wa_temp_path'):
                import tempfile
                suffix = os.path.splitext(attachment.name)[1]
                t_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                t_file.write(attachment.getvalue())
                t_file.close()
                st.session_state.wa_temp_path = t_file.name
            
            # Status Card
            st.markdown(f"""
            <div style="background: rgba(212, 175, 55, 0.05); padding: 15px; border-radius: 15px; border: 1px solid rgba(212, 175, 55, 0.2); margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="color: #00FF41; font-weight: 700; font-size: 1.1rem;">✅ {lbl['sent_count']}: {st.session_state.wa_idx}</span>
                    <span style="color: #D4AF37; font-weight: 700; font-size: 1.1rem;">⌛ {lbl['remaining_count']}: {len(active_targets) - st.session_state.wa_idx}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem; color: #888;">
                    <span>يتم الآن الإرسال من الرسالة رقم {st.session_state.wa_msg_index + 1}</span>
                    <span>تم إرسال {st.session_state.wa_msg_sent_count} رسالة → الانتقال للرسالة التالية بعد {msg_switch_threshold - st.session_state.wa_msg_sent_count}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.progress(st.session_state.wa_idx / len(active_targets))
            
            if st.session_state.wa_idx < len(active_targets):
                # --- ⏳ DELAY & COUNTDOWN (Before each message EXCEPT the first one) ---
                if st.session_state.wa_idx > 0:
                    def format_time(seconds):
                        m, s = divmod(seconds, 60)
                        if m > 0:
                            return f"{m} دقيقة و {s} ثانية" if is_ar else f"{m}m {s}s"
                        return f"{s} ثانية" if is_ar else f"{s}s"

                    is_batch_pause = batch_size > 0 and st.session_state.wa_idx % batch_size == 0
                    
                    # 2026 Advanced Anti-Pattern: Jittered Delay (Randomized intervals)
                    if is_batch_pause:
                        current_delay = int(random.uniform(batch_delay * 0.9, batch_delay * 1.3))
                        prefix = "🛡️ " + ("استراحة تمويهية عشوائية" if is_ar else "Randomized Anti-Ban Pause")
                    else:
                        # Allow variance from the base delay to look human
                        current_delay = int(random.uniform(delay * 0.85, delay * 1.5))
                        prefix = "🛡️ " + ("مهلة عشوائية" if is_ar else "Randomized Delay")
                        
                    delay_lbl = lbl['pausing'] if is_batch_pause else lbl['next_msg_in']
                    
                    wait_ph = st.empty()
                    for i in range(current_delay, 0, -1):
                        if not st.session_state.wa_running: break
                        # Displaying the current countdown + total randomized time to show it's working
                        status_text = f"{prefix}: {format_time(i)} / {format_time(current_delay)}"
                        if is_batch_pause:
                            wait_ph.warning(status_text)
                        else:
                            wait_ph.info(status_text)
                        time.sleep(1)
                    wait_ph.empty()

                if st.session_state.wa_running:
                    trg = active_targets[st.session_state.wa_idx]
                    p, n, v = trg['phone'], trg['name'], trg['cv']
                    
                    # --- Message Generation Logic ---
                    if st.session_state.get('wa_smart_mode'):
                        # Smart AI Mode: Generate unique message for each person
                        custom_job_val = st.session_state.get('wa_custom_job_val', '')
                        final_msg = generate_smart_message(n, v, custom_job=custom_job_val)
                    else:
                        # Standard Rotation Mode
                        current_msg_body = st.session_state.wa_messages[st.session_state.wa_msg_index]
                        final_msg = current_msg_body
                        
                        # PRE-CALCULATE placeholders for the entire batch to avoid repeated loops
                        cv_placeholders = ["{CV}", "{cv}", "{السيرة}"]
                        if st.session_state.get('wa_active_targets'):
                            first_trg = st.session_state.wa_active_targets[0]
                            for k in first_trg.keys():
                                if any(x in str(k).lower() for x in ["سيرة", "cv", "resume", "link"]):
                                    cv_placeholders.append("{" + str(k) + "}")
                        
                        # If CV is empty, remove lines containing CV placeholders
                        if not v or v.lower() == 'nan':
                            lines = final_msg.split('\n')
                            final_lines = []
                            for line in lines:
                                if not any(ph in line for ph in cv_placeholders):
                                    final_lines.append(line)
                            final_msg = '\n'.join(final_lines)
                        
                        for key, val in trg.items():
                            final_msg = final_msg.replace("{" + str(key) + "}", str(val))
                            final_msg = final_msg.replace("{" + str(key).lower() + "}", str(val))
                        
                        final_msg = final_msg.replace("{Name}", n).replace("{name}", n).replace("{الاسم}", n).replace("{CV}", v).replace("{cv}", v).replace("{السيرة}", v)
                    
                    import re
                    final_msg = re.sub(r'\n{3,}', '\n\n', final_msg).strip()
                    
                    st.info(lbl['sending'].format(n, p))
                    
                    # Call send_message with stored temp_path
                    temp_path = st.session_state.get('wa_temp_path')
                    ok, log = st.session_state.wa_service.send_message(p, final_msg, attachment_path=temp_path)
                    
                    st.session_state.wa_logs.append({
                        'name': n, 'phone': p,
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': log if ok else f"فشل ({log})", 'ok': ok
                    })

                    if ok:
                        st.session_state.wa_history.add(p)
                        save_wa_history(st.session_state.wa_history)
                        for t in st.session_state.wa_review_targets:
                            if t['phone'] == p: t['is_sent'] = True
                            
                        # Update message rotation counters ONLY on successful send
                        st.session_state.wa_msg_sent_count += 1
                        if st.session_state.wa_msg_sent_count >= msg_switch_threshold:
                            st.session_state.wa_msg_sent_count = 0
                            # Move to next message if available, otherwise stay on the last one
                            if st.session_state.wa_msg_index < len(st.session_state.wa_messages) - 1:
                                st.session_state.wa_msg_index += 1
                        
                        # Anti-ban: Secondary random micro-rest
                        time.sleep(random.uniform(1.0, 3.0))

                    st.session_state.wa_idx += 1
                    
                    if st.session_state.wa_idx == len(active_targets):
                        st.session_state.wa_running = False
                        st.session_state.wa_done = True
                        st.balloons()
                    
                    st.rerun()
            
            # Clean up temp file ONLY when done or stopped
            if not st.session_state.wa_running and st.session_state.get('wa_temp_path'):
                tp = st.session_state.get('wa_temp_path')
                if os.path.exists(tp):
                    try: os.remove(tp)
                    except: pass
                st.session_state.wa_temp_path = None

        # 📄 Professional 2026 Log Section
        if st.session_state.wa_logs:
            st.markdown("---")
            with st.expander(lbl['log_title'], expanded=True):
                log_h, log_del = st.columns([3, 1])
                with log_del:
                    if st.button(lbl['delete_log'], use_container_width=True, key="clear_log_btn"):
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
