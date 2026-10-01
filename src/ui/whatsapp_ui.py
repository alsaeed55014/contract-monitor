import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime
# WhatsAppService is imported lazily inside render_whatsapp_page() to avoid blocking app startup with selenium
from src.utils.phone_utils import validate_numbers, format_phone_number, save_to_local_desktop, render_pasha_export_button
from src.core.i18n import t as _translate
from src.config import WA_HISTORY_FILE, WA_TEMPLATES_FILE
from src.ui.styles import get_base64_image
import random

def _extract_only_digits(raw):
    """
    مُنظّف هجائِم فائق للنص: يستخرج الأرقام فقط من أي نص مهما كان محتواه.
    يعالج حالات مثل:
    - "554688559 📱 · عميل"  -> "554688559"
    - "050-123-4567 (جوال)"  -> "0501234567"
    - "WhatsApp: +966 50 123 4567"  -> "966501234567"
    """
    if not raw:
        return ""
    arabic_to_western = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    s = str(raw).translate(arabic_to_western)
    return "".join(filter(str.isdigit, s))


def standardize_saudi_phone(phone):
    """
    توحيد تنسيق رقم الهاتف السعودي لصيغة +966XXXXXXXXXX
    نسخة مطوّرة 2026 - تقاوم أشكال النص المختلط (أيقونات، نصوص، رموز، فراغات)
    
    يدعم الأشكال المختلفة:
    - 05XXXXXXXX (10 أرقام تبدأ بـ 05)
    - 5XXXXXXXX (9 أرقام تبدأ بـ 5)
    - 966XXXXXXXXXX (12 رقم تبدأ بـ 966)
    - +966XXXXXXXXXX (مع +)
    - "554688559 📱 · عميل"  ->  يتم استخلاص الأرقام تلقائياً
    """
    if not phone:
        return None
    
    # تنظيف خارق: استخراج الأرقام فقط مهما كان النص المحيط
    digits = _extract_only_digits(phone)
    
    if not digits or len(digits) < 8:
        return None
    
    # --- +966 مباشر (12 رقم تبدأ بـ 966)
    if digits.startswith("966") and len(digits) >= 12:
        return "+" + digits[:12]
    
    # --- 05XXXXXXXX (10 أرقام)
    if digits.startswith("05") and len(digits) == 10:
        return "+966" + digits[2:]
    
    # --- 5XXXXXXXX (9 أرقام يبدأ بـ 5)
    if digits.startswith("5") and len(digits) == 9:
        return "+966" + digits
    
    # --- 8 أرقام سعودي قديم يبدأ بـ 4,5,6,9
    if len(digits) == 8 and digits[0] in ['4','5','6','9']:
        return "+966" + digits
    
    # --- 11 رقماً تبدأ بـ 00966
    if digits.startswith("00966") and len(digits) >= 14:
        return "+" + digits[2:14]
    
    # --- 11 رقماً (بادئة + أو بدون) يبدأ بـ 0 -> نحذف صفر اليسار
    if len(digits) >= 10 and digits.startswith("0"):
        digits_no0 = digits.lstrip("0")
        if digits_no0.startswith("5") and len(digits_no0) == 9:
            return "+966" + digits_no0
        if digits_no0.startswith("966") and len(digits_no0) >= 12:
            return "+" + digits_no0[:12]
    
    # --- fallback: أرقام كثيرة نحاول إلحاقها بـ +966 لو مشتملة على 9 أرقام صالحة
    # استخراج آخر 9 أرقام إذا بدأت بـ 5
    if len(digits) >= 9:
        tail9 = digits[-9:]
        if tail9.startswith("5"):
            return "+966" + tail9
        tail12 = digits[-12:]
        if tail12.startswith("966"):
            return "+" + tail12
    
    return None

# قاموس ترجمة ثنائي اللغة للبحث
BILINGUAL_SEARCH_DICT = {
    # وظائف شائعة - Jobs/Professions
    "شيف": ["chef", "cook", "kitchen staff"],
    "chef": ["شيف", "طباخ", "مطبخ"],
    "حلويات": ["pastry", "baker", "confectionery", "sweet"],
    "pastry": ["حلويات", "حلوياتي", "باني"],
    "باني": ["baker", "pastry chef"],
    "مطعم": ["restaurant", "cafe", "dining"],
    "restaurant": ["مطعم", "مقهى", "كافي"],
    "كافي": ["cafe", "coffee shop", "coffee"],
    "مقهى": ["cafe", "coffee shop", "coffee"],
    "نادل": ["waiter", "server", "waitress"],
    "waiter": ["نادل", "خدم", "جارسون"],
    "سائق": ["driver", "chauffeur"],
    "driver": ["سائق", "قائد مركبة"],
    "عامل": ["worker", "employee", "staff"],
    "worker": ["عامل", "موظف", "مندوب"],
    "نظافة": ["cleaning", "cleaner", "housekeeping"],
    "cleaning": ["نظافة", "تنظيف", "عامل نظافة"],
    "بناء": ["construction", "builder"],
    "construction": ["بناء", "مقاولات", "عامل بناء"],
    "كهربائي": ["electrician", "electrical"],
    "electrician": ["كهربائي", "فني كهرباء"],
    "سباك": ["plumber", "plumbing"],
    "plumber": ["سباك", "سباكة"],
    "نجار": ["carpenter", "woodwork"],
    "carpenter": ["نجار", "نجارة"],
    "ميكانيكي": ["mechanic", "mechanical"],
    "mechanic": ["ميكانيكي", "فني ميكانيكا"],
    "حارس": ["guard", "security", "watchman"],
    "guard": ["حارس", "أمن", "حراسة"],
    "مدرس": ["teacher", "tutor", "instructor"],
    "teacher": ["مدرس", "معلم", "مربي"],
    
    # طبيعة العمل - Work Nature
    "تنظيف": ["cleaning", "cleaner", "housekeeping"],
    "خدم": ["service", "services", "customer service"],
    "خدمة عملاء": ["customer service", "client service"],
    "صيانة": ["maintenance", "repair", "fixing"],
    "maintenance": ["صيانة", "إصلاح", "ترميم"],
    "توريد": ["supply", "supplier", "logistics"],
    "supply": ["توريد", "موردين", "لوجستيك"],
    
    # مدن - Cities
    "الرياض": ["riyadh"],
    "riyadh": ["الرياض"],
    "جدة": ["jeddah"],
    "jeddah": ["جدة"],
    "مكة": ["makkah", "mecca"],
    "makkah": ["مكة"],
    "الدمام": ["dammam"],
    "dammam": ["الدمام"],
    "الخبر": ["khobar"],
    "khobar": ["الخبر"],
    "الطائف": ["taif"],
    "taif": ["الطائف"],
    "الزلفي": ["zulfy"],
    "zulfy": ["الزلفي"],
    "تبوك": ["tabuk"],
    "tabuk": ["تبوك"],
    "أبها": ["abha"],
    "abha": ["أبها"],
    
    # عام - General
    "شركة": ["company", "corporation", "firm"],
    "company": ["شركة", "مؤسسة"],
    "مؤسسة": ["foundation", "establishment", "institute"],
    "foundation": ["مؤسسة", "جمعية"],
}

def get_bilingual_search_terms(search_text):
    """
    الحصول على مصطلحات البحث الثنائية اللغة
    
    يحول النص العربي إلى مصطلحات إنجليزية والعكس
    """
    if not search_text:
        return []
    
    search_lower = search_text.lower().strip()
    terms = [search_lower]
    
    # إضافة المصطلحات المترجمة
    for key, translations in BILINGUAL_SEARCH_DICT.items():
        if key in search_lower:
            terms.extend(translations)
        elif any(t in search_lower for t in translations):
            terms.append(key)
    
    return list(set(terms))  # إزالة التكرار

# --- Smart Message Templates (Updated 2026-03-20) ---
SMART_PART_KEYS = ("header", "intro", "body_start", "body_end", "closing", "final_call", "signature")
SMART_TEMPLATES = {
    "header": [
        "Hello {Name},"
    ],
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
    ],
    "signature": [
        "Best regards,\nAbu Fahd\nHR Manager"
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
                smart = dict(SMART_TEMPLATES)
                smart.update(data.get("smart") or {})
                data["smart"] = smart
                return data
        except Exception:
            return default_templates
    return default_templates

def save_templates(templates):
    try:
        parent = os.path.dirname(WA_TEMPLATES_FILE)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(WA_TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        return True, None
    except Exception as e:
        return False, str(e)

def _split_smart_part_text(text):
    """Parse editor text into component options. A line with only --- separates multi-line options."""
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return []
    lines = text.split("\n")
    if any(line.strip() == "---" for line in lines):
        parts, buf = [], []
        for line in lines:
            if line.strip() == "---":
                chunk = "\n".join(buf).strip()
                if chunk:
                    parts.append(chunk)
                buf = []
            else:
                buf.append(line)
        chunk = "\n".join(buf).strip()
        if chunk:
            parts.append(chunk)
        return parts
    return [line.strip() for line in lines if line.strip()]


def _join_smart_part_list(part_list):
    return "\n---\n".join(str(item).strip() for item in (part_list or []) if str(item).strip())


def _pick_smart_part(templates, key, fallback, stable=False):
    options = templates.get(key) if templates else None
    if not options:
        options = fallback
    options = [o for o in options if str(o).strip()]
    if not options:
        options = fallback or [""]
    if stable:
        return options[0]
    return random.choice(options)


def _smart_editor_keys(file_smart=None):
    keys = list(SMART_PART_KEYS)
    if isinstance(file_smart, dict):
        for key in file_smart:
            if key not in keys:
                keys.append(key)
    return keys


def _read_smart_parts_from_widgets(file_smart=None):
    """Always prefer the editor widget text; never re-apply the file over typed changes."""
    file_smart = file_smart if isinstance(file_smart, dict) else (load_templates().get("smart") or dict(SMART_TEMPLATES))
    parts = {}
    for key in _smart_editor_keys(file_smart):
        raw = st.session_state.get(f"smart_comp_{key}")
        if isinstance(raw, str):
            parsed = _split_smart_part_text(raw)
            parts[key] = parsed if parsed else list(file_smart.get(key) or SMART_TEMPLATES.get(key) or [])
        else:
            parts[key] = list(file_smart.get(key) or SMART_TEMPLATES.get(key) or [])
    return parts


def get_live_smart_templates():
    live = st.session_state.get("smart_parts_live")
    if isinstance(live, dict) and live:
        return live
    return _read_smart_parts_from_widgets()


def _save_smart_parts_from_editor():
    data = load_templates()
    parts = _read_smart_parts_from_widgets(data.get("smart"))
    data["smart"] = parts
    ok, err = save_templates(data)
    st.session_state.smart_parts_live = parts
    st.session_state.smart_preview_nonce = st.session_state.get("smart_preview_nonce", 0) + 1
    st.session_state.smart_preview_randomize = False
    st.session_state.smart_save_status = {"ok": ok, "error": err, "parts": parts}


def generate_smart_message(name, cv_link, custom_job="", templates=None, stable=False):
    if templates is None:
        templates = load_templates().get("smart", SMART_TEMPLATES)

    header_opts = [o for o in (templates.get("header") or []) if str(o).strip()]
    if header_opts:
        header = _pick_smart_part(templates, "header", ["Hello {Name},"], stable=stable)
        header = (
            header.replace("{Name}", str(name))
            .replace("{name}", str(name))
            .replace("{الاسم}", str(name))
        )
    else:
        greetings = ["Hello", "Hi", "Greetings", "Dear"]
        greet = greetings[0] if stable else random.choice(greetings)
        header = f"{greet} {name},"

    intro = _pick_smart_part(templates, "intro", [""], stable=stable)
    b_start = _pick_smart_part(templates, "body_start", [""], stable=stable)
    b_end = _pick_smart_part(templates, "body_end", [""], stable=stable)
    closing = _pick_smart_part(templates, "closing", [""], stable=stable)
    final_call = _pick_smart_part(templates, "final_call", [""], stable=stable)
    signature = _pick_smart_part(
        templates,
        "signature",
        ["Best regards,\nAbu Fahd\nHR Manager"],
        stable=stable,
    )

    job_part = f" - {custom_job}" if custom_job and str(custom_job).strip() else ""
    full_body = f"{b_start}{job_part}{b_end}"
    lb = "\n\n" if stable else ("\n" if random.random() > 0.5 else "\n\n")

    msg = f"{header}{lb}{intro}{lb}{full_body}{lb}{closing}{lb}{final_call}{lb}"

    if cv_link and str(cv_link).lower() != "nan" and str(cv_link).strip() != "":
        msg += f"Link to your profile: {cv_link}\n\n"

    msg += signature

    if not stable and random.random() > 0.7:
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
    # ========== HACK ضربة جزم لمنع UnboundLocalError بسبب ظل المتغير 't' ==========
    # بدل ما نستخدم اسم 't' الملوث (اللي بيستخدمه اي حد فاكره كمتغير في اسفل الدالة)
    # نقوم باستيراد الدالة هنا داخل نفس الدالة باسم مختلف تماماً + نستخدمها فوراً
    # BEFORE: lbl['x'] = t(key, lang)  -> ERROR لأنه بايثون بيعتبر t متغير محلي من حلقات اسفل الدالة
    # AFTER : نستخدم اسم مش هيحصل فيه صدام نهائياً
    from src.core.i18n import t as _i18n_t_func
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
    # 🛡️ لا نُنشئ خدمة جديدة إذا كان هناك driver نشط — ذلك يُفقد الاتصال
    if 'wa_service' not in st.session_state or st.session_state.wa_service is None:
        st.session_state.wa_service = WhatsAppService()
    elif not getattr(st.session_state.wa_service, 'driver', None):
        # لا يوجد driver نشط — نتحقق من توافق الـ API فقط
        try:
            import inspect
            sig = inspect.signature(st.session_state.wa_service.send_message)
            if 'attachment_path' not in sig.parameters:
                st.session_state.wa_service = WhatsAppService()
        except Exception:
            st.session_state.wa_service = WhatsAppService()
    # إذا كان driver نشطاً → نُبقي الكائن كما هو بدون أي تعديل

    if 'wa_logs' not in st.session_state: st.session_state.wa_logs = []
    if 'wa_running' not in st.session_state: st.session_state.wa_running = False
    if 'wa_idx' not in st.session_state: st.session_state.wa_idx = 0
    if 'wa_data' not in st.session_state: st.session_state.wa_data = None
    if 'wa_history' not in st.session_state: st.session_state.wa_history = load_wa_history()
    if 'wa_review_targets' not in st.session_state: st.session_state.wa_review_targets = []
    if 'wa_messages' not in st.session_state: st.session_state.wa_messages = [""]
    if 'wa_emp_targets' not in st.session_state: st.session_state.wa_emp_targets = []
    if 'wa_emp_running' not in st.session_state: st.session_state.wa_emp_running = False
    if 'wa_emp_idx' not in st.session_state: st.session_state.wa_emp_idx = 0
    if 'wa_temp_attachments' not in st.session_state: st.session_state.wa_temp_attachments = []

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
        'wa_templates_title': _i18n_t_func('wa_templates_title', lang),
        'wa_save_as_template': _i18n_t_func('wa_save_as_template', lang),
        'wa_template_name': _i18n_t_func('wa_template_name', lang),
        'wa_manage_templates': _i18n_t_func('wa_manage_templates', lang),
        'wa_use_template': _i18n_t_func('wa_use_template', lang),
        'wa_delete_template': _i18n_t_func('wa_delete_template', lang),
        'wa_placeholders_guide': _i18n_t_func('wa_placeholders_guide', lang),
        'wa_scan_msg': _i18n_t_func('wa_scan_msg', lang),
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
        if (status_emp in ["Awaiting Login", "Loading..."]) and st.session_state.wa_service and st.session_state.wa_service.driver:
            scan_title = lbl.get('wa_scan_msg', "امسح الكود باستخدام الواتساب في جوالك" if is_ar else "Scan with WhatsApp on your phone")
            st.markdown(f'<div style="text-align:center; padding:10px 0;"><h4 style="color:#00FF88;">📱 {scan_title}</h4></div>', unsafe_allow_html=True)
            qr_b64 = st.session_state.wa_service.get_qr_hd()
            if qr_b64:
                src = qr_b64 if qr_b64.startswith("data:") else f"data:image/png;base64,{qr_b64}"
                st.markdown(
                    f'<div style="background:#FFFFFF;padding:25px;border-radius:20px;max-width:420px;'
                    f'margin:15px auto;text-align:center;box-shadow:0 0 40px rgba(0,255,136,0.3);border:2px solid #00FF88;">'
                    f'<img src="{src}" style="width:350px;height:350px;image-rendering:pixelated;image-rendering:crisp-edges;" />'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.warning("⏳ " + ("جاري تحضير رمز الباركود من واتساب..." if is_ar else "Preparing QR code from WhatsApp..."))
                diag_b64 = st.session_state.wa_service.get_diagnostic_screenshot()
                if diag_b64:
                    d_src = diag_b64 if diag_b64.startswith("data:") else f"data:image/png;base64,{diag_b64}"
                    with st.expander("📸 " + ("لقطة شاشة تشخيصية من المتصفح" if is_ar else "Diagnostic Browser Screenshot"), expanded=True):
                        st.image(d_src, caption="Browser Screen State", use_container_width=True)

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
        if status_emp != "Connected" and not st.session_state.get('wa_emp_running', False):
            st.info("💡 " + ("قم بتشغيل المحرك ومسح الباركود أولاً للبدء بالإرسال." if is_ar else "Start the engine and scan the QR code first to begin sending."))
            st.markdown("---")
            return

        st.markdown("---")
        # ──────────────────────────────────────────────────────────────
        # 🛡️ شريط الأمان وإحصائيات اليوم وزر فك القفل
        # ──────────────────────────────────────────────────────────────
        sec_c1, sec_c2 = st.columns([3, 1])
        with sec_c1:
            stats = st.session_state.wa_service.get_daily_stats() if st.session_state.wa_service else {}
            ok_cnt = stats.get('sent_ok', 0)
            fail_cnt = stats.get('sent_fail', 0)
            inval_cnt = stats.get('invalid_numbers', 0)
            st.markdown(
                f'<div style="background: rgba(0,255,136,0.06); padding: 10px 15px; border-radius: 10px; border: 1px solid rgba(0,255,136,0.2); font-size: 0.9rem;">'
                f'🛡️ <b>{"درع الحماية من الحظر" if is_ar else "Anti-Ban Shield"}:</b> '
                f'{"تم إرسال اليوم" if is_ar else "Today Sent"}: <span style="color:#00FF88; font-weight:bold;">{ok_cnt}</span> | '
                f'{"محاولات فاشلة" if is_ar else "Failed"}: <span style="color:#FF6B6B; font-weight:bold;">{fail_cnt}</span> | '
                f'{"أرقام غير صالحة" if is_ar else "Invalid"}: <span style="color:#FFA500; font-weight:bold;">{inval_cnt}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        with sec_c2:
            if st.button("🔄 " + ("تصفير العداد / فك القفل" if is_ar else "Reset Counter"), key="emp_unblock_btn", help="تصفير عداد الأخطاء وفك أي قفل أمان مؤقت"):
                if st.session_state.wa_service:
                    st.session_state.wa_service.reset_daily_stats()
                    st.toast("✅ " + ("تم فك قفل الأمان وتصفير العداد بنجاح" if is_ar else "Anti-ban counters reset successfully!"))
                    st.rerun()

        st.markdown("---")

        # ──────────────────────────────────────────────────────────────
        # 1. اختيار مصدر البيانات وإدارتها (محفوظة في st.session_state)
        # ──────────────────────────────────────────────────────────────
        st.markdown(f"#### {'مصدر أرقام العملاء' if is_ar else 'Customer Data Source'}")
        data_source = st.radio(
            "اختر مصدر البيانات" if is_ar else "Select Data Source",
            ["استيراد ملف Excel" if is_ar else "Import Excel File",
             "من النظام (طلبات العملاء & Bengali Supply)" if is_ar else "From System (Requests & Bengali Supply)",
             "إدخال أرقام يدوياً" if is_ar else "Enter Numbers Manually"],
            horizontal=True,
            key="wa_emp_data_source"
        )

        if data_source == ("استيراد ملف Excel" if is_ar else "Import Excel File"):
            uploaded_file = st.file_uploader(
                "ارفع ملف Excel" if is_ar else "Upload Excel file",
                type=['xlsx', 'xls'],
                key="wa_emp_excel_uploader"
            )
            if uploaded_file:
                try:
                    df = pd.read_excel(uploaded_file)
                    st.success(f"✅ {'تم قراءة الملف بنجاح' if is_ar else 'File loaded successfully'}: {len(df)} {'صف' if is_ar else 'rows'}")
                    
                    ec_c1, ec_c2 = st.columns(2)
                    with ec_c1:
                        name_col = st.selectbox("عمود الاسم" if is_ar else "Name column", df.columns.tolist(), key="wa_emp_name_col")
                    with ec_c2:
                        phone_col = st.selectbox("عمود رقم الجوال" if is_ar else "Phone column", df.columns.tolist(), key="wa_emp_phone_col")

                    if st.button("📥 " + ("استخراج وحفظ قائمة العملاء" if is_ar else "Extract & Load Customers"), type="primary", key="btn_extract_emp_excel"):
                        extracted = []
                        seen_phones = set()
                        for _, row in df.iterrows():
                            c_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else "عميل"
                            raw_p = str(row[phone_col]).strip() if pd.notna(row[phone_col]) else ""
                            # تنظيف خارق ضد أيقونات ونصوص إضافية في الخلية
                            c_phone = _extract_only_digits(raw_p)
                            if c_phone and len(c_phone) >= 8 and c_phone not in seen_phones:
                                seen_phones.add(c_phone)
                                formatted_p = standardize_saudi_phone(c_phone)
                                extracted.append({
                                    'name': c_name if c_name != 'nan' else 'عميل',
                                    'phone': formatted_p if formatted_p else c_phone,
                                    'is_sent': False
                                })
                        st.session_state.wa_emp_targets = extracted
                        st.toast(f"✅ تم استخراج {len(extracted)} عميل بنجاح")
                        st.rerun()
                except Exception as ex:
                    st.error(f"❌ {'خطأ في قراءة ملف الإكسل' if is_ar else 'Error reading Excel file'}: {str(ex)}")

        elif data_source == ("من النظام (طلبات العملاء & Bengali Supply)" if is_ar else "From System (Requests & Bengali Supply)"):
            from src.data.bengali_manager import BengaliDataManager

            # ── جلب البيانات من المصدرين ──────────────────────────────
            all_sys_records = []  # list of dicts: {name, phone, city, job, nature, source}

            # 1) طلبات العملاء (Google Sheet)
            try:
                if hasattr(st.session_state, 'db') and st.session_state.db:
                    cust_df = st.session_state.db.fetch_customer_requests()
                    if cust_df is not None and not cust_df.empty:
                        cols = cust_df.columns.tolist()
                        # محاولة تحديد أعمدة الاسم، الجوال، المدينة، الوظيفة
                        def _find_col(keywords):
                            for kw in keywords:
                                for c in cols:
                                    if kw.lower() in str(c).lower():
                                        return c
                            return None
                        name_c   = _find_col(["اسم", "name", "شركة", "company", "عميل"])
                        phone_c  = _find_col(["جوال", "موبايل", "تليفون", "هاتف", "phone", "mobile"])
                        city_c   = _find_col(["مدينة", "city", "منطقة", "location"])
                        job_c    = _find_col(["وظيفة", "مهنة", "طلب", "job", "category", "profession"])
                        nature_c = _find_col(["طبيعة", "نوع العمل", "نشاط", "nature", "work type", "activity", "type"])
                        for _, row in cust_df.iterrows():
                            r_name   = str(row[name_c]).strip()   if name_c   and pd.notna(row[name_c])   else "عميل"
                            r_phone  = str(row[phone_c]).strip()  if phone_c  and pd.notna(row[phone_c])  else ""
                            r_city   = str(row[city_c]).strip()   if city_c   and pd.notna(row[city_c])   else ""
                            r_job    = str(row[job_c]).strip()    if job_c    and pd.notna(row[job_c])    else ""
                            r_nature = str(row[nature_c]).strip() if nature_c and pd.notna(row[nature_c]) else ""
                            # تنظيف خارق يحذف أيقونات، نصوص، رموز مثل "عميل" و 📱 و ·
                            r_phone_clean = _extract_only_digits(r_phone)
                            # توحيد رقم الهاتف السعودي
                            r_phone_formatted = standardize_saudi_phone(r_phone_clean)
                            if r_phone_formatted:
                                all_sys_records.append({
                                    'name':   r_name if r_name not in ('', 'nan') else 'عميل',
                                    'phone':  r_phone_formatted,
                                    'phone_raw_display': _extract_only_digits(r_phone),
                                    'city':   r_city,
                                    'job':    r_job,
                                    'nature': r_nature,
                                    'source': '📋 طلبات العملاء'
                                })
            except Exception as _ce:
                st.warning(f"⚠️ تعذّر جلب طلبات العملاء: {_ce}")

            # 2) Bengali Supply
            try:
                bm = BengaliDataManager()
                for e in (bm.get_employers() or []):
                    # تنظيف خارق ضد أيقونات ونصوص إضافية
                    raw_p = _extract_only_digits(str(e.get('mobile', '')))
                    # توحيد رقم الهاتف السعودي
                    formatted_p = standardize_saudi_phone(raw_p)
                    if formatted_p:
                        all_sys_records.append({
                            'name':   str(e.get('name', 'عميل')).strip(),
                            'phone':  formatted_p,
                            'phone_raw_display': raw_p,
                            'city':   str(e.get('city', '')).strip(),
                            'job':    str(e.get('cafe', '')).strip(),
                            'nature': '',
                            'source': '🏢 Bengali Supply'
                        })
            except Exception as _be:
                st.warning(f"⚠️ تعذّر جلب Bengali Supply: {_be}")

            if not all_sys_records:
                st.warning("⚠️ لا توجد بيانات في النظام حالياً")
            else:
                # ── إحصائيات سريعة ────────────────────────────────────
                _src_cust = sum(1 for r in all_sys_records if 'طلبات' in r['source'])
                _src_beng = len(all_sys_records) - _src_cust
                st.markdown(
                    f"<div style='display:flex;gap:14px;margin-bottom:8px'>"
                    f"<span style='background:rgba(0,229,255,0.1);border:1px solid rgba(0,229,255,0.3);"
                    f"border-radius:8px;padding:4px 12px;font-size:.85rem'>📊 الإجمالي: <b>{len(all_sys_records)}</b></span>"
                    f"<span style='background:rgba(0,229,255,0.1);border:1px solid rgba(0,229,255,0.3);"
                    f"border-radius:8px;padding:4px 12px;font-size:.85rem'>📋 طلبات: <b>{_src_cust}</b></span>"
                    f"<span style='background:rgba(0,229,255,0.1);border:1px solid rgba(0,229,255,0.3);"
                    f"border-radius:8px;padding:4px 12px;font-size:.85rem'>🏢 Bengali: <b>{_src_beng}</b></span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                # ── خانة البحث الشاملة (تشمل طبيعة العمل) ────────────
                search_q = st.text_input(
                    "🔍 ابحث بالاسم · رقم التليفون · المدينة · المهنة · طبيعة العمل · المصدر",
                    key="wa_sys_search_box",
                    placeholder="مثال:  محمد  أو  0501234567  أو  الرياض  أو  مطعم  أو  تنظيف"
                )

                # ── تصفية النتائج (تشمل طبيعة العمل) ─────────────────
                if search_q and search_q.strip():
                    q_low = search_q.strip().lower()
                    # إزالة الأرقام من البحث للبحث بالأرقام أيضاً
                    q_digits = "".join(filter(str.isdigit, search_q))
                    
                    # الحصول على مصطلحات البحث الثنائية اللغة
                    search_terms = get_bilingual_search_terms(search_q)
                    
                    filtered = []
                    for r in all_sys_records:
                        match_found = False
                        
                        # البحث بجميع المصطلحات المتاحة
                        for term in search_terms:
                            # البحث في الاسم
                            if term in r['name'].lower():
                                match_found = True
                                break
                            # البحث في المدينة
                            elif term in r['city'].lower():
                                match_found = True
                                break
                            # البحث في الوظيفة
                            elif term in r['job'].lower():
                                match_found = True
                                break
                            # البحث في طبيعة العمل
                            elif term in r.get('nature', '').lower():
                                match_found = True
                                break
                            # البحث في المصدر
                            elif term in r['source'].lower():
                                match_found = True
                                break
                        
                        # البحث برقم الهاتف (مع دعم الأشكال المختلفة)
                        if not match_found and q_digits and q_digits in r['phone'].replace('+', '').replace('966', ''):
                            match_found = True
                        
                        if match_found:
                            filtered.append(r)
                else:
                    filtered = all_sys_records

                # ── شريط النتائج + أزرار اعتماد جماعي ────────────────
                rc1, rc2, rc3 = st.columns([2, 1, 1])
                with rc1:
                    st.markdown(f"**🔎 نتائج البحث:** {len(filtered)} سجل")
                with rc2:
                    if filtered and st.button(
                        f"⚡ إضافة كل النتائج ({len(filtered)}) للإرسال",
                        key="btn_add_all_filtered",
                        use_container_width=True,
                        type="primary"
                    ):
                        existing_ph = {t['phone'] for t in st.session_state.get('wa_emp_targets', [])}
                        new_list = list(st.session_state.get('wa_emp_targets', []))
                        added_n = 0
                        for r in filtered:
                            # Phone is already standardized in the search results
                            formatted_phone = r['phone']
                            
                            if formatted_phone not in existing_ph:
                                existing_ph.add(formatted_phone)
                                
                                # Use provided name or default
                                final_name = r['name'] if r['name'] and r['name'] not in ('', 'nan', 'عميل') else ("السادة / عملائنا الكرام المحترمين" if is_ar else "Dear Valued Customers")
                                
                                new_list.append({
                                    'name': final_name,
                                    'phone': formatted_phone,
                                    'city': r['city'] or ("غير محدد" if is_ar else "Not specified"),
                                    'job': r.get('job', ''),
                                    'nature': r.get('nature', ''),
                                    'source': r['source'],
                                    'is_sent': False
                                })
                                added_n += 1
                        st.session_state.wa_emp_targets = new_list
                        st.toast(f"✅ تمت إضافة {added_n} عميل لقائمة الإرسال")
                        st.rerun()
                with rc3:
                    if st.session_state.get('wa_emp_targets'):
                        if st.button("🗑️ مسح قائمة الإرسال", key="btn_clr_targets_from_search", use_container_width=True):
                            st.session_state.wa_emp_targets = []
                            st.toast("🗑️ تم مسح قائمة الإرسال")
                            st.rerun()

                if not filtered:
                    st.info("لا توجد نتائج مطابقة، جرّب كلمة بحث مختلفة.")
                else:
                    # ── بطاقة لكل سجل مع رقم بارز وزر إضافة/حذف فردي ─
                    existing_ph_set = {t['phone'] for t in st.session_state.get('wa_emp_targets', [])}
                    
                    # تصفية النتائج لإظهار فقط غير المحذوفين
                    filtered_display = [r for r in filtered if r['phone'] not in existing_ph_set]
                    
                    if not filtered_display:
                        st.info("جميع النتائج تمت إضافتها بالفعل أو تم حذفها من القائمة.")
                    else:
                        for idx_r, r in enumerate(filtered_display):
                            already_added = r['phone'] in existing_ph_set
                            card_border   = "rgba(0,255,136,0.45)" if already_added else "rgba(0,229,255,0.25)"
                            card_bg       = "rgba(0,255,136,0.04)" if already_added else "rgba(0,229,255,0.03)"
                            badge_color   = "#00FF88" if already_added else "#00E5FF"

                            extra_parts = []
                            if r.get('city'):   extra_parts.append(f"📍 {r['city']}")
                            if r.get('job'):    extra_parts.append(f"💼 {r['job']}")
                            if r.get('nature'): extra_parts.append(f"🏗️ {r['nature']}")
                            extra_parts.append(r['source'])
                            extra_html = "  ·  ".join(extra_parts)

                            col_card, col_btn = st.columns([5, 1])
                            with col_card:
                                st.markdown(
                                    f"<div style='background:{card_bg};border:1.5px solid {card_border};"
                                    f"border-radius:10px;padding:10px 16px;margin-bottom:6px'>"
                                    f"<span style='font-weight:700;font-size:.95rem;color:#FFFFFF'>{r['name']}</span>"
                                    f"&nbsp;&nbsp;"
                                    f"<span style='font-family:monospace;font-size:1.05rem;font-weight:800;"
                                    f"color:{badge_color};background:rgba(0,0,0,0.3);padding:2px 10px;"
                                    f"border-radius:6px'>📱 {r['phone']}</span>"
                                    f"<div style='font-size:.78rem;color:#AAA;margin-top:4px'>{extra_html}</div>"
                                    f"</div>",
                                    unsafe_allow_html=True
                            )
                            with col_btn:
                                # زر الإضافة لقائمة الإرسال فقط (حذف إمكانية الحذف من هنا)
                                if st.button("➕", key=f"sys_add_{idx_r}_{r['phone']}",
                                             help="إضافة لقائمة الإرسال", use_container_width=True):
                                    # Phone is already standardized in the search results
                                    formatted_phone = r['phone']
                                    
                                    # Use provided name or default
                                    final_name = r['name'] if r['name'] and r['name'] not in ('', 'nan', 'عميل') else ("السادة / عملائنا الكرام المحترمين" if is_ar else "Dear Valued Customers")
                                    
                                    # Include city in the data
                                    new_target = {
                                        'name': final_name,
                                        'phone': formatted_phone,
                                        'city': r['city'] or ("غير محدد" if is_ar else "Not specified"),
                                        'job': r.get('job', ''),
                                        'nature': r.get('nature', ''),
                                        'source': r['source'],
                                        'is_sent': False
                                    }
                                    
                                    st.session_state.wa_emp_targets = (
                                        st.session_state.get('wa_emp_targets', []) +
                                        [new_target]
                                    )
                                    st.toast(f"✅ تمت إضافة {final_name} — 📱 {formatted_phone} — 🏙️ {r['city']}")
                                    st.rerun()
                        with col_btn:
                            # تنظيف المفتاح بإزالة الرموز الخاصة من رقم الهاتف
                            clean_phone_key = r['phone'].replace('+', '').replace('-', '').replace(' ', '')
                            
                            if already_added:
                                # زر الحذف من قائمة الإرسال
                                if st.button("❌", key=f"sys_rm_{idx_r}_{clean_phone_key}",
                                             help="حذف من قائمة الإرسال", use_container_width=True):
                                    st.session_state.wa_emp_targets = [
                                        t for t in st.session_state.get('wa_emp_targets', [])
                                        if t['phone'] != r['phone']
                                    ]
                                    st.toast(f"🗑️ تم حذف {r['name']} من القائمة")
                                    st.rerun()
                            else:
                                # زر الإضافة لقائمة الإرسال
                                if st.button("➕", key=f"sys_add_{idx_r}_{clean_phone_key}",
                                             help="إضافة لقائمة الإرسال", use_container_width=True):
                                    # Phone is already standardized in the search results
                                    formatted_phone = r['phone']
                                    
                                    # Use provided name or default
                                    final_name = r['name'] if r['name'] and r['name'] not in ('', 'nan', 'عميل') else ("السادة / عملائنا الكرام المحترمين" if is_ar else "Dear Valued Customers")
                                    
                                    # Include city in the data
                                    new_target = {
                                        'name': final_name,
                                        'phone': formatted_phone,
                                        'city': r['city'] or ("غير محدد" if is_ar else "Not specified"),
                                        'job': r.get('job', ''),
                                        'nature': r.get('nature', ''),
                                        'source': r['source'],
                                        'is_sent': False
                                    }
                                    
                                    st.session_state.wa_emp_targets = (
                                        st.session_state.get('wa_emp_targets', []) +
                                        [new_target]
                                    )
                                    st.toast(f"✅ تمت إضافة {final_name} — 📱 {formatted_phone} — 🏙️ {r['city']}")
                                    st.rerun()

                    # ── ملخص قائمة الإرسال الحالية ────────────────────
                    curr_targets = st.session_state.get('wa_emp_targets', [])
                    if curr_targets:
                        st.markdown("---")
                        pending_cnt = sum(1 for t in curr_targets if not t.get('is_sent', False))
                        st.markdown(
                            f"<div style='background:rgba(0,255,136,0.07);border:1.5px solid rgba(0,255,136,0.35);"
                            f"border-radius:10px;padding:10px 16px;text-align:center'>"
                            f"<span style='color:#00FF88;font-weight:700;font-size:1rem'>"
                            f"✅ قائمة الإرسال جاهزة — {len(curr_targets)} عميل"
                            f" ({pending_cnt} بانتظار الإرسال)"
                            f"</span><br>"
                            f"<span style='color:#AAA;font-size:.82rem'>تابع لأسفل لكتابة الرسالة وبدء الإرسال ⬇️</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

        else: # Manual input
            raw_txt = st.text_area(lbl['paste_numbers'], placeholder="05XXXXXXXX\n05YYYYYYYY...", height=120, key="wa_emp_manual_raw")
            if st.button("📥 " + ("اعتماد الأرقام" if is_ar else "Load Numbers"), key="btn_load_manual_emp"):
                m_list, _, _ = validate_numbers(raw_txt)
                extracted = [{'name': 'عميل', 'phone': p, 'is_sent': False} for p in m_list]
                st.session_state.wa_emp_targets = extracted
                st.toast(f"✅ تم تحميل {len(extracted)} رقم")
                st.rerun()

        # ──────────────────────────────────────────────────────────────
        # 2. عرض القائمة وإعداد الرسالة والإرسال
        # ──────────────────────────────────────────────────────────────
        targets = st.session_state.get('wa_emp_targets', [])
        if targets:
            st.markdown("---")
            t_hdr_col1, t_hdr_col2 = st.columns([3, 1])
            with t_hdr_col1:
                pending_count = sum(1 for t in targets if not t.get('is_sent', False))
                sent_count = len(targets) - pending_count
                st.markdown(f"#### 📋 {'قائمة العملاء المستهدفين' if is_ar else 'Target Customers'} ({len(targets)} إجمالي | {pending_count} بانتظار الإرسال | {sent_count} تم الإرسال)")
            with t_hdr_col2:
                if st.button("🗑️ " + ("مسح القائمة بالكامل" if is_ar else "Clear List"), key="emp_clear_targets_btn"):
                    st.session_state.wa_emp_targets = []
                    st.session_state.wa_emp_running = False
                    st.session_state.wa_emp_idx = 0
                    st.session_state.wa_emp_saved_attachments = []
                    st.rerun()

            with st.expander("👁️ " + ("عرض وتعديل قائمة العملاء المستخرجين" if is_ar else "View & Edit Target List"), expanded=False):
                for idx_t, trg in enumerate(targets):
                    col_t1, col_t2, col_t3 = st.columns([3, 2, 1])
                    with col_t1:
                        status_mark = "✅ تم الإرسال" if trg.get('is_sent') else "⏳ بانتظار الإرسال"
                        st.write(f"**{trg['name']}** ({status_mark})")
                    with col_t2:
                        st.code(trg['phone'], language=None)
                    with col_t3:
                        # تنظيف المفتاح لإزالة الرموز الخاصة
                        clean_phone_key = trg['phone'].replace('+', '').replace('-', '').replace(' ', '')
                        if st.button("❌", key=f"del_emp_trg_{idx_t}_{clean_phone_key}", help="حذف من القائمة"):
                            # استخدام الهاتف للتعريف الفريد بدلاً من الفهرس
                            target_phone = trg['phone']
                            st.session_state.wa_emp_targets = [
                                t for t in st.session_state.wa_emp_targets 
                                if t['phone'] != target_phone
                            ]
                            st.toast(f"🗑️ تم حذف {trg['name']} من القائمة")
                            st.rerun()

            # 📝 Message Composition
            st.markdown("---")
            st.markdown(f"#### 📝 {'نص الرسالة' if is_ar else 'Message Content'}")
            st.caption("💡 يمكنك استخدام `{Name}` أو `{الاسم}` لإدراج اسم العميل تلقائياً، والـ Spintax مثل `{مرحباً|أهلاً|السلام عليكم}` لتنويع الرسائل وتجنب الحظر.")
            
            default_emp_msg = "مرحباً {Name}،\n\nنأمل أن تكونوا بخير.\nيسعدنا خدمتكم في توفير أفضل الكوادر المهنية والعمالة المناسبة لمتطلباتكم بأسرع وقت.\n\nللتواصل والاستفسار يرجى الرد على هذه الرسالة.\n\nمع خالص التحية والتقدير،\nأبو فهد\nHR"
            emp_message = st.text_area(
                "الرسالة" if is_ar else "Message",
                value=st.session_state.get('wa_emp_last_msg', default_emp_msg),
                height=160,
                key="wa_emp_msg_input"
            )
            st.session_state.wa_emp_last_msg = emp_message

            # 📎 مرفقات الرسالة للعملاء (صور / فيديوهات / مستندات PDF وملفات أخرى)
            st.markdown("---")
            st.markdown(f"#### 📎 {'مرفقات الرسالة للعملاء (صور 🖼️ + فيديوهات 🎥 + مستندات 📄 PDF وملفات أخرى)' if is_ar else 'Customer Attachments (Images 🖼️ + Videos 🎥 + PDFs 📄 & more)'}")
            st.caption("💡 " + ("يمكنك رفع ملفات متعددة في نفس الوقت: صور (JPG/PNG/GIF/WEBP)، مقاطع فيديو (MP4/MOV/AVI/MKV/3GP)، مستندات (PDF/DOCX/XLSX/PPTX)، ملفات صوتية، وملفات مضغوطة." if is_ar else "You can upload multiple files: Images (JPG/PNG/GIF/WEBP), Videos (MP4/MOV/AVI/MKV/3GP), Docs (PDF/DOCX/XLSX/PPTX), Audio files, and Archives."))

            emp_uploaded_files = st.file_uploader(
                "📎 " + ("اختر أو اسحب الملفات (صور، فيديو، PDF، ومستندات أخرى)" if is_ar else "Upload files (Images, Videos, PDFs, & Docs)"),
                type=["png", "jpg", "jpeg", "gif", "bmp", "webp",
                      "mp4", "mov", "avi", "mkv", "3gp",
                      "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
                      "mp3", "wav", "ogg",
                      "zip", "rar", "7z", "txt", "csv"],
                accept_multiple_files=True,
                key="wa_emp_files_uploader"
            )

            # معالجة وحفظ المرفقات في مجلد مؤقت للجلسة
            emp_saved_attachments = []
            if emp_uploaded_files and len(emp_uploaded_files) > 0:
                base_dir = os.path.join(os.getcwd(), "whatsapp_session")
                if not os.path.exists(base_dir):
                    base_dir_alt = os.path.join(os.getcwd(), ".whatsapp_session")
                    if os.path.exists(base_dir_alt):
                        base_dir = base_dir_alt
                emp_uploads_dir = os.path.join(base_dir, "emp_temp_uploads")
                os.makedirs(emp_uploads_dir, exist_ok=True)

                total_size_bytes = 0
                st.markdown("<div style='margin: 8px 0; display: flex; flex-wrap: wrap; gap: 8px;'>", unsafe_allow_html=True)
                for f in emp_uploaded_files:
                    total_size_bytes += f.size
                    file_ext = os.path.splitext(f.name)[1].lower()
                    if file_ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp']:
                        icon = "🖼️ [صورة]"
                    elif file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.3gp']:
                        icon = "🎥 [فيديو]"
                    elif file_ext == '.pdf':
                        icon = "📄 [PDF]"
                    elif file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv']:
                        icon = "📝 [مستند]"
                    elif file_ext in ['.mp3', '.wav', '.ogg']:
                        icon = "🎵 [صوت]"
                    elif file_ext in ['.zip', '.rar', '.7z']:
                        icon = "🗜️ [مضغوط]"
                    else:
                        icon = "📎 [ملف]"

                    sz_str = f"{f.size / (1024*1024):.2f} MB" if f.size >= 1024*1024 else f"{f.size / 1024:.1f} KB"
                    st.markdown(
                        f"<div style='background: rgba(0, 229, 255, 0.08); border: 1px solid rgba(0, 229, 255, 0.3); border-radius: 10px; padding: 7px 14px; display: inline-block;'>"
                        f"<b>{icon}</b> {f.name} <span style='color: #00E5FF;'>({sz_str})</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    # حفظ الملف محلياً
                    save_path = os.path.join(emp_uploads_dir, f.name)
                    try:
                        with open(save_path, "wb") as out_f:
                            out_f.write(f.getbuffer())
                        emp_saved_attachments.append(save_path)
                    except Exception as err:
                        st.error(f"❌ خطأ في حفظ المرفق {f.name}: {err}")
                st.markdown("</div>", unsafe_allow_html=True)
                st.session_state.wa_emp_saved_attachments = emp_saved_attachments
            else:
                st.session_state.wa_emp_saved_attachments = []

            has_attachments = bool(st.session_state.get('wa_emp_saved_attachments', []))

            # 🛡️ إشعار وتنبيه الأمان لمكافحة الحظر عند وجود مرفقات
            if has_attachments:
                st.markdown(f"""
                <div style="background: rgba(255, 170, 0, 0.08); border: 1.5px solid rgba(255, 170, 0, 0.4); border-radius: 12px; padding: 12px 18px; margin: 12px 0;">
                    <div style="color: #FFA500; font-weight: 700; font-size: 0.95rem; margin-bottom: 4px;">
                        🛡️ {'تم تفعيل درع الأمان التلقائي لمرفقات الوسائط (صور / فيديوهات / PDF)' if is_ar else 'Media Anti-Ban Shield Activated'}
                    </div>
                    <div style="color: #E0E0E0; font-size: 0.85rem; line-height: 1.5;">
                        {'⚠️ <b>تنبيه لحماية الحساب من الحظر:</b> إرسال الوسائط والمستندات يتطلب وقتاً أطول لرفع البيانات ومعالجتها على خوادم واتساب ويخضع لرقابة صارمة من خوارزميات مكافحة السبام.<br>✅ <b>تم تفعيل فترات التهدئة الآمنة:</b> تم ضبط أدنى وقت انتظار بين <b>45 إلى 90 ثانية</b> مع استراحة دورية كل عدة رسائل لحماية رقمك تماماً من الحظر.' if is_ar else '⚠️ <b>Anti-ban notice:</b> Sending media & documents requires longer upload times and strict anti-spam pacing.<br>✅ Safe auto-delays and periodic batch breaks have been enabled to protect your account.'}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 🛡️ Anti-ban Settings
            st.markdown(f"#### ⚙️ {'إعدادات الأمان والتأخير ومكافحة الحظر' if is_ar else 'Safety, Delay & Anti-Ban Settings'}")
            c_d1, c_d2, c_d3, c_d4 = st.columns(4)
            with c_d1:
                # إعدادات التأخير والاستراحة للعملاء (طلبات العملاء & Bengali Supply)
                def_min = 60
                min_allowed = 20
                emp_min_delay = st.number_input(
                    "أدنى تأخير (ثانية)" if is_ar else "Min delay (s)",
                    min_value=min_allowed, max_value=300, value=def_min,
                    help="الحد الأدنى الآمن للانتظار بين كل رسالة (أعلى عند إرسال المرفقات لحماية الرقم)",
                    key="emp_min_delay_val"
                )
            with c_d2:
                def_max = 120
                min_max_allowed = max(emp_min_delay + 5, 25)
                emp_max_delay = st.number_input(
                    "أقصى تأخير (ثانية)" if is_ar else "Max delay (s)",
                    min_value=min_max_allowed, max_value=600, value=max(def_max, min_max_allowed),
                    help="الحد الأقصى للتأخير العشوائي بين الرسائل (لمحاكاة السلوك البشري الطبيعي)",
                    key="emp_max_delay_val"
                )
            with c_d3:
                def_break = 6
                emp_batch_break = st.number_input(
                    "استراحة كل (رسائل)" if is_ar else "Pause every (msgs)",
                    min_value=3, max_value=50, value=def_break,
                    help="التوقف لأخذ استراحة أمان لمحاكاة السلوك البشري الطبيعي",
                    key="emp_batch_break_val"
                )
            with c_d4:
                def_pause_mins = 5
                emp_batch_pause_mins = st.number_input(
                    "مدة الاستراحة (دقائق)" if is_ar else "Break time (mins)",
                    min_value=2, max_value=20, value=def_pause_mins,
                    help="مدة الاستراحة الدورية بين الدفعات بالدقائق",
                    key="emp_batch_pause_mins_val"
                )

            # 🚀 Send / Stop Controls
            st.markdown("---")
            is_sending = st.session_state.get('wa_emp_running', False)
            btn_box1, btn_box2 = st.columns([1, 2])

            with btn_box1:
                if is_sending:
                    if st.button("🛑 " + ("إيقاف الإرسال" if is_ar else "Stop Sending"), type="primary", width='stretch', key="btn_stop_emp_send"):
                        st.session_state.wa_emp_running = False
                        st.toast("🛑 " + ("تم إيقاف الإرسال" if is_ar else "Sending stopped"))
                        st.rerun()
                else:
                    ready_to_send = (pending_count > 0) and (bool(emp_message.strip()) or has_attachments)
                    att_label = f" ({len(st.session_state.wa_emp_saved_attachments)} مرفقات)" if has_attachments else ""
                    btn_send_label = f"📨 {'إرسال إلى' if is_ar else 'Send to'} {pending_count} {'عميل' if is_ar else 'clients'}{att_label}"
                    if st.button(btn_send_label, disabled=not ready_to_send, type="primary", width='stretch', key="btn_start_emp_send"):
                        # فحص اتصال واتساب
                        wa_stat = st.session_state.wa_service.get_status() if st.session_state.wa_service else "Stopped"
                        if wa_stat != "Connected":
                            st.error("⚠️ " + ("يرجى تشغيل محرك واتساب والاتصال أولاً" if is_ar else "WhatsApp is not connected!"))
                        else:
                            st.session_state.wa_emp_running = True
                            st.session_state.wa_emp_idx = 0
                            st.rerun()

            # ══════════════════════════════════════════════════════════
            # 🚀 حلقة الإرسال المباشرة لواتساب للعملاء (مع دعم المرفقات والأمان)
            # ══════════════════════════════════════════════════════════
            if is_sending:
                # --- إصلاح عداد الإرسال: نستخدم القائمة الكاملة دائماً وليس نسخة مفلترة
                # --- لحساب الإجمالي الأصلي بدقة وتجنب خلط الفهارس
                all_targets_full = st.session_state.wa_emp_targets
                full_total = len(all_targets_full)
                sent_count = sum(1 for t in all_targets_full if t.get('is_sent', False))
                remaining_count = full_total - sent_count

                # --- إيجاد العميل الحالي (أول عميل لم يُرسل له بعد) بالبحث في القائمة الكاملة
                # --- مهم جداً: نستخدم القائمة الأصلية للبحث لتجنب أي عدم تطابق في الفهارس
                current_client = None
                current_full_index = None
                for idx_full, _trg in enumerate(all_targets_full):
                    if not _trg.get('is_sent', False):
                        current_client = _trg
                        current_full_index = idx_full
                        break

                if remaining_count == 0 or current_client is None:
                    st.session_state.wa_emp_running = False
                    st.balloons()
                    st.success("🎉 " + ("اكتمل إرسال الرسائل والمرفقات لجميع العملاء بنجاح!" if is_ar else "All customer messages & attachments sent!"))
                    time.sleep(1)
                    st.rerun()
                else:
                    c_name = current_client.get('name', 'عميل')
                    c_phone_raw = current_client.get('phone', '')
                    
                    # تنظيف وتوحيد رقم الهاتف قبل الإرسال (درع إضافي ضد أي تنسيق خاطئ)
                    c_phone_clean_digits = _extract_only_digits(c_phone_raw)
                    c_phone = standardize_saudi_phone(c_phone_clean_digits)
                    if not c_phone:
                        # fallback: استخدم الأرقام النقية فقط إذا فشل التوحيد
                        if c_phone_clean_digits:
                            c_phone = c_phone_clean_digits
                        else:
                            c_phone = str(c_phone_raw).strip()
                    # تأكد من وجود + في البداية لو لم يكن موجود
                    if c_phone and not c_phone.startswith('+') and c_phone[0].isdigit():
                        c_phone = '+' + c_phone if len(c_phone) >= 11 else c_phone
                    
                    # تحديث رقم الهاتف في البيانات للعرض الصحيح (بالقائمة الكاملة)
                    all_targets_full[current_full_index]['phone'] = c_phone
                    
                    saved_attachments = st.session_state.get('wa_emp_saved_attachments', [])

                    # رقم التقدم الحالي: عدد المرسلة + 1 (اللي بنرسلها دلوقتي) مقسوم على الإجمالي الأصلي
                    progress_num = sent_count + 1
                    progress_den = full_total
                    remaining_after = full_total - progress_num

                    # بطاقة حالة الإرسال المباشرة مع تفاصيل المرفقات
                    progress_frac = progress_num / progress_den if progress_den > 0 else 0
                    st.progress(progress_frac)
                    att_info_html = ""
                    if saved_attachments:
                        att_names = ", ".join([os.path.basename(p) for p in saved_attachments])
                        att_info_html = f"""
                        <div style="margin-top: 6px; font-size: 0.88rem; color: #00E5FF;">
                            📎 <b>{'المرفقات الملحقة بالرسالة' if is_ar else 'Attached files'}:</b> {att_names}
                        </div>
                        """

                    st.markdown(f"""
                    <div style="background: rgba(0, 255, 100, 0.05); padding: 16px 20px; border-radius: 14px; border: 1.5px solid rgba(0, 255, 100, 0.3); margin: 12px 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="color: #00FF88; font-weight: 700; font-size: 1.05rem;">📤 {'جاري الإرسال للعميل' if is_ar else 'Sending to'}: {progress_num} / {progress_den}</span>
                            <span style="color: #D4AF37; font-weight: 700; font-size: 1.05rem;">⌛ {'متبقٍ' if is_ar else 'Remaining'}: {remaining_after}</span>
                        </div>
                        <div style="color: #FFFFFF; font-size: 0.95rem;">
                            👤 <strong>{c_name}</strong> · 📱 <span style="font-family: monospace; color: #00FF88;">{c_phone}</span>
                        </div>
                        {att_info_html}
                    </div>
                    """, unsafe_allow_html=True)

                    # تجهيز نص الرسالة وتخصيصه للعميل مع تنويع الصياغة
                    base_msg = emp_message.replace("{Name}", c_name).replace("{name}", c_name).replace("{الاسم}", c_name)
                    
                    # إضافة المدينة قبل نص الرسالة إذا كانت موجودة
                    c_city = current_client.get('city', '')
                    if c_city and c_city != ('غير محدد' if is_ar else 'Not specified'):
                        city_line = f"من {c_city}\n"
                        base_msg = city_line + base_msg
                    
                    # تنويع صياغة الرسالة للحفاظ على نفس المعنى مع تغيير الأسلوب
                    import random
                    message_variations = [
                        base_msg,  # الصيغة الأصلية
                        f"السلام عليكم ورحمة الله وبركاته،\n{base_msg}",  # مع السلام
                        f"مرحباً {c_name}،\n{base_msg}",  # مع مرحباً
                        f"تحية طيبة،\n{base_msg}",  # مع تحية طيبة
                        f"عزيزي {c_name}،\n{base_msg}",  # مع عزيزي
                    ]
                    personalized_msg = random.choice(message_variations)

                    # إضافة التوقيع العربي مع تنويع
                    signature_variations = [
                        "\n\nمع خالص التحية والتقدير،\nأبو فهد\nHR",
                        "\n\nتحياتي،\nأبو فهد\nHR",
                        "\n\nوتفضلوا بقبول فائق الاحترام،\nأبو فهد\nHR",
                        "\n\nشكراً لكم،\nأبو فهد\nHR",
                    ]
                    signature = random.choice(signature_variations)
                    if signature not in personalized_msg and personalized_msg.strip():
                        personalized_msg += signature

                    # إرسال متعدد: الرسالة أولاً ثم المرفقات بترتيب آمن
                    send_success = False
                    send_log = ""
                    
                    # الخطوة 1: إرسال الرسالة النصية أولاً
                    try:
                        # التأكد من أن الرسالة تحتوي على محتوى
                        if not personalized_msg or not personalized_msg.strip():
                            send_success = False
                            send_log = "الرسالة فارغة"
                            st.error("❌ الرسالة فارغة، يرجى إدخال نص الرسالة")
                        # التأكد من أن رقم الهاتف صحيح
                        elif not c_phone or len(c_phone) < 10:
                            send_success = False
                            send_log = "رقم الهاتف غير صحيح"
                            st.error(f"❌ رقم الهاتف غير صحيح: {c_phone}")
                        else:
                            with st.spinner(f"📨 {'جاري إرسال الرسالة النصية إلى' if is_ar else 'Sending text message to'} {c_name} ({c_phone})..."):
                                msg_ok, msg_log = st.session_state.wa_service.send_message(
                                    c_phone,
                                    personalized_msg,
                                    attachment_path=None  # رسالة نصية فقط بدون مرفقات
                                )
                            
                            if msg_ok:
                                send_success = True
                                send_log = msg_log
                                st.toast(f"✅ {'تم إرسال الرسالة النصية' if is_ar else 'Text message sent'}")
                                
                                # فاصل زمني قصير جداً بعد الرسالة (3 ثواني فقط)
                                time.sleep(3)
                            else:
                                send_success = False
                                send_log = msg_log
                                st.error(f"❌ {'فشل إرسال الرسالة' if is_ar else 'Failed to send message'}: {msg_log}")
                            
                    except Exception as e:
                        send_success = False
                        send_log = f"Exception: {str(e)}"
                        st.error(f"❌ {'خطأ في إرسال الرسالة' if is_ar else 'Error sending message'}: {e}")
                    
                    # الخطوة 2: إرسال المرفقات بترتيب آمن (PDF أولاً ثم الصور/فيديوهات)
                    if send_success and saved_attachments:
                        # تصنيف المرفقات
                        pdf_files = []
                        image_video_files = []
                        
                        for att in saved_attachments:
                            if att.lower().endswith('.pdf'):
                                pdf_files.append(att)
                            else:
                                image_video_files.append(att)
                        
                        # إرسال ملفات PDF أولاً بدون تأخير
                        for pdf in pdf_files:
                            try:
                                with st.spinner(f"📄 {'جاري إرسال ملف PDF' if is_ar else 'Sending PDF'}: {os.path.basename(pdf)}..."):
                                    pdf_ok, pdf_log = st.session_state.wa_service.send_message(
                                        c_phone,
                                        "",
                                        attachment_path=pdf
                                    )
                                if not pdf_ok:
                                    st.warning(f"⚠️ {'فشل إرسال ملف PDF' if is_ar else 'Failed to send PDF'}: {os.path.basename(pdf)}")
                            except Exception as e:
                                st.warning(f"⚠️ {'خطأ في إرسال PDF' if is_ar else 'Error sending PDF'}: {e}")
                        
                        # إرسال الصور والفيديوهات بدون تأخير
                        for idx, media in enumerate(image_video_files):
                            try:
                                with st.spinner(f"🖼️ {'جاري إرسال ملف وسائط' if is_ar else 'Sending media'}: {os.path.basename(media)}..."):
                                    media_ok, media_log = st.session_state.wa_service.send_message(
                                        c_phone,
                                        "",
                                        attachment_path=media
                                    )
                                if not media_ok:
                                    st.warning(f"⚠️ {'فشل إرسال ملف وسائط' if is_ar else 'Failed to send media'}: {os.path.basename(media)}")
                            except Exception as e:
                                st.warning(f"⚠️ {'خطأ في إرسال ملف وسائط' if is_ar else 'Error sending media'}: {e}")
                    
                    # تسجيل النتيجة في سجل الإرسال العام
                    att_summary = f" (مع {len(saved_attachments)} مرفق)" if (saved_attachments and send_success) else ""
                    log_entry = {
                        "idx": progress_num,
                        "name": c_name,
                        "phone": c_phone,
                        "status": f"{send_log}{att_summary}" if send_success else f"فشل ({send_log})",
                        "ok": send_success,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.wa_logs.append(log_entry)

                    if send_success:
                        # وضع علامة الإرسال بالفهرس الصحيح في القائمة الكاملة (مهم جداً لصحة التقدم)
                        st.session_state.wa_emp_targets[current_full_index]['is_sent'] = True
                        st.session_state.wa_history.add(c_phone)
                        save_wa_history(st.session_state.wa_history)
                    # إذا كان الرقم غير مسجل في واتساب، وضعه كمُرسل لتجنب إعادة المحاولة
                    elif "غير مسجل" in send_log or "not on whatsapp" in send_log.lower():
                        st.session_state.wa_emp_targets[current_full_index]['is_sent'] = True
                        st.toast(f"⏭️ تم تخطي الرقم غير المسجل: {c_phone}")

                    # 🛡️ إيقاف فوري إذا كان خطأ أمان لحماية الحساب من الحظر
                    if not send_success and str(send_log).startswith("🛑"):
                        st.session_state.wa_emp_running = False
                        st.error(f"🛑 {send_log}")
                        st.toast("🛑 تم إيقاف الإرسال لحماية الحساب من الحظر", icon="⚠️")
                    else:
                        # لا نعتمد على wa_emp_idx كفهرس مباشر - نحافظ عليه فقط للإشارة
                        st.session_state.wa_emp_idx = current_full_index + 1
                        
                        # حساب التأخير العشوائي الذكي بين الرسائل (حماية الحساب ضد الحظر)
                        still_remaining = full_total - (sent_count + (1 if send_success else 0))
                        if still_remaining > 0:
                            # فحص استراحة الدفعات (بناءً على عدد المرسلة حتى الآن)
                            total_sent_so_far = sent_count + (1 if send_success else 0)
                            is_break = (emp_batch_break > 0 and total_sent_so_far > 0 and total_sent_so_far % emp_batch_break == 0)
                            if is_break:
                                delay_sec = int(emp_batch_pause_mins * 60)
                                break_msg = f"🛡️ استراحة دفعات أمان دورية لحماية الحساب ({emp_batch_pause_mins} دقيقة)"
                            else:
                                low_s = max(30 if saved_attachments else 20, int(emp_min_delay))
                                high_s = max(low_s + 5, int(emp_max_delay))
                                delay_sec = random.randint(low_s, high_s)
                                # إضافة تشتيت عشوائي ذكي (Jitter) لمحاكاة السلوك البشري الطبيعي
                                delay_sec = max(low_s, delay_sec + random.randint(-2, 3))
                                media_tag = " (محملة بمرفقات)" if saved_attachments else ""
                                break_msg = f"⏳ انتظار أمان ذكي لحماية الحساب من الحظر{media_tag} ({delay_sec} ثانية)"

                            # عداد تنازلي تفاعلي أنيق
                            timer_ph = st.empty()
                            timer_color = "#FFA500" if saved_attachments else "#00E5FF"
                            for rem in range(delay_sec, 0, -1):
                                if not st.session_state.get('wa_emp_running', False):
                                    break
                                m, s = divmod(rem, 60)
                                timer_str = f"{m:02d}:{s:02d}" if m > 0 else f"{s} ثانية"
                                timer_ph.markdown(f"""
                                <div style="background: rgba(0, 229, 255, 0.05); border: 1.5px solid {timer_color}; border-radius: 14px; padding: 15px; text-align: center; margin: 10px 0;">
                                    <div style="color: {timer_color}; font-weight: 700; font-size: 1.05rem;">{break_msg}</div>
                                    <div style="font-size: 2.2rem; font-weight: 800; color: #FFFFFF; font-family: monospace; margin: 5px 0;">{timer_str}</div>
                                    <div style="font-size: 0.8rem; color: #AAA;">🛡️ حماية متقدمة ضد الحظر التلقائي من خوارزميات واتساب</div>
                                </div>
                                """, unsafe_allow_html=True)
                                time.sleep(1)
                            timer_ph.empty()

                        if st.session_state.get('wa_emp_running', False):
                            st.rerun()

        else:
            st.info("💡 " + ("يرجى اختيار مصدر البيانات بالأعلى واستخراج قائمة العملاء للبدء في كتابة الرسالة والإرسال." if is_ar else "Please choose a data source and extract customer list to begin."))

        # ──────────────────────────────────────────────────────────────
        # 3. سجل الإرسال الحديث ببطاقات أنيقة (Send Log)
        # ──────────────────────────────────────────────────────────────
        if st.session_state.get('wa_logs', []):
            st.markdown("---")
            with st.expander(lbl['log_title'], expanded=True):
                lg_col1, lg_col2 = st.columns([3, 1])
                with lg_col2:
                    if st.button(lbl['delete_log'], width='stretch', key="emp_clear_log_btn"):
                        st.session_state.wa_logs = []
                        st.rerun()
                
                for entry in reversed(st.session_state.wa_logs):
                    if isinstance(entry, str):
                        st.text(entry)
                        continue
                    status_cls = "status-success" if entry.get('ok') else "status-error"
                    status_t = entry.get('status', '')
                    st.markdown(f"""
                    <div class="log-card">
                        <div class="log-info">
                            <div class="log-name">{entry.get('name', 'عميل')}</div>
                            <div class="log-phone">📱 {entry.get('phone', '')}</div>
                        </div>
                        <div class="log-status-group">
                            <div class="log-status">
                                <span class="status-badge {status_cls}">{status_t}</span>
                                <span class="log-time">🕒 {entry.get('time', '')}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

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
    if (status in ["Awaiting Login", "Loading..."]) and st.session_state.wa_service and st.session_state.wa_service.driver:
        scan_title = lbl.get('wa_scan_msg', "امسح الكود باستخدام الواتساب في جوالك" if is_ar else "Scan with WhatsApp on your phone")
        st.markdown(f'<div style="text-align:center; padding:10px 0;"><h4 style="color:#00FF88;">📱 {scan_title}</h4></div>', unsafe_allow_html=True)
        qr_b64 = st.session_state.wa_service.get_qr_hd()
        if qr_b64:
            src = qr_b64 if qr_b64.startswith("data:") else f"data:image/png;base64,{qr_b64}"
            st.markdown(f'<div style="background: #FFFFFF; padding: 25px; border-radius: 20px; max-width: 420px; margin: 15px auto; text-align: center; box-shadow: 0 0 40px rgba(0,255,136,0.3); border: 2px solid #00FF88;"><img src="{src}" style="width: 350px; height: 350px; image-rendering: pixelated; image-rendering: crisp-edges;" /></div>', unsafe_allow_html=True)
        else:
            st.warning("⏳ " + ("جاري تحضير رمز الباركود من واتساب..." if is_ar else "Preparing QR code from WhatsApp..."))
            diag_b64 = st.session_state.wa_service.get_diagnostic_screenshot()
            if diag_b64:
                d_src = diag_b64 if diag_b64.startswith("data:") else f"data:image/png;base64,{diag_b64}"
                with st.expander("📸 " + ("لقطة شاشة تشخيصية من المتصفح" if is_ar else "Diagnostic Browser Screenshot"), expanded=True):
                    st.image(d_src, caption="Browser Screen State", use_container_width=True)
        
        b1, b2 = st.columns(2)
        with b1:
            if st.button(lbl['refresh_qr'], width='stretch', key="refresh_qr_main"):
                st.rerun()
        with b2:
            if st.button(lbl['verify'], width='stretch', type="primary", key="verify_qr_main"):
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
        # 🛡️ شريط الأمان وإحصائيات اليوم وزر فك القفل في وضع ماركتنج
        m_sec1, m_sec2 = st.columns([3, 1])
        with m_sec1:
            stats_m = st.session_state.wa_service.get_daily_stats() if st.session_state.wa_service else {}
            ok_m = stats_m.get('sent_ok', 0)
            fail_m = stats_m.get('sent_fail', 0)
            inval_m = stats_m.get('invalid_numbers', 0)
            st.markdown(
                f'<div style="background: rgba(0,255,136,0.06); padding: 10px 15px; border-radius: 10px; border: 1px solid rgba(0,255,136,0.2); font-size: 0.9rem;">'
                f'🛡️ <b>{"درع الحماية من الحظر" if is_ar else "Anti-Ban Shield"}:</b> '
                f'{"تم إرسال اليوم" if is_ar else "Today Sent"}: <span style="color:#00FF88; font-weight:bold;">{ok_m}</span> | '
                f'{"محاولات فاشلة" if is_ar else "Failed"}: <span style="color:#FF6B6B; font-weight:bold;">{fail_m}</span> | '
                f'{"أرقام غير صالحة" if is_ar else "Invalid"}: <span style="color:#FFA500; font-weight:bold;">{inval_m}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        with m_sec2:
            if st.button("🔄 " + ("فك قفل الأمان" if is_ar else "Reset Counter"), key="mkt_unblock_btn", help="تصفير عداد الأخطاء وفك أي قفل أمان مؤقت"):
                if st.session_state.wa_service:
                    st.session_state.wa_service.reset_daily_stats()
                    st.toast("✅ " + ("تم فك قفل الأمان وتصفير العداد بنجاح" if is_ar else "Anti-ban counters reset successfully!"))
                    st.rerun()

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
                                    # تنظيف المفتاح لإزالة الرموز الخاصة
                                    clean_phone_key = trg['phone'].replace('+', '').replace('-', '').replace(' ', '')
                                    if r_c1.checkbox(f"{trg['name']} ({trg['phone'][-4:]})", value=False, key=f"trg_pending_{i}_{clean_phone_key}"):
                                        st.session_state.wa_review_targets[i]['is_sent'] = True
                                        st.session_state.wa_history.add(trg['phone'])
                                        save_wa_history(st.session_state.wa_history)
                                        st.rerun()
                                    # تنظيف المفتاح لإزالة الرموز الخاصة
                                    clean_phone_key = trg['phone'].replace('+', '').replace('-', '').replace(' ', '')
                                    if r_c2.button("🗑️", key=f"trg_del_p_{i}_{clean_phone_key}"):
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
                                    # تنظيف المفتاح لإزالة الرموز الخاصة
                                    clean_phone_key = trg['phone'].replace('+', '').replace('-', '').replace(' ', '')
                                    if r_c4.button("🗑️", key=f"trg_del_e_{i}_{clean_phone_key}"):
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
            
            # 🛡️ Build review targets only when NOT sending — never interrupt the send loop
            if not st.session_state.get('wa_running', False):
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
        final_targets = [trg for trg in st.session_state.wa_review_targets if not trg['is_sent']]


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
        
        # --- ⚙️ Smart Templates Components Editor (before preview so live edits apply) ---
        with st.expander("🛠️ " + ("تعديل مكونات الرسائل الذكية" if is_ar else "Edit Smart Message Components"), expanded=is_smart):
            templates_data_smart = load_templates()
            smart_parts = {k: list(v) for k, v in templates_data_smart.get("smart", SMART_TEMPLATES).items()}
            original_smart_parts = {k: list(v) for k, v in smart_parts.items()}

            st.caption("💡 " + (
                "افصل بين الخيارات بسطر يحتوي --- حتى تبقى النصوص متعددة الأسطر خياراً واحداً."
                if is_ar else
                "Separate options with a line containing --- so multi-line texts stay as one option."
            ))

            for part_key, part_list in smart_parts.items():
                st.markdown(f"**{part_key.replace('_', ' ').title()}**")
                new_list_str = st.text_area(
                    f"Options for {part_key}",
                    value=_join_smart_part_list(part_list),
                    height=120,
                    key=f"smart_comp_{part_key}",
                )
                smart_parts[part_key] = _split_smart_part_text(new_list_str)

            st.session_state.smart_parts_live = smart_parts
            has_changes = any(original_smart_parts.get(k) != smart_parts.get(k) for k in original_smart_parts)

            save_col1, save_col2 = st.columns([2, 1])
            with save_col1:
                if st.button(
                    "💾 " + ("حفظ التغييرات وتحديث المعاينة" if is_ar else "Save Changes & Update Preview"),
                    type="primary" if has_changes else "secondary",
                    key="save_smart_parts",
                ):
                    templates_data_smart["smart"] = smart_parts
                    save_templates(templates_data_smart)
                    st.session_state.smart_parts_live = smart_parts
                    st.session_state.smart_preview_nonce = st.session_state.get("smart_preview_nonce", 0) + 1
                    st.toast("✅ " + ("تم حفظ التغييرات وتحديث المعاينة بنجاح!" if is_ar else "Changes saved and preview updated!"))
                    st.rerun()

            with save_col2:
                if has_changes:
                    st.info("📝 " + ("هناك تغييرات غير محفوظة" if is_ar else "Unsaved changes"))
                else:
                    st.success("✅ " + ("جميع التغييرات محفوظة" if is_ar else "All changes saved"))

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
            st.info("💡 " + ("سيتم توليد رسالة فريدة لكل رقم تلقائياً عند بدء الإرسال." if is_ar else "A unique message will be generated for each number upon sending."))

            live_templates = get_live_smart_templates()
            use_random_preview = bool(st.session_state.pop("smart_preview_randomize", False))
            preview_msg = generate_smart_message(
                "{Name}",
                "{CV}",
                custom_job=st.session_state.get("wa_custom_job_val", ""),
                templates=live_templates,
                stable=not use_random_preview,
            )

            # Streamlit ignores `value` on a keyed widget after first render; remount when content changes.
            preview_token = abs(hash(preview_msg + str(st.session_state.get("smart_preview_nonce", 0))))
            for stale_key in [k for k in st.session_state.keys() if str(k).startswith("smart_preview_area")]:
                if stale_key != f"smart_preview_area_{preview_token}":
                    try:
                        del st.session_state[stale_key]
                    except Exception:
                        pass

            preview_col1, preview_col2 = st.columns([4, 1])
            with preview_col1:
                st.text_area(
                    "معاينة الرسالة الذكية (Smart Message Preview)",
                    value=preview_msg,
                    height=250,
                    disabled=True,
                    key=f"smart_preview_area_{preview_token}",
                )
                st.caption("🔎 " + (
                    "المعاينة تستخدم الخيار الأول من كل مكوّن بعد التعديل. اضغط تحديث لعرض عينة عشوائية."
                    if is_ar else
                    "Preview uses the first option of each component after edits. Click Refresh for a random sample."
                ))
            with preview_col2:
                if st.button("🔄 " + ("تحديث" if is_ar else "Refresh"), key="refresh_preview"):
                    st.session_state.smart_preview_randomize = True
                    st.session_state.smart_preview_nonce = st.session_state.get("smart_preview_nonce", 0) + 1
                    st.rerun()
            
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

        # 📎 مرفقات متعددة: صور، فيديوهات، مستندات PDF وملفات أخرى
        st.markdown("---")
        st.markdown(f"#### 📎 {'مرفقات الرسالة (صور 🖼️ + فيديوهات 🎥 + مستندات 📄 PDF وملفات)' if is_ar else 'Message Attachments (Images + Videos + PDFs & more)'}")
        st.caption("💡 " + ("يمكنك رفع ملفات متعددة في نفس الوقت: صور (JPG/PNG/GIF/WEBP)، فيديوهات (MP4/MOV/AVI/MKV)، مستندات (PDF/DOCX/XLSX/PPTX)، وملفات أخرى." if is_ar else "You can upload multiple files at once: Images (JPG/PNG/GIF/WEBP), Videos (MP4/MOV/AVI/MKV), Documents (PDF/DOCX/XLSX/PPTX), and more."))

        attachments_uploaded = st.file_uploader(
            "📎 " + ("اختر أو اسحب الملفات (أو اضغط هنا للاختيار)" if is_ar else "Upload one or more files (click or drag)"),
            type=["png","jpg","jpeg","gif","bmp","webp",
                  "pdf","doc","docx","xls","xlsx","ppt","pptx",
                  "mp4","avi","mov","mkv","3gp",
                  "mp3","wav","ogg",
                  "zip","rar","7z","txt","csv"],
            accept_multiple_files=True,
            key="wa_marketing_attachments"
        )

        # معالجة وحفظ المرفقات في مجلد الجلسة (قائمة مسارات)
        marketing_attachments_paths = []
        if attachments_uploaded and len(attachments_uploaded) > 0:
            base_no_dot = os.path.join(os.getcwd(), "whatsapp_session")
            base_with_dot = os.path.join(os.getcwd(), ".whatsapp_session")
            temp_dir = base_no_dot if os.path.exists(base_no_dot) else (base_with_dot if os.path.exists(base_with_dot) else base_no_dot)
            mrkt_uploads_dir = os.path.join(temp_dir, "marketing_temp_uploads")
            os.makedirs(mrkt_uploads_dir, exist_ok=True)

            total_size_bytes = 0
            st.markdown("<div style='margin: 8px 0; display: flex; flex-wrap: wrap; gap: 8px;'>", unsafe_allow_html=True)
            for f in attachments_uploaded:
                total_size_bytes += f.size
                file_ext = os.path.splitext(f.name)[1].lower()
                if file_ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp']:
                    icon = "🖼️ [صورة]"
                elif file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.3gp']:
                    icon = "🎥 [فيديو]"
                elif file_ext == '.pdf':
                    icon = "📄 [PDF]"
                elif file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv']:
                    icon = "📝 [مستند]"
                elif file_ext in ['.mp3', '.wav', '.ogg']:
                    icon = "🎵 [صوت]"
                elif file_ext in ['.zip', '.rar', '.7z']:
                    icon = "🗜️ [مضغوط]"
                else:
                    icon = "📎 [ملف]"

                sz_str = f"{f.size / (1024*1024):.2f} MB" if f.size >= 1024*1024 else f"{f.size / 1024:.1f} KB"
                st.markdown(
                    f"<div style='background: rgba(0, 229, 255, 0.08); border: 1px solid rgba(0, 229, 255, 0.3); border-radius: 10px; padding: 7px 14px; display: inline-block;'>"
                    f"<b>{icon}</b> {f.name} <span style='color: #00E5FF;'>({sz_str})</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                # حفظ الملف في مجلد مؤقت
                save_path = os.path.join(mrkt_uploads_dir, f.name)
                try:
                    with open(save_path, "wb") as out_f:
                        out_f.write(f.getbuffer())
                    marketing_attachments_paths.append(save_path)
                except Exception as att_err:
                    st.error(f"❌ {'خطأ في حفظ الملف ' if is_ar else 'Failed to save file '}{f.name}: {str(att_err)}")
            st.markdown("</div>", unsafe_allow_html=True)
            st.session_state.wa_temp_attachments = marketing_attachments_paths
            # حفظ متوافق مع الكود القديم (لو كان ملف واحد فقط)
            if len(marketing_attachments_paths) == 1:
                st.session_state.wa_temp_path = marketing_attachments_paths[0]
        else:
            st.session_state.wa_temp_attachments = []
            st.session_state.wa_temp_path = None

        mrkt_has_att = bool(st.session_state.get('wa_temp_attachments', []))

        # 🛡️ تنبيهات الأمان عند وجود مرفقات في واتساب ماركتنج
        if mrkt_has_att:
            st.markdown(f"""
            <div style="background: rgba(255, 170, 0, 0.08); border: 1.5px solid rgba(255, 170, 0, 0.4); border-radius: 12px; padding: 12px 18px; margin: 12px 0;">
                <div style="color: #FFA500; font-weight: 700; font-size: 0.95rem; margin-bottom: 4px;">
                    🛡️ {'تم تفعيل درع الأمان التلقائي لمرفقات الوسائط والملفات' if is_ar else 'Media & Files Anti-Ban Shield Activated'}
                </div>
                <div style="color: #E0E0E0; font-size: 0.85rem; line-height: 1.5;">
                    {'⚠️ <b>تنبيه:</b> إرسال الصور/الفيديوهات/المستندات يتطلب وقتاً أطول في الرفع والمعالجة ويخضع لرقابة السبام.<br>✅ <b>نرجوع الالتزام بالفترات الأمنية الآتية:</b> أقصى سرعة 45-90 ثانية بين الرسائل، واستراحة دورية كل دفعة لحماية رقمك من الحظر.' if is_ar else '⚠️ <b>Notice:</b> Sending media/videos/docs requires longer upload times and strict anti-spam pacing.<br>✅ <b>Please keep safe delays:</b> 45-90s min between messages, with periodic batch breaks.'}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown(lbl['settings_title'])
        col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
        with col_s1:
            min_delay = st.number_input("أدنى مهلة (ثانية)" if is_ar else "Min Delay (s)", min_value=30, max_value=300, value=60, disabled=st.session_state.wa_running,
                                        help=("🛡️ أدنى وقت انتظار عشوائي بين الرسائل (الافتراضي 60 ثانية)" if is_ar else "🛡️ Minimum random delay (default 60s)"))
        with col_s2:
            max_delay = st.number_input("أقصى مهلة (ثانية)" if is_ar else "Max Delay (s)", min_value=30, max_value=600, value=120, disabled=st.session_state.wa_running,
                                        help=("🛡️ أقصى وقت انتظار عشوائي بين الرسائل (الافتراضي 120 ثانية)" if is_ar else "🛡️ Maximum random delay (default 120s)"))
        with col_s3:
            # 🛡️ min_value = 5 على الأقل — ممنوع الصفر (كان يسمح بإلغاء الاستراحة تماماً)
            batch_size = st.number_input(lbl['batch_size'], min_value=5, max_value=100, value=10, help=lbl['batch_help'], disabled=st.session_state.wa_running)
        with col_s4:
            # 🛡️ min 3 دقائق بدل 1 (يوصى 10 دقائق فما فوق)
            batch_delay_mins = st.number_input(lbl['batch_delay'], min_value=3, max_value=60, value=10, disabled=st.session_state.wa_running,
                                               help=("🛡️ 3 دقائق على الأقل بين الدفعات (يوصى 10+)" if is_ar else "🛡️ Min 3 min between batches (recommended 10+)"))
            batch_delay = int(batch_delay_mins * 60)
        with col_s5:
            msg_switch_threshold = st.number_input("تبديل الرسالة بعد" if is_ar else "Switch msg after", min_value=1, max_value=50, value=2, disabled=st.session_state.wa_running)

        # Smart detect target changes
        current_fp = ",".join([trg['phone'] for trg in final_targets]) if final_targets else ""
        if current_fp != st.session_state.get('wa_sent_fingerprint', ''):
            st.session_state.wa_done = False

        # ══════════════════════════════════════════════════════════
        # 🚀 أزرار الإرسال / الإيقاف (مع دعم المرفقات المتعددة)
        # ══════════════════════════════════════════════════════════
        btn1, btn2, btn3 = st.columns([1, 1, 2])
        with btn1:
            if st.session_state.get('wa_running', False):
                if st.button(lbl['stop'], type="primary", width='stretch', key="wa_stop_btn"):
                    st.session_state.wa_running = False
                    # تنظيف كافة المرفقات المؤقتة عند الإيقاف
                    _temp_all = st.session_state.get('wa_temp_attachments', []) or []
                    for _p in _temp_all:
                        try:
                            if os.path.exists(_p): os.remove(_p)
                        except: pass
                    if st.session_state.get('wa_temp_path') and os.path.exists(st.session_state.wa_temp_path):
                        try: os.remove(st.session_state.wa_temp_path)
                        except: pass
                    st.session_state.wa_temp_attachments = []
                    st.session_state.wa_temp_path = None
                    st.toast("🛑 " + ("تم إيقاف الإرسال" if is_ar else "Sending stopped"))
                    st.rerun()
            else:
                has_valid_msg = any(msg.strip() != "" for msg in st.session_state.wa_messages) or st.session_state.get('wa_smart_mode', False)
                mrkt_att_list = st.session_state.get('wa_temp_attachments', []) or []
                mrkt_att_count = len(mrkt_att_list)
                # يسمح بالإرسال لو فيه رسالة صالحة OR مرفقات (إرسال ملفات بدون رسالة نصية مسموح)
                ready = len(final_targets) > 0 and (has_valid_msg or mrkt_att_count > 0)

                if st.session_state.get('wa_done', False) and current_fp == st.session_state.get('wa_sent_fingerprint', ''):
                    st.button(lbl['sent_done'], disabled=True, width='stretch')
                else:
                    send_label_extra = f" ({mrkt_att_count} مرفقات)" if mrkt_att_count > 0 else ""
                    btn_label = lbl['send'].format(len(final_targets)) + send_label_extra
                    if st.button(btn_label, disabled=not ready, width='stretch', type="primary", key="wa_send_btn"):
                        # Check WhatsApp connection
                        wa_stat = st.session_state.wa_service.get_status() if st.session_state.wa_service else "Stopped"
                        if wa_stat != "Connected":
                            st.error("⚠️ " + ("يرجى تشغيل محرك واتساب ومسح الباركود أولاً للاتصال" if is_ar else "Please start WhatsApp engine and scan QR first to connect"))
                        else:
                            # المرفقات محفوظة مسبقاً في wa_temp_attachments من قسم الرفع الأعلى
                            # نضمن فقط وجود القائمة بشكل صحيح
                            if not st.session_state.get('wa_temp_attachments'):
                                st.session_state.wa_temp_attachments = []
                            st.session_state.wa_running = True
                            st.session_state.wa_idx = 0
                            st.session_state.wa_done = False
                            st.session_state.wa_sent_fingerprint = current_fp
                            st.rerun()

        # ══════════════════════════════════════════════════════════
        # 🚀 حلقة الإرسال والعداد التنازلي المباشر (Live Sending Loop & Countdown)
        # ══════════════════════════════════════════════════════════
        # 🛡️ إذا كان wa_running لكن لا توجد أهداف — أوقف الحلقة بأمان
        if st.session_state.get('wa_running', False) and not final_targets:
            st.session_state.wa_running = False
            st.session_state.wa_done = True
            st.warning("⚠️ " + ("لا توجد أرقام جاهزة للإرسال. ربما تم إرسالها جميعاً." if is_ar else "No numbers ready to send. They may have all been sent already."))
        elif st.session_state.get('wa_running', False) and final_targets:
            total_targets = len(final_targets)
            curr_i = st.session_state.get('wa_idx', 0)

            if curr_i < total_targets:
                trg = final_targets[curr_i]
                p = trg.get('phone', '')
                n = trg.get('name', 'Client')
                v = trg.get('cv', '')

                # 1. Progress Bar & Live Status Card
                sent_pct = (curr_i / total_targets * 100) if total_targets > 0 else 0
                st.progress(min(1.0, (curr_i + 1) / total_targets))

                st.markdown(f"""
                <div style="background: rgba(0, 255, 100, 0.05); padding: 16px 20px; border-radius: 14px; border: 1.5px solid rgba(0, 255, 100, 0.3); margin: 12px 0; box-shadow: 0 0 15px rgba(0, 255, 100, 0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="color: #00FF88; font-weight: 700; font-size: 1.05rem;">📤 {'جاري إرسال الرسالة' if is_ar else 'Sending Message'}: {curr_i + 1} / {total_targets}</span>
                        <span style="color: #D4AF37; font-weight: 700; font-size: 1.05rem;">⌛ {'متبقٍ' if is_ar else 'Remaining'}: {total_targets - (curr_i + 1)}</span>
                    </div>
                    <div style="color: #FFFFFF; font-size: 0.95rem;">
                        👤 <strong>{n}</strong> · 📱 <span style="font-family: monospace; color: #00FF88;">{p}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 2. Message Generation
                if st.session_state.get('wa_smart_mode', False):
                    final_msg = generate_smart_message(
                        n,
                        v,
                        custom_job=st.session_state.get('wa_custom_job_val', ''),
                        templates=get_live_smart_templates(),
                    )
                else:
                    msg_idx = (curr_i // max(1, int(msg_switch_threshold))) % len(st.session_state.wa_messages)
                    msg_template = st.session_state.wa_messages[msg_idx]
                    
                    final_msg = msg_template
                    for k, val_k in trg.items():
                        final_msg = final_msg.replace("{" + str(k) + "}", str(val_k))
                    final_msg = final_msg.replace("{Name}", n).replace("{name}", n).replace("{الاسم}", n)
                    final_msg = final_msg.replace("{CV}", v).replace("{cv}", v).replace("{السيرة}", v)
                    import re
                    final_msg = re.sub(r'\n{3,}', '\n\n', final_msg).strip()

                temp_path = st.session_state.get('wa_temp_path')
                attachments_list = st.session_state.get('wa_temp_attachments') or []
                # إنشاء قائمة المرفقات للخدمة: نعطي الأولوية للقائمة الكاملة
                # ولو فاضت نستخدم temp_path القديمة للتوافق العكسي
                wa_final_attachments = None
                if attachments_list and len(attachments_list) > 0:
                    wa_final_attachments = [p for p in attachments_list if p and os.path.exists(str(p))]
                    if not wa_final_attachments and temp_path and os.path.exists(temp_path):
                        wa_final_attachments = [temp_path]
                elif temp_path and os.path.exists(temp_path):
                    wa_final_attachments = [temp_path]

                att_count_final = len(wa_final_attachments) if wa_final_attachments else 0
                att_info_html_mrkt = ""
                if att_count_final > 0:
                    att_names = ", ".join([os.path.basename(p) for p in wa_final_attachments])
                    att_info_html_mrkt = f"""
                    <div style="margin-top: 8px; font-size: 0.88rem; color: #00E5FF;">
                        📎 <b>{'المرفقات' if is_ar else 'Attachments'} ({att_count_final}):</b> {att_names}
                    </div>
                    """

                # تحديث بطاقة الحالة لإظهار معلومات المرفقات إن وجدت
                if att_count_final > 0:
                    # إعادة طباعة البطاقة مع إضافة قسم المرفقات
                    st.markdown(f"""
                    <div style="background: rgba(0, 255, 100, 0.05); padding: 16px 20px; border-radius: 14px; border: 1.5px solid rgba(0, 255, 100, 0.3); margin: 12px 0; box-shadow: 0 0 15px rgba(0, 255, 100, 0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="color: #00FF88; font-weight: 700; font-size: 1.05rem;">📤 {'جاري إرسال الرسالة + مرفقات' if is_ar else 'Sending Msg + Attachments'}: {curr_i + 1} / {total_targets}</span>
                            <span style="color: #D4AF37; font-weight: 700; font-size: 1.05rem;">⌛ {'متبقٍ' if is_ar else 'Remaining'}: {total_targets - (curr_i + 1)}</span>
                        </div>
                        <div style="color: #FFFFFF; font-size: 0.95rem;">
                            👤 <strong>{n}</strong> · 📱 <span style="font-family: monospace; color: #00FF88;">{p}</span>
                        </div>
                        {att_info_html_mrkt}
                    </div>
                    """, unsafe_allow_html=True)

                # إضافة التوقيع الإنجليزي لواتساب ماركتنج
                signature = "\n\nBest regards,\nAbu Fahd\nHR Manager"
                if signature not in final_msg:
                    final_msg += signature

                # 3. إرسال متعدد آمن: الرسالة أولاً ثم المرفقات بترتيب آمن
                send_success_mk = False
                send_log_mk = ""
                
                # الخطوة 1: إرسال الرسالة النصية أولاً
                try:
                    with st.spinner(f"📨 {'جاري إرسال الرسالة النصية إلى' if is_ar else 'Sending text message to'} {n} ({p})..."):
                        msg_ok_mk, msg_log_mk = st.session_state.wa_service.send_message(
                            p,
                            final_msg,
                            attachment_path=None  # رسالة نصية فقط بدون مرفقات
                        )
                    
                    if msg_ok_mk:
                        send_success_mk = True
                        send_log_mk = msg_log_mk
                        st.toast(f"✅ {'تم إرسال الرسالة النصية' if is_ar else 'Text message sent'}")
                        
                        # فاصل زمني قصير جداً بعد الرسالة (3 ثواني فقط)
                        time.sleep(3)
                    else:
                        send_success_mk = False
                        send_log_mk = msg_log_mk
                        st.error(f"❌ {'فشل إرسال الرسالة' if is_ar else 'Failed to send message'}: {msg_log_mk}")
                        
                except Exception as e:
                    send_success_mk = False
                    send_log_mk = f"Exception: {str(e)}"
                    st.error(f"❌ {'خطأ في إرسال الرسالة' if is_ar else 'Error sending message'}: {e}")
                
                # الخطوة 2: إرسال المرفقات بترتيب آمن (PDF أولاً ثم الصور/فيديوهات)
                if send_success_mk and (wa_final_attachments or temp_path):
                    # تصنيف المرفقات
                    all_attachments = wa_final_attachments if wa_final_attachments else ([temp_path] if temp_path else [])
                    pdf_files_mk = []
                    image_video_files_mk = []
                    
                    for att in all_attachments:
                        if att and att.lower().endswith('.pdf'):
                            pdf_files_mk.append(att)
                        elif att:
                            image_video_files_mk.append(att)
                    
                    # إرسال ملفات PDF أولاً بدون تأخير
                    for pdf in pdf_files_mk:
                        try:
                            with st.spinner(f"📄 {'جاري إرسال ملف PDF' if is_ar else 'Sending PDF'}: {os.path.basename(pdf)}..."):
                                pdf_ok_mk, pdf_log_mk = st.session_state.wa_service.send_message(
                                    p,
                                    "",
                                    attachment_path=pdf
                                )
                            if not pdf_ok_mk:
                                st.warning(f"⚠️ {'فشل إرسال ملف PDF' if is_ar else 'Failed to send PDF'}: {os.path.basename(pdf)}")
                        except Exception as e:
                            st.warning(f"⚠️ {'خطأ في إرسال PDF' if is_ar else 'Error sending PDF'}: {e}")
                    
                    # إرسال الصور والفيديوهات بدون تأخير
                    for idx, media in enumerate(image_video_files_mk):
                        try:
                            with st.spinner(f"🖼️ {'جاري إرسال ملف وسائط' if is_ar else 'Sending media'}: {os.path.basename(media)}..."):
                                media_ok_mk, media_log_mk = st.session_state.wa_service.send_message(
                                    p,
                                    "",
                                    attachment_path=media
                                )
                            if not media_ok_mk:
                                st.warning(f"⚠️ {'فشل إرسال ملف وسائط' if is_ar else 'Failed to send media'}: {os.path.basename(media)}")
                        except Exception as e:
                            st.warning(f"⚠️ {'خطأ في إرسال ملف وسائط' if is_ar else 'Error sending media'}: {e}")
                
                # 4. Record Log
                att_summary = f" (+{att_count_final} مرفق)" if (send_success_mk and att_count_final > 0) else ""
                entry = {
                    "idx": curr_i + 1,
                    "name": n,
                    "phone": p,
                    "status": f"{send_log_mk}{att_summary}" if send_success_mk else f"فشل ({send_log_mk})",
                    "ok": send_success_mk,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.wa_logs.append(entry)
                if send_success_mk:
                    st.session_state.wa_history.add(p)
                    save_wa_history(st.session_state.wa_history)
                    for r_i, r_trg in enumerate(st.session_state.wa_review_targets):
                        if r_trg.get('phone') == p:
                            st.session_state.wa_review_targets[r_i]['is_sent'] = True
                            break

                # 🛡️ إيقاف فوري للحملة إذا تم إرجاع تنبيه أمان لمنع حظر الحساب وحفظ باقي الأرقام
                if not ok and str(log_msg).startswith("🛑"):
                    st.session_state.wa_running = False
                    # تنظيف المرفقات عند الإيقاف الأمني
                    _temp_all = st.session_state.get('wa_temp_attachments', []) or []
                    for _p in _temp_all:
                        try:
                            if os.path.exists(_p): os.remove(_p)
                        except: pass
                    if st.session_state.get('wa_temp_path') and os.path.exists(st.session_state.wa_temp_path):
                        try: os.remove(st.session_state.wa_temp_path)
                        except: pass
                    st.error(f"🛑 تم إيقاف الحملة لحماية الحساب من الحظر: {log_msg}")
                    st.toast("🛑 تم إيقاف الحملة لحماية الحساب", icon="⚠️")
                else:
                    # 5. Move to next index
                    st.session_state.wa_idx += 1

                    # 6. Check if completed
                    if st.session_state.wa_idx >= total_targets:
                        st.session_state.wa_running = False
                        st.session_state.wa_done = True
                        # تنظيف كافة الملفات المؤقتة للمرفقات عند الانتهاء
                        _cleanup_all = st.session_state.get('wa_temp_attachments', []) or []
                        for _p in _cleanup_all:
                            try:
                                if os.path.exists(_p): os.remove(_p)
                            except: pass
                        if temp_path and os.path.exists(temp_path):
                            try: os.remove(temp_path)
                            except: pass
                        st.session_state.wa_temp_attachments = []
                        st.session_state.wa_temp_path = None
                        st.balloons()
                        st.success("🎉 " + ("اكتمل إرسال جميع الرسائل والمرفقات بنجاح!" if is_ar else "All messages & attachments sent successfully!"))
                        time.sleep(1)
                        st.rerun()
                    else:
                        # 7. ⏱️ LIVE DYNAMIC RANDOM COUNTDOWN TIMER (60s - 120s unique per message)
                        is_batch_break = (batch_size > 0 and st.session_state.wa_idx % batch_size == 0)
                        if is_batch_break:
                            wait_seconds = batch_delay
                        else:
                            low_d = min(int(min_delay), int(max_delay))
                            high_d = max(int(min_delay), int(max_delay))
                            wait_seconds = random.randint(low_d, high_d)
                        
                        next_target = final_targets[st.session_state.wa_idx]
                        next_n = next_target.get('name', 'Client')
                        next_p = next_target.get('phone', '')

                        c_title = "🛡️ استراحة دفعات بين الرسائل (حماية من الحظر)" if is_batch_break else f"⏳ انتظار عشوائي بين الرسائل ({wait_seconds} ثانية)"
                        if not is_ar:
                            c_title = "🛡️ Batch Break (Anti-Ban Protection)" if is_batch_break else f"⏳ Random Delay Between Messages ({wait_seconds}s)"
                        c_icon = "🛡️" if is_batch_break else "🎲"
                        c_border = "rgba(0, 229, 255, 0.4)" if is_batch_break else "rgba(0, 255, 136, 0.4)"
                        c_bg = "rgba(0, 229, 255, 0.06)" if is_batch_break else "rgba(0, 255, 136, 0.06)"
                        c_text = "#00E5FF" if is_batch_break else "#00FF88"

                        countdown_ph = st.empty()
                        for remaining in range(wait_seconds, 0, -1):
                            if not st.session_state.get('wa_running', False):
                                break
                            m, s = divmod(remaining, 60)
                            if m > 0:
                                time_display = f"{m:02d}:{s:02d} دقيقة" if is_ar else f"{m:02d}:{s:02d} min"
                            else:
                                time_display = f"{s} ثانية" if is_ar else f"{s} sec"

                            countdown_ph.markdown(f"""
                            <div style="background: {c_bg}; border: 1.5px solid {c_border}; border-radius: 16px; padding: 20px; text-align: center; margin: 15px 0; box-shadow: 0 0 25px rgba(0,0,0,0.3);">
                                <div style="color: {c_text}; font-size: 1.15rem; font-weight: 700; margin-bottom: 8px;">
                                    {c_icon} {c_title}
                                </div>
                                <div style="font-size: 2.6rem; font-weight: 800; color: #FFFFFF; font-family: 'Courier New', monospace; letter-spacing: 2px; text-shadow: 0 0 15px {c_text};">
                                    {time_display}
                                </div>
                                <div style="color: #bbb; font-size: 0.9rem; margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 8px;">
                                    👤 {'الرقم التالي' if is_ar else 'Next'}: <strong>{next_n}</strong> · 📱 <span style="font-family: monospace;">{next_p}</span> · ({st.session_state.wa_idx} / {total_targets})
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            time.sleep(1)
                        
                        countdown_ph.empty()
                        if st.session_state.get('wa_running', False):
                            st.rerun()

            else:
                st.session_state.wa_running = False
                st.session_state.wa_done = True
                st.rerun()

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
