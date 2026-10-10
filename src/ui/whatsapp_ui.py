import streamlit as st
import pandas as pd
import json
import os
import re
import html
import time
from datetime import datetime, timedelta
# WhatsAppService is imported lazily inside render_whatsapp_page() to avoid blocking app startup with selenium
from src.utils.phone_utils import validate_numbers, format_phone_number, save_to_local_desktop, render_pasha_export_button
from src.core.i18n import t
from src.config import WA_HISTORY_FILE, WA_TEMPLATES_FILE
from src.ui.styles import get_base64_image
import random

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


def _find_df_col(columns, keys):
    for c in columns:
        cl = str(c).lower()
        if any(k.lower() in cl for k in keys):
            return c
    return None


def _dedup_workers_by_iqama_keep_newest(df):
    """حذف المكرر من رقم الإقامة مع الاحتفاظ بالأحدث بتاريخ التسجيل.

    Returns: (deduped_df, removed_count, iqama_col, ts_col)
    - يبحث عن عمود رقم الإقامة (ويستبعد عمود المهنة في الإقامة).
    - يرتب حسب تاريخ التسجيل/الطابع الزمني تنازلياً (الأحدث أولاً) ثم يحذف المكرر.
    - الصفوف بدون رقم إقامة صالح تُترك كما هي ولا تُحذف.
    """
    import re as _re

    if df is None or getattr(df, "empty", True):
        return df, 0, None, None

    cols = list(df.columns)

    # 1) إيجاد عمود رقم الإقامة — مع استبعاد عمود المهنة في الإقامة
    exclude_kw = ["مهنة", "مهنه", "profession", "occupation", "listed on", "job"]
    iqama_candidates = []
    for c in cols:
        cl = str(c).lower().strip()
        if str(c).startswith("__"):
            continue
        has_iqama = any(k in cl for k in ["رقم الاقامة", "رقم الإقامة", "iqama id", "iqama", "residency", "national id", "رقم الهوية", "باسبورد"])
        if has_iqama and not any(x in cl for x in exclude_kw):
            iqama_candidates.append(c)
    # الأفضل: عمود يحتوي صراحة "رقم" أولاً
    iqama_col = None
    for c in iqama_candidates:
        if "رقم" in str(c):
            iqama_col = c
            break
    if iqama_col is None and iqama_candidates:
        iqama_col = iqama_candidates[0]
    if iqama_col is None:
        return df, 0, None, None

    # 2) إيجاد عمود تاريخ التسجيل / الطابع الزمني
    ts_keys = ["طابع زمني", "تاريخ التسجيل", "وقت التسجيل", "timestamp", "registration date", "تاريخ التقديم", "date submitted"]
    ts_col = _find_df_col(cols, ts_keys)
    # احتياط: أي عمود فيه timestamp وما يبدأ بـ __
    if ts_col is None:
        for c in cols:
            if str(c).startswith("__"):
                continue
            if "timestamp" in str(c).lower():
                ts_col = c
                break

    # 3) تطبيع رقم الإقامة: تحويل الأرقام العربية + إبقاء الأرقام فقط
    ar_to_west = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

    def _norm_iqama(v):
        if v is None:
            return ""
        try:
            import pandas as _pd
            if _pd.isna(v):
                return ""
        except Exception:
            pass
        s = str(v).translate(ar_to_west).strip()
        if not s or s.lower() == "nan":
            return ""
        digits = _re.sub(r'\D', '', s)
        return digits

    work = df.copy()
    work["__iqama_norm"] = work[iqama_col].apply(_norm_iqama)
    # الصفوف الفارغة تبقى كما هي (لا تعتبر مكررة)
    valid_mask = work["__iqama_norm"].astype(str).str.len() > 0
    valid_df = work[valid_mask].copy()
    empty_df = work[~valid_mask].copy()
    if valid_df.empty:
        return df, 0, iqama_col, ts_col

    # 4) تحليل تاريخ التسجيل
    def _parse_ts(v):
        try:
            import pandas as _pd
            if v is None:
                return _pd.NaT
            s = str(v).translate(ar_to_west).strip()
            if not s or s.lower() == "nan":
                return _pd.NaT
            if 'ص' in s or 'م' in s:
                marker = 'AM' if 'ص' in s else 'PM'
                s = _re.sub(r'[صم]', '', s).strip() + " " + marker
            try:
                from dateutil import parser as _parser
                return _pd.Timestamp(_parser.parse(s, dayfirst=False))
            except Exception:
                return _pd.to_datetime(s, errors='coerce')
        except Exception:
            try:
                import pandas as _pd2
                return _pd2.NaT
            except Exception:
                return None

    if ts_col is not None and ts_col in valid_df.columns:
        valid_df["__ts_parsed"] = valid_df[ts_col].apply(_parse_ts)
        # الأحدث أولاً (NaT في الأخير)، ثم حذف المكرر مع إبقاء الأول = الأحدث
        valid_df = valid_df.sort_values(by="__ts_parsed", ascending=False, kind="mergesort")
        before = len(valid_df)
        valid_df = valid_df.drop_duplicates(subset=["__iqama_norm"], keep="first")
        removed = before - len(valid_df)
        valid_df = valid_df.drop(columns=["__ts_parsed"], errors="ignore")
    else:
        before = len(valid_df)
        valid_df = valid_df.drop_duplicates(subset=["__iqama_norm"], keep="first")
        removed = before - len(valid_df)

    valid_df = valid_df.drop(columns=["__iqama_norm"], errors="ignore")
    empty_df = empty_df.drop(columns=["__iqama_norm"], errors="ignore")

    # نعيد الدمج: النتائج المعالجة (الأحدث أولاً) + الصفوف بدون إقامة
    deduped = pd.concat([valid_df, empty_df], ignore_index=False)
    # إسقاط أي أعمدة مؤقتة متبقية
    deduped = deduped.drop(columns=[c for c in ["__iqama_norm", "__ts_parsed"] if c in deduped.columns], errors="ignore")
    return deduped, int(removed), iqama_col, ts_col


def _sort_df_by_registration_newest(df, ts_col_hint=None):
    """ترتيب دائم: الأحدث بتاريخ التسجيل أولاً (والفارغ/غير الصالح في الأخير)."""
    import re as _re2
    if df is None or getattr(df, "empty", True):
        return df
    cols = list(df.columns)
    ts_col = ts_col_hint if (ts_col_hint is not None and ts_col_hint in cols) else None
    if ts_col is None:
        ts_col = _find_df_col(cols, ["طابع زمني", "تاريخ التسجيل", "وقت التسجيل", "timestamp", "registration date", "تاريخ التقديم", "date submitted"])
        if ts_col is None:
            for _c in cols:
                if str(_c).startswith("__"):
                    continue
                if "timestamp" in str(_c).lower():
                    ts_col = _c
                    break
    if ts_col is None:
        return df
    _ar2w = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

    def _p(v):
        try:
            import pandas as _pd
            if v is None:
                return _pd.NaT
            s = str(v).translate(_ar2w).strip()
            if not s or s.lower() == "nan":
                return _pd.NaT
            if 'ص' in s or 'م' in s:
                mk = 'AM' if 'ص' in s else 'PM'
                s = _re2.sub(r'[صم]', '', s).strip() + " " + mk
            try:
                from dateutil import parser as _prs
                return _pd.Timestamp(_prs.parse(s, dayfirst=False))
            except Exception:
                return _pd.to_datetime(s, errors='coerce')
        except Exception:
            try:
                import pandas as _pd2
                return _pd2.NaT
            except Exception:
                return None

    try:
        _tmp = df[ts_col].apply(_p)
        out = df.copy()
        out["__reg_sort"] = _tmp
        out = out.sort_values(by="__reg_sort", ascending=False, kind="mergesort", na_position="last")
        return out.drop(columns=["__reg_sort"], errors="ignore")
    except Exception:
        return df


def _wa_format_reg_date(v):
    """تنسيق تاريخ التسجيل بصيغة YYYY-MM-DD للعرض."""
    if v is None:
        return ""
    try:
        import pandas as _pd
        if _pd.isna(v):
            return ""
    except Exception:
        pass
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return ""
    try:
        _ar2w = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        s2 = s.translate(_ar2w)
        import re as _rx
        s2 = _rx.sub(r'[صم]', '', s2).strip()
        from dateutil import parser as _prs
        return _prs.parse(s2, dayfirst=False).strftime('%Y-%m-%d')
    except Exception:
        try:
            import pandas as _pd2
            _dt = _pd2.to_datetime(s, errors='coerce')
            if _pd2.isna(_dt):
                return s
            return _dt.strftime('%Y-%m-%d')
        except Exception:
            return s


# خريطة الأعلام محلياً (نسخة من الجدول الشامل في app.py — بدون استيراده لتفادي إعادة
# تنفيذ app.py كاملاً داخل العرض والذي كان يسبب فراغاً كبيراً وبطئاً في الجدول).
_WA_FLAG_MAP = {
    "هندي": "in", "هنديه": "in", "الهند": "in", "هند": "in",
    "فلبيني": "ph", "فلبينيه": "ph", "الفلبين": "ph", "فلبين": "ph",
    "نيبالي": "np", "نيباليه": "np", "نيبال": "np",
    "بنجلاديشي": "bd", "بنجاليه": "bd", "بنجلاديش": "bd", "بنقالي": "bd", "بنغالي": "bd", "بنغاليه": "bd", "بنجلادش": "bd",
    "باكستاني": "pk", "باكستانيه": "pk", "باكستان": "pk",
    "مصري": "eg", "مصريه": "eg", "مصر": "eg",
    "سوداني": "sd", "سودانيه": "sd", "السودان": "sd",
    "سيريلانكي": "lk", "سيريلانكيه": "lk", "سيريلانكا": "lk", "سيرلانكي": "lk", "سيرلانكيه": "lk",
    "كيني": "ke", "كينيه": "ke", "كينيا": "ke",
    "اوغندي": "ug", "اوغنديه": "ug", "اوغندا": "ug",
    "اثيوبي": "et", "اثيوبيه": "et", "اثيوبيا": "et",
    "مغربي": "ma", "مغربيه": "ma", "المغرب": "ma",
    "يمني": "ye", "يمنيه": "ye", "اليمن": "ye",
    "اندونيسي": "id", "اندونيسيه": "id", "اندونيسيا": "id", "اندونيسا": "id",
    "رواندي": "rw", "روانديه": "rw", "رواندا": "rw", "روندا": "rw", "روندي": "rw", "رونديه": "rw",
    "افغاني": "af", "افغانيه": "af", "افغانستان": "af", "افغان": "af",
    "نيجيري": "ng", "نيجيريه": "ng", "نيجيريا": "ng", "نيجريا": "ng", "نيجري": "ng", "نيجرية": "ng",
    "غاني": "gh", "غانيه": "gh", "غانا": "gh",
    "فيتنام": "vn", "فيتنامي": "vn", "فيتناميه": "vn",
    "سيراليون": "sl",
    "بوروندي": "bi",
    "indian": "in", "filipino": "ph", "filipina": "ph", "philippines": "ph", "nepi": "np", "nepali": "np", "nepal": "np",
    "bangla": "bd", "bangladeshi": "bd", "bangladesh": "bd", "pakistan": "pk", "pakistani": "pk",
    "egypt": "eg", "egyptian": "eg", "sudan": "sd", "sudanese": "sd",
    "sri lanka": "lk", "sri lankan": "lk", "srilankan": "lk", "kenya": "ke", "kenyan": "ke",
    "uganda": "ug", "ugandan": "ug", "ethiopia": "et", "ethiopian": "et",
    "indonesian": "id", "indonesia": "id", "rwandan": "rw", "rwanda": "rw",
    "afghan": "af", "afghanistan": "af", "nigerian": "ng", "nigeria": "ng",
    "ghanaian": "gh", "ghana": "gh", "vietnam": "vn", "vietnamese": "vn",
    "sierra leone": "sl", "burundi": "bi", "sierra leonean": "sl", "burundian": "bi",
    "saudi": "sa", "السعودية": "sa",
}
_WA_FLAG_SORTED = sorted(_WA_FLAG_MAP.items(), key=lambda x: len(x[0]), reverse=True)


def _wa_norm_ar(text):
    return (text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي"))


def _wa_flag_url(nat_val):
    """رابط علم الدولة — نفس منطق الجدول الشامل لكن محلياً (بدون استيراد app)."""
    if nat_val is None:
        return None
    try:
        import pandas as _pd
        if _pd.isna(nat_val):
            return None
    except Exception:
        pass
    s = str(nat_val).strip().lower()
    if not s or s == "nan":
        return None
    try:
        import re as _rx
        # إزالة ال التعريف + توحيد الهمزات (نفس app.py)
        if s.startswith("ال") and len(s) > 4:
            s = s[2:]
        s = _wa_norm_ar(s)
        for _k, _code in _WA_FLAG_SORTED:
            _nk = _wa_norm_ar(_k)
            if len(_nk) <= 3:
                if _rx.search(r'(?:^|[\s,:;.\-/])' + _rx.escape(_nk) + r'(?:[\s,:;.\-/]|$)', s):
                    return f"https://cdn.jsdelivr.net/gh/lipis/flag-icons@7.2.0/flags/4x3/{_code.lower()}.svg"
            elif _nk in s:
                return f"https://cdn.jsdelivr.net/gh/lipis/flag-icons@7.2.0/flags/4x3/{_code.lower()}.svg"
    except Exception:
        pass
    return None


def _wa_gender_label(v, is_ar=True):
    """تسمية الجنس مع الأيقونة كما في الجدول الشامل."""
    s = str(v).strip().lower() if v is not None else ""
    if s in ("female", "أنثى", "انثى", "انثي", "أنثي", "f", "🚺 female", "🚺 أنثى"):
        return ("🚺 أنثى" if is_ar else "🚺 Female")
    if s in ("male", "ذكر", "m", "🚹 male", "🚹 ذكر"):
        return ("🚹 ذكر" if is_ar else "🚹 Male")
    if "female" in s or "أنث" in s or "انث" in s:
        return ("🚺 أنثى" if is_ar else "🚺 Female")
    if "male" in s or "ذكر" in s:
        return ("🚹 ذكر" if is_ar else "🚹 Male")
    return str(v).strip() if v is not None else ""


def _worker_df_to_wa_targets(df, history_set):
    """Convert worker search results into WhatsApp send targets (name, phone, CV, row fields)."""
    targets = []
    seen = set()
    if df is None or getattr(df, "empty", True):
        return targets
    cols = list(df.columns)
    c_name = _find_df_col(cols, ["full name", "الاسم الكامل", "اسم العامل", "candidate name", "worker name"])
    if not c_name:
        c_name = _find_df_col(cols, ["name", "الاسم"])
    c_phone = _find_df_col(cols, ["whatsapp", "phone number", "mobile number", "رقم الجوال", "رقم الهاتف", "رقم الموبايل"])
    if not c_phone:
        c_phone = _find_df_col(cols, ["phone", "mobile", "جوال", "هاتف", "واتساب"])
    c_cv = _find_df_col(cols, ["download cv", "سيرة الذاتية", "resume", "cv"])

    for idx, row in df.iterrows():
        raw_p = str(row[c_phone]).strip() if c_phone and pd.notna(row[c_phone]) else ""
        phone = format_phone_number(raw_p)
        if not phone:
            phone = format_phone_number("".join(raw_p.split()))
        if not phone or phone in seen:
            continue
        seen.add(phone)
        target_data = {
            str(col): (str(row[col]).strip() if pd.notna(row[col]) else "")
            for col in cols
            if not str(col).startswith("__")
        }
        name = str(row[c_name]).strip() if c_name and pd.notna(row[c_name]) else "عامل"
        if not name or name.lower() == "nan":
            name = "عامل"
        cv = str(row[c_cv]).strip() if c_cv and pd.notna(row[c_cv]) else ""
        if cv.lower() == "nan":
            cv = ""
        target_data.update({
            "idx": idx,
            "phone": phone,
            "name": name,
            "cv": cv,
            "is_sent": phone in (history_set or set()),
        })
        targets.append(target_data)
    return targets


def _adopt_wa_worker_targets(targets):
    st.session_state.wa_from_worker_db = True
    st.session_state.wa_review_targets = targets
    st.session_state.wa_done = False
    st.session_state.wa_idx = 0
    st.session_state.wa_running = False

def render_whatsapp_page():
    from src.services.whatsapp_service import WhatsAppService
    from src.services.wa_worker_manager import WAWorkerManager
    from src.core.translation import TranslationManager
    lang = st.session_state.get('lang', 'ar')
    is_ar = lang == 'ar'
    is_cloud = "/mount/" in __file__

    # ── تهيئة TranslationManager ──
    if 'tm' not in st.session_state:
        try:
            st.session_state.tm = TranslationManager()
        except Exception as e:
            print(f"[ERROR] Failed to init TranslationManager: {e}")
            st.session_state.tm = None

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
    if 'wa_from_worker_db' not in st.session_state: st.session_state.wa_from_worker_db = False
    if 'wa_messages' not in st.session_state: st.session_state.wa_messages = [""]
    if 'wa_emp_targets' not in st.session_state: st.session_state.wa_emp_targets = []
    if 'wa_emp_running' not in st.session_state: st.session_state.wa_emp_running = False
    if 'wa_emp_idx' not in st.session_state: st.session_state.wa_emp_idx = 0

    st.markdown('<div class="programmer-signature-neon">By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)
    st.caption("build b1011c")

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
        'tab_db_search': "🔍 بحث في قاعدة بيانات العمال" if is_ar else "🔍 Search Workers Database",
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
        'wa_scan_msg': t('wa_scan_msg', lang),
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
             "بحث في قاعدة بيانات العملاء" if is_ar else "Search in Customer Database",
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
                            c_phone = "".join(filter(str.isdigit, raw_p))
                            if c_phone and len(c_phone) >= 8 and c_phone not in seen_phones:
                                seen_phones.add(c_phone)
                                extracted.append({'name': c_name if c_name != 'nan' else 'عميل', 'phone': c_phone, 'is_sent': False})
                        st.session_state.wa_emp_targets = extracted
                        st.toast(f"✅ تم استخراج {len(extracted)} عميل بنجاح")
                        st.rerun()
                except Exception as ex:
                    st.error(f"❌ {'خطأ في قراءة ملف الإكسل' if is_ar else 'Error reading Excel file'}: {str(ex)}")

        elif data_source == ("بحث في قاعدة بيانات العملاء" if is_ar else "Search in Customer Database"):
            from src.data.bengali_manager import BengaliDataManager
            from src.core.search import SmartSearchEngine

            # ── جلب البيانات من المصدرين ──────────────────────────────
            all_sys_records = []  # list of dicts: {name, phone, city, job, source, company, responsible, nationality, salary, nature}

            # 1) طلبات العملاء (Google Sheet) - مع المزيد من الحقول
            try:
                if hasattr(st.session_state, 'db') and st.session_state.db:
                    cust_df = st.session_state.db.fetch_customer_requests()
                    if cust_df is not None and not cust_df.empty:
                        cols = cust_df.columns.tolist()
                        # محاولة تحديد أعمدة الاسم، الجوال، المدينة، الوظيفة، إضافة المزيد من الحقول
                        def _find_col(keywords):
                            for kw in keywords:
                                for c in cols:
                                    if kw.lower() in str(c).lower():
                                        return c
                            return None
                        name_c  = _find_col(["اسم", "name", "شركة", "company", "عميل"])
                        phone_c = _find_col(["جوال", "موبايل", "تليفون", "هاتف", "phone", "mobile"])
                        city_c  = _find_col(["مدينة", "city", "منطقة", "location"])
                        job_c   = _find_col(["وظيفة", "مهنة", "طلب", "job", "category", "profession"])
                        company_c = _find_col(["شركة", "company", "مؤسس"])
                        responsible_c = _find_col(["مسؤول", "responsible"])
                        nationality_c = _find_col(["جنسي", "nationality"])
                        salary_c = _find_col(["راتب", "salary"])
                        nature_c = _find_col(["طبيعة", "nature"])
                        
                        for _, row in cust_df.iterrows():
                            r_name  = str(row[name_c]).strip()  if name_c  and pd.notna(row[name_c])  else "عميل"
                            r_phone = str(row[phone_c]).strip() if phone_c and pd.notna(row[phone_c]) else ""
                            r_city  = str(row[city_c]).strip()  if city_c  and pd.notna(row[city_c])  else ""
                            r_job   = str(row[job_c]).strip()   if job_c   and pd.notna(row[job_c])   else ""
                            r_company = str(row[company_c]).strip() if company_c and pd.notna(row[company_c]) else ""
                            r_responsible = str(row[responsible_c]).strip() if responsible_c and pd.notna(row[responsible_c]) else ""
                            r_nationality = str(row[nationality_c]).strip() if nationality_c and pd.notna(row[nationality_c]) else ""
                            r_salary = str(row[salary_c]).strip() if salary_c and pd.notna(row[salary_c]) else ""
                            r_nature = str(row[nature_c]).strip() if nature_c and pd.notna(row[nature_c]) else ""
                            r_phone_clean = "".join(filter(str.isdigit, r_phone))
                            if r_phone_clean and len(r_phone_clean) >= 8:
                                all_sys_records.append({
                                    'name': r_name if r_name not in ('', 'nan') else 'عميل',
                                    'phone': r_phone_clean,
                                    'city': r_city,
                                    'job': r_job,
                                    'source': '📋 طلبات العملاء',
                                    'company': r_company,
                                    'responsible': r_responsible,
                                    'nationality': r_nationality,
                                    'salary': r_salary,
                                    'nature': r_nature
                                })
            except Exception as _ce:
                st.warning(f"⚠️ تعذّر جلب طلبات العملاء: {_ce}")

            # 2) Bengali Supply - مع المزيد من الحقول
            try:
                bm = BengaliDataManager()
                for e in (bm.get_employers() or []):
                    raw_p = "".join(filter(str.isdigit, str(e.get('mobile', ''))))
                    if raw_p and len(raw_p) >= 8:
                        all_sys_records.append({
                            'name': str(e.get('name', 'عميل')).strip(),
                            'phone': raw_p,
                            'city': str(e.get('city', '')).strip(),
                            'job': str(e.get('cafe', '')).strip(),
                            'source': '🏢 Bengali Supply',
                            'company': str(e.get('cafe', '')).strip(),
                            'responsible': '',
                            'nationality': '',
                            'salary': '',
                            'nature': ''
                        })
            except Exception as _be:
                st.warning(f"⚠️ تعذّر جلب Bengali Supply: {_be}")

            if not all_sys_records:
                st.warning("⚠️ لا توجد بيانات في النظام حالياً")
            else:
                # ── عرض عينة من البيانات للتحقق (Debug) ──────────────────────────────
                with st.expander("🔍 عينة من البيانات (للتأكد من المحتوى)", expanded=False):
                    sample_df = pd.DataFrame(all_sys_records[:5])
                    st.dataframe(sample_df)
                
                # ─ـ تحويل البيانات إلى DataFrame لاستخدام SmartSearchEngine ──────────────────────────────
                sys_df = pd.DataFrame(all_sys_records)
                
                # ── خانة البحث ────────────────────────────────────────
                st.markdown(f"**📊 إجمالي السجلات:** {len(all_sys_records)} سجل")
                search_q = st.text_input(
                    "🔍 ابحث بالاسم، رقم الجوال، المدينة، المهنة، الشركة، المسؤول، الجنسية، الراتب، الكوفي...",
                    key="wa_sys_search_box",
                    placeholder="مثال: محمد  أو  0501234567  أو  الرياض  أو  مطعم  أو  Barista"
                )

                # ── تصفية النتائج باستخدام TranslationManager (مثل معالجة الطلبات) ─────────────────────────────────────
                if search_q and search_q.strip():
                    from src.core.translation import TranslationManager
                    
                    def _normalize_phone(text):
                        """تطبيع رقم الهاتف"""
                        arabic_to_western = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
                        s = str(text).translate(arabic_to_western)
                        digits = re.sub(r'\D', '', s)
                        if not digits: return ""
                        if digits.startswith('00'): digits = digits[2:]
                        if digits.startswith('966'): digits = digits[3:]
                        while digits.startswith('0'): digits = digits[1:]
                        return digits

                    def _is_phone_query(q):
                        """التحقق مما إذا كان البحث رقم هاتف"""
                        arabic_to_western = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
                        clean = re.sub(r'[\s\+\-\(\)]', '', str(q)).translate(arabic_to_western)
                        return clean.isdigit() and len(clean) >= 5

                    is_phone_search = _is_phone_query(search_q)
                    
                    if is_phone_search:
                        # البحث برقم الهاتف
                        q_phone = _normalize_phone(search_q)
                        filtered = [
                            r for r in all_sys_records
                            if q_phone and q_phone in _normalize_phone(r['phone'])
                        ]
                    else:
                        # استخدام TranslationManager للبحث ثنائي اللغة
                        tm = st.session_state.get('tm')
                        
                        # تحليل الاستعلام للحصول على المرادفات
                        query_bundles = tm.analyze_query(search_q) if tm else [[search_q.lower()]]
                        
                        # Debug: عرض المرادفات للتحقق
                        with st.expander("🔍 تفاصيل تحليل البحث (Debug)", expanded=False):
                            st.write(f"كلمات البحث: {search_q}")
                            st.write(f"المرادفات المحللة: {query_bundles}")
                            st.write(f"عدد السجلات الكلي: {len(all_sys_records)}")
                        
                        filtered = []
                        for r in all_sys_records:
                            # تجميع جميع الحقول في نص واحد للبحث (مثل معالجة الطلبات)
                            search_text = " ".join([
                                r['name'],
                                r['phone'],
                                r['city'],
                                r['job'],
                                r['source'],
                                r.get('company', ''),
                                r.get('responsible', ''),
                                r.get('nationality', ''),
                                r.get('salary', ''),
                                r.get('nature', '')
                            ]).lower()
                            
                            # منطق AND بين جميع الكلمات (مثل معالجة الطلبات)
                            match_all_words = True
                            for bundle in query_bundles:
                                found_synonym = False
                                for syn in bundle:
                                    if syn.lower() in search_text:
                                        found_synonym = True
                                        break
                                if not found_synonym:
                                    match_all_words = False
                                    break
                            
                            if match_all_words:
                                filtered.append(r)
                    
                    if not filtered:
                        st.warning(f"⚠️ لا توجد نتائج مطابقة لجميع كلمات البحث: \"{search_q}\"")
                        st.info("💡 نصيحة: جرب البحث بكلمات أقل أو استخدم كلمات عامة")
                else:
                    filtered = all_sys_records

                st.markdown(f"**🔎 نتائج البحث:** {len(filtered)} سجل")

                if not filtered:
                    pass  # تم عرض الرسالة أعلاه
                else:
                    # ── عرض النتائج كجدول قابل للاختيار ─────────────
                    # بناء DataFrame للعرض مع جميع البيانات
                    display_rows = []
                    for i, r in enumerate(filtered):
                        display_rows.append({
                            '#': i + 1,
                            'الاسم': r['name'],
                            '📱 رقم التليفون': r['phone'],
                            'المدينة': r['city'],
                            'المهنة / النشاط': r['job'],
                            'المصدر': r['source'],
                            'الشركة': r.get('company', ''),
                            'المسؤول': r.get('responsible', ''),
                            'الجنسية': r.get('nationality', ''),
                            'الراتب': r.get('salary', ''),
                            'طبيعة العمل': r.get('nature', ''),
                        })
                    disp_df = pd.DataFrame(display_rows)

                    # multiselect باستخدام options مبسطة (الاسم + رقم الهاتف)
                    options_list = [
                        f"{r['name']} | 📱 {r['phone']} | {r['city']} | {r['source']}"
                        for r in filtered
                    ]

                    # إظهار الجدول للمعاينة مع العنوان
                    st.markdown("### 📊 جدول نتائج البحث الشامل")
                    st.dataframe(
                        disp_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            '#': st.column_config.NumberColumn('#', width='small'),
                            'الاسم': st.column_config.TextColumn('الاسم', width='medium'),
                            '📱 رقم التليفون': st.column_config.TextColumn('📱 رقم التليفون', width='medium'),
                            'المدينة': st.column_config.TextColumn('المدينة', width='medium'),
                            'المهنة / النشاط': st.column_config.TextColumn('المهنة / النشاط', width='medium'),
                            'المصدر': st.column_config.TextColumn('المصدر', width='medium'),
                            'الشركة': st.column_config.TextColumn('الشركة', width='medium'),
                            'المسؤول': st.column_config.TextColumn('المسؤول', width='medium'),
                            'الجنسية': st.column_config.TextColumn('الجنسية', width='medium'),
                            'الراتب': st.column_config.TextColumn('الراتب', width='small'),
                            'طبيعة العمل': st.column_config.TextColumn('طبيعة العمل', width='medium'),
                        }
                    )

                    st.markdown("**اختر السجلات للإضافة:**")
                    selected_sys = st.multiselect(
                        "✅ حدد العملاء المراد إرسالهم",
                        options=options_list,
                        default=options_list,
                        key="wa_emp_sys_multiselect_new",
                        format_func=lambda x: x
                    )

                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button(
                            f"📥 اعتماد المحددين ({len(selected_sys)})",
                            type="primary",
                            key="btn_load_sys_selected",
                            use_container_width=True
                        ):
                            extracted = []
                            seen_phones = set()
                            for opt in selected_sys:
                                # استخراج رقم الهاتف من الخيار
                                try:
                                    parts = opt.split('|')
                                    raw_name = parts[0].strip()
                                    raw_phone = parts[1].replace('📱', '').strip() if len(parts) > 1 else ''
                                    c_phone = "".join(filter(str.isdigit, raw_phone))
                                    if c_phone and len(c_phone) >= 8 and c_phone not in seen_phones:
                                        seen_phones.add(c_phone)
                                        extracted.append({'name': raw_name, 'phone': c_phone, 'is_sent': False})
                                except Exception:
                                    pass
                            st.session_state.wa_emp_targets = extracted
                            st.toast(f"✅ تم اعتماد {len(extracted)} عميل")
                            st.rerun()
                    with btn_col2:
                        if st.button(
                            f"⚡ اعتماد كافة نتائج البحث ({len(filtered)})",
                            key="btn_load_sys_all_filtered",
                            use_container_width=True
                        ):
                            extracted = []
                            seen_phones = set()
                            for r in filtered:
                                if r['phone'] not in seen_phones:
                                    seen_phones.add(r['phone'])
                                    extracted.append({'name': r['name'], 'phone': r['phone'], 'is_sent': False})
                            st.session_state.wa_emp_targets = extracted
                            st.toast(f"✅ تم اعتماد كافة {len(extracted)} نتيجة بحث")
                            st.rerun()

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
                        if st.button("❌", key=f"del_emp_trg_{idx_t}", help="حذف من القائمة"):
                            st.session_state.wa_emp_targets.pop(idx_t)
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

            # 👀 معاينة حية كما ستظهر في واتساب: رسالة واحدة (المتن + التوقيع)
            try:
                _pv = emp_message.replace("{Name}", "مثال").replace("{name}", "مثال").replace("{الاسم}", "مثال")
                _pv = _pv.replace("\u202A", "").replace("\u202C", "").replace("\u2066", "").replace("\u2069", "")
                _m = re.search(
                    r'\n*((?:مع خالص التحية والتقدير|مع جزيل الشكر والتقدير|مع أطيب التحيات|مع فائق الاحترام|مع فائق الاحترام والتقدير|مع الفائق الاحترام والتقدير|مع خالص التقدير والاحترام|شاكرين ومقدرين|دمتم بخير)[،,]?\nأبو فهد\nHR)\s*$',
                    _pv,
                )
                if not _m and _pv.strip():
                    _pv = _pv.rstrip() + "\n\nمع خالص التحية والتقدير،\nأبو فهد\nHR"
                _bh = "<br>".join(html.escape(_pv).split("\n"))
                st.markdown(
                    f"""<div style="background:#0b141a; border:1px solid rgba(255,255,255,0.12); border-radius:12px; padding:14px 16px; margin:6px 0 2px 0;">
<div style="background:#005c4b; color:#e7ffdb; border-radius:8px; padding:10px 12px; font-size:0.92rem; line-height:1.9;">
<div dir="rtl" style="text-align:right;">{_bh}</div></div>
<div style="color:rgba(255,255,255,0.45); font-size:0.72rem; margin-top:6px;">{"👁️ رسالة واحدة كما ستصل في واتساب" if is_ar else "👁️ Single message as delivered in WhatsApp"}</div></div>""",
                    unsafe_allow_html=True,
                )
            except Exception:
                pass

            # 📎 مرفقات الرسالة للعملاء (PDF / فيديوهات / صور)
            st.markdown("---")
            st.markdown(f"#### 📎 {'مرفقات الرسالة للعملاء (PDF / فيديوهات / صور)' if is_ar else 'Customer Attachments (PDF / Videos / Photos)'}")
            st.caption("💡 يمكنك رفع ملفات PDF، مقاطع فيديو (MP4/MOV)، وصور (JPG/PNG) لإرسالها كمرفقات مع الرسالة المخصصة لكل عميل.")

            # قائمة منسدلة لاختيار نوع المرفق - زر واحد فقط
            att_type = st.selectbox(
                "📎 " + ("BROWSE files" if is_ar else "BROWSE files"),
                options=[
                    "📄 " + ("مستند" if is_ar else "Document"),
                    "🖼️ " + ("الصور ومقاطع الفيديو" if is_ar else "Images & Videos"),
                    "🎵 " + ("الصوت" if is_ar else "Audio")
                ],
                key="wa_emp_att_type_select"
            )

            emp_uploaded_files = []
            
            # تحديد أنواع الملفات حسب الاختيار
            if "مستند" in att_type or "Document" in att_type:
                emp_uploaded_files = st.file_uploader(
                    "📄 " + ("اختر المستندات (PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT)" if is_ar else "Select documents (PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT)"),
                    type=["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt"],
                    accept_multiple_files=True,
                    key="wa_emp_files_uploader_doc"
                )
            elif "الصور" in att_type or "Images" in att_type:
                emp_uploaded_files = st.file_uploader(
                    "🖼️ " + ("اختر الصور ومقاطع الفيديو (JPG, PNG, MP4, MOV, AVI, MKV)" if is_ar else "Select images & videos (JPG, PNG, MP4, MOV, AVI, MKV)"),
                    type=["png", "jpg", "jpeg", "webp", "gif", "mp4", "mov", "avi", "mkv", "webm"],
                    accept_multiple_files=True,
                    key="wa_emp_files_uploader_media"
                )
            elif "الصوت" in att_type or "Audio" in att_type:
                emp_uploaded_files = st.file_uploader(
                    "🎵 " + ("اختر الملفات الصوتية (MP3, WAV, M4A, OGG, AAC)" if is_ar else "Select audio files (MP3, WAV, M4A, OGG, AAC)"),
                    type=["mp3", "wav", "m4a", "ogg", "aac"],
                    accept_multiple_files=True,
                    key="wa_emp_files_uploader_audio"
                )

            # معالجة وحفظ المرفقات في مجلد مؤقت للجلسة
            emp_saved_attachments = st.session_state.get('wa_emp_saved_attachments', [])
            
            # عرض المرفقات المحفوظة مع إمكانية الحذف
            if emp_saved_attachments:
                st.markdown(f"**📎 {'المرفقات المحفوظة:' if is_ar else 'Saved Attachments:'}** ({len(emp_saved_attachments)})")
                for idx, att_path in enumerate(emp_saved_attachments):
                    col_att1, col_att2 = st.columns([4, 1])
                    with col_att1:
                        file_name = os.path.basename(att_path)
                        file_ext = os.path.splitext(file_name)[1].lower()
                        if file_ext == '.pdf':
                            icon = "📄"
                        elif file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.3gp']:
                            icon = "🎥"
                        elif file_ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp']:
                            icon = "🖼️"
                        elif file_ext in ['.mp3', '.wav', '.ogg']:
                            icon = "🎵"
                        else:
                            icon = "📎"
                        st.markdown(f"{icon} **{file_name}**")
                    with col_att2:
                        if st.button("❌", key=f"del_emp_att_{idx}", help="حذف المرفق"):
                            emp_saved_attachments.pop(idx)
                            st.session_state.wa_emp_saved_attachments = emp_saved_attachments
                            st.rerun()
            
            # معالجة الملفات المرفوعة حديثاً
            if emp_uploaded_files:
                base_dir = os.path.join(os.getcwd(), "whatsapp_session")
                if not os.path.exists(base_dir):
                    base_dir_alt = os.path.join(os.getcwd(), ".whatsapp_session")
                    if os.path.exists(base_dir_alt):
                        base_dir = base_dir_alt
                emp_uploads_dir = os.path.join(base_dir, "emp_temp_uploads")
                os.makedirs(emp_uploads_dir, exist_ok=True)

                total_size_bytes = 0
                st.markdown("<div style='margin: 8px 0;'>", unsafe_allow_html=True)
                for f in emp_uploaded_files:
                    total_size_bytes += f.size
                    file_ext = os.path.splitext(f.name)[1].lower()
                    if file_ext == '.pdf':
                        icon = "📄 [PDF]"
                    elif file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.3gp']:
                        icon = "🎥 [فيديو]"
                    elif file_ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp']:
                        icon = "🖼️ [صورة]"
                    elif file_ext in ['.mp3', '.wav', '.ogg']:
                        icon = "🎵 [صوت]"
                    else:
                        icon = "📎 [مستند]"

                    sz_str = f"{f.size / (1024*1024):.2f} MB" if f.size >= 1024*1024 else f"{f.size / 1024:.1f} KB"
                    st.markdown(
                        f"<div style='background: rgba(0, 229, 255, 0.08); border: 1px solid rgba(0, 229, 255, 0.3); border-radius: 8px; padding: 6px 12px; margin-bottom: 5px; display: inline-block; margin-inline-end: 8px;'>"
                        f"<b>{icon}</b> {f.name} <span style='color: #00E5FF;'>({sz_str})</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    # حفظ الملف محلياً
                    save_path = os.path.join(emp_uploads_dir, f.name)
                    try:
                        with open(save_path, "wb") as out_f:
                            out_f.write(f.getbuffer())
                        if save_path not in emp_saved_attachments:
                            emp_saved_attachments.append(save_path)
                    except Exception as err:
                        st.error(f"❌ خطأ في حفظ المرفق {f.name}: {err}")
                st.markdown("</div>", unsafe_allow_html=True)
                st.session_state.wa_emp_saved_attachments = emp_saved_attachments

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
            
            # إضافة وضع الإرسال (Presets)
            preset_mode = st.radio(
                "وضع الإرسال" if is_ar else "Sending Mode",
                ["🛡️ آمن (موصى به)", "⚡ سريع", "⚖️ متوازن"],
                horizontal=True,
                key="emp_preset_mode"
            )
            
            if preset_mode == "🛡️ آمن (موصى به)":
                def_min, def_max = 45, 90
                def_break, def_pause = 8, 4
            elif preset_mode == "⚡ سريع":
                def_min, def_max = 25, 45
                def_break, def_pause = 15, 3
            else:  # متوازن
                def_min, def_max = 30, 60
                def_break, def_pause = 10, 3
            
            # تعديل القيم حسب المرفقات
            if has_attachments:
                def_min = max(def_min, 45)
                def_max = max(def_max, 90)
                def_break = max(def_break, 8)
                def_pause = max(def_pause, 4)
            
            c_d1, c_d2, c_d3, c_d4 = st.columns(4)
            with c_d1:
                min_allowed = 20
                emp_min_delay = st.number_input(
                    "أدنى تأخير (ثانية)" if is_ar else "Min delay (s)",
                    min_value=min_allowed, max_value=300, value=def_min,
                    help="الحد الأدنى الآمن للانتظار بين كل رسالة (أعلى عند إرسال المرفقات لحماية الرقم)",
                    key="emp_min_delay_val"
                )
            with c_d2:
                min_max_allowed = max(emp_min_delay + 5, 25)
                emp_max_delay = st.number_input(
                    "أقصى تأخير (ثانية)" if is_ar else "Max delay (s)",
                    min_value=min_max_allowed, max_value=600, value=max(def_max, min_max_allowed),
                    help="الحد الأقصى للتأخير العشوائي بين الرسائل (لمحاكاة السلوك البشري الطبيعي)",
                    key="emp_max_delay_val"
                )
            with c_d3:
                emp_batch_break = st.number_input(
                    "استراحة كل (رسائل)" if is_ar else "Pause every (msgs)",
                    min_value=3, max_value=50, value=def_break,
                    help="التوقف لأخذ استراحة أمان لمحاكاة السلوك البشري الطبيعي",
                    key="emp_batch_break_val"
                )
            with c_d4:
                emp_batch_pause_mins = st.number_input(
                    "مدة الاستراحة (دقائق)" if is_ar else "Pause duration (min)",
                    min_value=2, max_value=20, value=def_pause,
                    help="مدة الاستراحة الأمنية بين الدفعات",
                    key="emp_batch_pause_mins"
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
                targets_to_send = st.session_state.wa_emp_targets
                total_t = len(targets_to_send)
                curr_idx = st.session_state.get('wa_emp_idx', 0)

                # البحث عن أول رقم لم يتم إرساله بدءاً من curr_idx
                while curr_idx < total_t and targets_to_send[curr_idx].get('is_sent', False):
                    curr_idx += 1
                st.session_state.wa_emp_idx = curr_idx

                if curr_idx >= total_t:
                    st.session_state.wa_emp_running = False
                    st.balloons()
                    st.success("🎉 " + ("اكتمل إرسال الرسائل والمرفقات لجميع العملاء بنجاح!" if is_ar else "All customer messages & attachments sent!"))
                    time.sleep(1)
                    st.rerun()
                else:
                    current_client = targets_to_send[curr_idx]
                    c_name = current_client.get('name', 'عميل')
                    c_phone = current_client.get('phone', '')
                    saved_attachments = st.session_state.get('wa_emp_saved_attachments', [])

                    # بطاقة حالة الإرسال المباشرة مع تفاصيل المرفقات
                    st.progress((curr_idx + 1) / total_t)
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
                            <span style="color: #00FF88; font-weight: 700; font-size: 1.05rem;">📤 {'جاري الإرسال للعميل' if is_ar else 'Sending to'}: {curr_idx + 1} / {total_t}</span>
                            <span style="color: #D4AF37; font-weight: 700; font-size: 1.05rem;">⌛ {'متبقٍ' if is_ar else 'Remaining'}: {total_t - (curr_idx + 1)}</span>
                        </div>
                        <div style="color: #FFFFFF; font-size: 0.95rem;">
                            👤 <strong>{c_name}</strong> · 📱 <span style="font-family: monospace; color: #00FF88;">{c_phone}</span>
                        </div>
                        {att_info_html}
                    </div>
                    """, unsafe_allow_html=True)

                    # تجهيز نص الرسالة وتخصيصه للعميل — رسالة واحدة (المتن + التوقيع)
                    personalized_msg = emp_message.replace("{Name}", c_name).replace("{name}", c_name).replace("{الاسم}", c_name)
                    personalized_msg = personalized_msg.replace("\u202A", "").replace("\u202C", "").replace("\u2066", "").replace("\u2069", "")
                    _has_sig = re.search(
                        r'(?:مع خالص التحية والتقدير|مع جزيل الشكر والتقدير|مع أطيب التحيات|مع فائق الاحترام|مع فائق الاحترام والتقدير|مع الفائق الاحترام والتقدير|مع خالص التقدير والاحترام|شاكرين ومقدرين|دمتم بخير)[،,]?\nأبو فهد\nHR',
                        personalized_msg,
                    )
                    if not _has_sig and personalized_msg.strip():
                        personalized_msg = personalized_msg.rstrip() + "\n\nمع خالص التحية والتقدير،\nأبو فهد\nHR"

                    # إرسال الرسالة والمرفقات عبر محرك واتساب
                    spin_text = f"🚀 {'جاري إرسال الرسالة والمرفقات إلى' if is_ar else 'Sending message & attachments to'} {c_name} ({c_phone})..." if saved_attachments else f"🚀 {'جاري الإرسال إلى' if is_ar else 'Sending to'} {c_name} ({c_phone})..."
                    import inspect as _insp
                    try:
                        _vg = "verbatim" in _insp.signature(st.session_state.wa_service.send_message).parameters
                    except Exception:
                        _vg = False
                    _vkw = {"verbatim": True} if _vg else {}

                    # التحقق من حالة الخدمة قبل الإرسال
                    if not st.session_state.wa_service or not getattr(st.session_state.wa_service, 'driver', None):
                        ok_send = False
                        log_detail = "محرك واتساب غير متصل (يرجى تشغيل المحرك أولاً)"
                        st.error("❌ محرك واتساب غير متصل! يرجى الضغط على 'Start Engine' أولاً")
                    else:
                        with st.spinner(spin_text):
                            ok_send, log_detail = st.session_state.wa_service.send_message(
                                c_phone,
                                personalized_msg,
                                attachment_path=saved_attachments if saved_attachments else None,
                                **_vkw,
                            )

                    # تسجيل النتيجة في سجل الإرسال العام مع تفاصيل المرفقات
                    att_summary = f" (مع {len(saved_attachments)} مرفق)" if (saved_attachments and ok_send) else ""
                    att_status = "تم الإرسال" if ok_send else "فشل الإرسال"
                    log_entry = {
                        "idx": curr_idx + 1,
                        "name": c_name,
                        "phone": c_phone,
                        "status": f"{log_detail}{att_summary}" if ok_send else f"فشل ({log_detail})",
                        "ok": ok_send,
                        "attachments_count": len(saved_attachments) if saved_attachments else 0,
                        "attachments_status": att_status,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.wa_logs.append(log_entry)

                    if ok_send:
                        st.session_state.wa_emp_targets[curr_idx]['is_sent'] = True
                        st.session_state.wa_history.add(c_phone)
                        save_wa_history(st.session_state.wa_history)

                    # 🛡️ إيقاف فوري إذا كان خطأ أمان لحماية الحساب من الحظر
                    if not ok_send and str(log_detail).startswith("🛑"):
                        st.session_state.wa_emp_running = False
                        st.error(f"🛑 {log_detail}")
                        st.toast("🛑 تم إيقاف الإرسال لحماية الحساب من الحظر", icon="⚠️")
                    else:
                        st.session_state.wa_emp_idx = curr_idx + 1
                        
                        # حساب التأخير العشوائي الذكي بين الرسائل (حماية الحساب ضد الحظر)
                        if st.session_state.wa_emp_idx < total_t:
                            # فحص استراحة الدفعات
                            is_break = (emp_batch_break > 0 and st.session_state.wa_emp_idx % emp_batch_break == 0)
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
                    att_count = entry.get('attachments_count', 0)
                    att_status = entry.get('attachments_status', '')
                    att_info = f" | 📎 {att_count} مرفق ({att_status})" if att_count > 0 else ""
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
                            <div class="log-attachments">
                                <span style="color: #bbb; font-size: 0.85rem;">{att_info}</span>
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

            t_manual, t_xl, t_db = st.tabs([lbl['tab_manual'], lbl['tab_excel'], lbl['tab_db_search']])
            
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

            with t_db:
                from src.core.search import SmartSearchEngine

                st.markdown("#### 🔍 " + ("بحث في قاعدة بيانات العمال" if is_ar else "Search Workers Database"))
                st.caption(
                    "نفس محرك البحث الذكي للعمال — ثم اعتماد النتائج لإرسالها عبر واتساب."
                    if is_ar else
                    "Uses the same Smart Search engine as workers, then loads results for WhatsApp sending."
                )

                with st.expander(t("advanced_filters", lang), expanded=False):
                    st.markdown(f"📅 {t('filter_dates_group', lang)}")
                    fc1, fc2, fc3 = st.columns(3)
                    with fc1:
                        wa_use_age = st.checkbox(("تفعيل " if is_ar else "Enable ") + t("age", lang), key="wa_wrk_use_age")
                        if wa_use_age:
                            wa_age_min = st.number_input("من سن" if is_ar else "From", 1, 100, 16, key="wa_wrk_age_min")
                            wa_age_max = st.number_input("إلى سن" if is_ar else "To", 1, 100, 35, key="wa_wrk_age_max")
                        else:
                            wa_age_min, wa_age_max = 16, 35
                    with fc2:
                        wa_use_contract = st.checkbox(("تفعيل " if is_ar else "Enable ") + t("contract_end", lang), key="wa_wrk_use_contract")
                        if wa_use_contract:
                            wa_contract_range = st.date_input(
                                "Contract Range",
                                (datetime.now().date(), datetime.now().date() + timedelta(days=30)),
                                label_visibility="collapsed",
                                key="wa_wrk_contract_range",
                            )
                        else:
                            wa_contract_range = []
                    with fc3:
                        wa_use_reg = st.checkbox(("تفعيل " if is_ar else "Enable ") + t("registration_date", lang), key="wa_wrk_use_reg")
                        if wa_use_reg:
                            wa_reg_range = st.date_input(
                                "Registration Range",
                                (datetime.now().date().replace(day=1), datetime.now().date()),
                                label_visibility="collapsed",
                                key="wa_wrk_reg_range",
                            )
                        else:
                            wa_reg_range = []

                    st.markdown(f"⚙️ {t('filter_advanced_group', lang)}")
                    sc1, sc2, sc3 = st.columns(3)
                    with sc1:
                        wa_use_expired = st.checkbox(t("expired_filter", lang), key="wa_wrk_expired")
                    with sc2:
                        wa_use_not_working = st.checkbox(t("not_working_no", lang), key="wa_wrk_not_working")
                    with sc3:
                        transfer_options = {
                            "": f"— {t('transfer_all', lang)} —",
                            "First time": t("transfer_1", lang),
                            "Second time": t("transfer_2", lang),
                            "The third time": t("transfer_3", lang),
                            "More than three": t("transfer_more", lang),
                        }
                        selected_transfer_label = st.selectbox(
                            t("transfer_count_label", lang),
                            options=list(transfer_options.values()),
                            key="wa_wrk_transfer_count",
                        )
                        wa_selected_transfer_key = [k for k, v in transfer_options.items() if v == selected_transfer_label][0]

                    tc1, tc2, tc3, tc4, tc5 = st.columns(5)
                    with tc1:
                        wa_use_domestic = st.checkbox(t("domestic_worker_filter", lang), key="wa_wrk_domestic")
                    with tc2:
                        wa_use_no_huroob = st.checkbox(t("no_huroob", lang), key="wa_wrk_no_huroob")
                    with tc3:
                        wa_use_yes_huroob = st.checkbox(t("yes_huroob_label", lang), key="wa_wrk_yes_huroob")
                    with tc4:
                        wa_use_sponsor = st.checkbox(t("sponsor_transfer_yes", lang), key="wa_wrk_sponsor")
                    with tc5:
                        wa_use_outside = st.checkbox(t("work_outside_city", lang), key="wa_wrk_outside")

                wa_filters = {}
                if wa_use_age:
                    wa_filters.update({"age_enabled": True, "age_min": wa_age_min, "age_max": wa_age_max})
                if wa_use_contract and len(wa_contract_range) == 2:
                    wa_filters.update({
                        "contract_enabled": True,
                        "contract_end_start": wa_contract_range[0],
                        "contract_end_end": wa_contract_range[1],
                    })
                if wa_use_reg and len(wa_reg_range) == 2:
                    wa_filters.update({
                        "date_enabled": True,
                        "date_start": wa_reg_range[0],
                        "date_end": wa_reg_range[1],
                    })
                if wa_use_expired:
                    wa_filters["expired_only"] = True
                if wa_use_not_working:
                    wa_filters["not_working_only"] = True
                if wa_use_no_huroob:
                    wa_filters["no_huroob"] = True
                if wa_use_yes_huroob:
                    wa_filters["yes_huroob"] = True
                if wa_use_sponsor:
                    wa_filters["sponsor_transfer"] = True
                if wa_use_outside:
                    wa_filters["work_outside_city"] = True
                if wa_use_domestic:
                    wa_filters["domestic_worker"] = True
                if wa_selected_transfer_key:
                    wa_filters["transfer_count"] = wa_selected_transfer_key

                q_col, btn_col, ref_col = st.columns([4, 1, 1])
                with q_col:
                    wa_worker_q = st.text_input(
                        t("smart_search", lang),
                        placeholder=t("search_placeholder", lang),
                        key="wa_worker_search_query",
                    )
                with btn_col:
                    st.markdown("<div style='height: 1.7rem'></div>", unsafe_allow_html=True)
                    wa_search_clicked = st.button(t("search_btn", lang), type="primary", width="stretch", key="wa_worker_search_btn")
                with ref_col:
                    st.markdown("<div style='height: 1.7rem'></div>", unsafe_allow_html=True)
                    if st.button(t("refresh_data_btn", lang), width="stretch", key="wa_worker_refresh_data"):
                        st.session_state.pop("wa_workers_df", None)
                        st.rerun()

                has_wa_filter = bool(wa_filters)
                should_search = wa_search_clicked or bool(str(wa_worker_q or "").strip()) or has_wa_filter

                if should_search:
                    db = st.session_state.get("db")
                    if db is None or not hasattr(db, "fetch_data"):
                        st.error("❌ " + ("قاعدة بيانات العمال غير متاحة حالياً." if is_ar else "Workers database is not available."))
                    else:
                        if "wa_workers_df" not in st.session_state or st.session_state.wa_workers_df is None:
                            with st.spinner("⏳ " + ("جاري تحميل قاعدة بيانات العمال..." if is_ar else "Loading workers database...")):
                                st.session_state.wa_workers_df = db.fetch_data()

                        workers_src = st.session_state.wa_workers_df
                        if workers_src is None or getattr(workers_src, "empty", True):
                            st.warning("⚠️ " + ("لا توجد بيانات في قاعدة العمال." if is_ar else "No workers found in the database."))
                        else:
                            total_workers = len(workers_src)
                            st.markdown(f"**📊 {'إجمالي العمال' if is_ar else 'Total workers'}:** {total_workers}")
                            try:
                                engine = SmartSearchEngine(workers_src)
                                res = engine.search(wa_worker_q, filters=wa_filters)
                            except Exception as se:
                                st.error(f"❌ {'خطأ أثناء البحث' if is_ar else 'Search error'}: {se}")
                                res = pd.DataFrame()

                            if res is None or getattr(res, "empty", True):
                                st.warning(t("no_results", lang))
                                st.session_state.wa_worker_search_res = pd.DataFrame()
                            else:
                                # 🗑️ حذف المكرر برقم الإقامة — الاحتفاظ بالأحدث بتاريخ التسجيل
                                _iq_col = None
                                _ts_col = None
                                try:
                                    res, iqama_removed, _iq_col, _ts_col = _dedup_workers_by_iqama_keep_newest(res)
                                except Exception:
                                    iqama_removed = 0
                                # 📅 ترتيب دائم: الأحدث بتاريخ التسجيل أولاً
                                try:
                                    res = _sort_df_by_registration_newest(res, _ts_col)
                                except Exception:
                                    pass
                                st.session_state.wa_worker_search_res = res
                                st.success(
                                    f"✅ {'تم العثور على' if is_ar else 'Found'} {len(res)} "
                                    f"{'نتيجة من أصل' if is_ar else 'results out of'} {total_workers}"
                                )
                                if True:
                                    st.caption(
                                        f"🗑️ {'المكرر المحذوف برقم الإقامة' if is_ar else 'Duplicates removed by Iqama'}: {iqama_removed}"
                                        + (f" {'(تم الاحتفاظ بالأحدث بتاريخ التسجيل)' if is_ar else '(kept newest by registration date)'}" if iqama_removed > 0 else "")
                                    )

                                cols = list(res.columns)
                                c_name = _find_df_col(cols, ["full name", "الاسم الكامل", "اسم العامل", "name", "الاسم"])
                                c_phone = _find_df_col(cols, ["whatsapp", "phone number", "mobile", "رقم الجوال", "رقم الهاتف", "phone", "جوال"])
                                # 🪪 عمود رقم الإقامة فقط (مع استبعاد المهنة في الإقامة) — للعرض في جدول النتائج
                                c_iqama = _iq_col if (_iq_col is not None and _iq_col in cols) else None
                                if c_iqama is None:
                                    for _c in cols:
                                        if str(_c).startswith("__"):
                                            continue
                                        _cl = str(_c).lower().strip()
                                        _has = any(k in _cl for k in ["رقم الاقامة", "رقم الإقامة", "iqama id", "iqama", "residency", "national id", "رقم الهوية", "باسبورد"])
                                        _excl = any(x in _cl for x in ["مهنة", "مهنه", "profession", "occupation", "listed on", "job"])
                                        if _has and not _excl:
                                            if "رقم" in str(_c):
                                                c_iqama = _c
                                                break
                                            if c_iqama is None:
                                                c_iqama = _c
                                c_city = _find_df_col(cols, ["city", "مدينة"])
                                c_job = _find_df_col(cols, ["which job are you looking", "requested job", "الوظيفة", "المهنة", "job"])
                                c_nat = _find_df_col(cols, ["nationality", "الجنسية", "الجنسيه"])
                                c_gender = _find_df_col(cols, ["gender", "الجنس"])
                                # 📅 عمود تاريخ التسجيل (نفس العمود المستخدم للترتيب/حذف المكرر)
                                c_reg = _ts_col if (_ts_col is not None and _ts_col in cols) else _find_df_col(cols, ["طابع زمني", "تاريخ التسجيل", "وقت التسجيل", "timestamp", "registration date", "تاريخ التقديم", "date submitted"])
                                c_age = _find_df_col(cols, ["age", "العمر"])
                                c_cv = _find_df_col(cols, ["download cv", "سيرة", "cv", "resume"])

                                _LBL_FLAG = ("دولة" if is_ar else "Country")
                                _LBL_NAT = ("الجنسية" if is_ar else "Nationality")
                                _LBL_GENDER = ("الجنس" if is_ar else "Gender")
                                _LBL_REG = ("تاريخ التسجيل" if is_ar else "Registration Date")

                                # 🗂️ جميع الحقول: أي عمود من قاعدة البيانات لم يُعرض أعلاه يُضاف كما هو
                                _used_src = {c for c in [c_name, c_phone, c_iqama, c_city, c_job, c_nat, c_gender, c_age, c_cv, c_reg] if c is not None}
                                _extra_cols = [c for c in cols if not str(c).startswith("__") and c not in _used_src]
                                display_rows = []
                                options_list = []
                                option_map = {}
                                for i, (idx, row) in enumerate(res.iterrows()):
                                    name_v = str(row[c_name]).strip() if c_name and pd.notna(row[c_name]) else "عامل"
                                    phone_raw = str(row[c_phone]).strip() if c_phone and pd.notna(row[c_phone]) else ""
                                    phone_v = format_phone_number(phone_raw) or "".join(filter(str.isdigit, phone_raw))
                                    iqama_v = str(row[c_iqama]).strip() if c_iqama and pd.notna(row[c_iqama]) else ""
                                    if iqama_v.lower() == "nan":
                                        iqama_v = ""
                                    city_v = str(row[c_city]).strip() if c_city and pd.notna(row[c_city]) else ""
                                    job_v = str(row[c_job]).strip() if c_job and pd.notna(row[c_job]) else ""
                                    nat_raw = str(row[c_nat]).strip() if c_nat and pd.notna(row[c_nat]) else ""
                                    if nat_raw.lower() == "nan":
                                        nat_raw = ""
                                    nat_v = nat_raw
                                    flag_v = _wa_flag_url(nat_raw)
                                    gender_raw = str(row[c_gender]).strip() if c_gender and pd.notna(row[c_gender]) else ""
                                    gender_v = _wa_gender_label(gender_raw, is_ar=is_ar)
                                    reg_v = _wa_format_reg_date(row[c_reg]) if c_reg and pd.notna(row[c_reg]) else ""
                                    age_v = str(row[c_age]).strip() if c_age and pd.notna(row[c_age]) else ""
                                    cv_v = str(row[c_cv]).strip() if c_cv and pd.notna(row[c_cv]) else ""
                                    _row = {
                                        "#": i + 1,
                                        _LBL_REG: reg_v,
                                        ("الاسم" if is_ar else "Name"): name_v,
                                        ("الجوال" if is_ar else "Phone"): phone_v,
                                        ("رقم الإقامة" if is_ar else "Iqama ID"): iqama_v,
                                        ("المدينة" if is_ar else "City"): city_v,
                                        ("المهنة" if is_ar else "Job"): job_v,
                                        _LBL_FLAG: flag_v,
                                        _LBL_NAT: nat_v,
                                        _LBL_GENDER: gender_v,
                                        ("العمر" if is_ar else "Age"): age_v,
                                        ("السيرة" if is_ar else "CV"): cv_v,
                                    }
                                    for _ec in _extra_cols:
                                        try:
                                            _ev = row[_ec]
                                            _es = "" if _ev is None or (pd.notna(_ev) is False) else str(_ev).strip()
                                            if _es.lower() == "nan":
                                                _es = ""
                                        except Exception:
                                            _es = ""
                                        _ek = str(_ec).strip()
                                        if _ek in _row:
                                            _ek = f"{_ek} (2)"
                                        _row[_ek] = _es
                                    display_rows.append(_row)
                                    opt = f"{name_v} | 📱 {phone_v} | 🪪 {iqama_v} | {city_v} | {job_v} | {nat_v} | #{i}"
                                    options_list.append(opt)
                                    option_map[opt] = i

                                st.markdown("### 📊 " + ("جدول نتائج البحث" if is_ar else "Search Results") + f"  —  🗑️ {'المحذوف' if is_ar else 'Removed'}: {iqama_removed}")
                                try:
                                    _disp_df = pd.DataFrame(display_rows)

                                    def _wa_color(v):
                                        _s = str(v).lower()
                                        if "🚺" in _s or "أنث" in _s or "انث" in _s or "female" in _s:
                                            return "color: #e91e63; font-weight: bold;"
                                        if "🚹" in _s or "ذكر" in _s or "male" in _s:
                                            return "color: #3498db; font-weight: bold;"
                                        return "color: #4CAF50;"

                                    _styler = _disp_df.style.map(_wa_color, subset=[c for c in [_LBL_NAT, _LBL_GENDER] if c in _disp_df.columns])
                                    _col_cfg = {}
                                    if _LBL_FLAG in _disp_df.columns:
                                        try:
                                            _col_cfg[_LBL_FLAG] = st.column_config.ImageColumn(_LBL_FLAG, width="small")
                                        except Exception:
                                            pass
                                    st.dataframe(_styler, width="stretch", hide_index=True, column_config=_col_cfg)
                                except Exception:
                                    st.dataframe(pd.DataFrame(display_rows), width="stretch", hide_index=True)

                                with_phone = sum(1 for r in display_rows if str(r[("الجوال" if is_ar else "Phone")]).strip())
                                st.caption(
                                    f"{'سجلات بجوال صالح للإرسال' if is_ar else 'Records with a sendable phone'}: {with_phone}"
                                )

                                selected_workers = st.multiselect(
                                    "✅ " + ("حدد العمال المراد إرسالهم" if is_ar else "Select workers to send"),
                                    options=options_list,
                                    default=options_list,
                                    key="wa_worker_sys_multiselect",
                                )

                                b1, b2 = st.columns(2)
                                with b1:
                                    if st.button(
                                        f"📥 {'اعتماد المحددين' if is_ar else 'Load selected'} ({len(selected_workers)})",
                                        type="primary",
                                        key="btn_load_wa_workers_selected",
                                        width="stretch",
                                    ):
                                        selected_pos = [option_map[o] for o in selected_workers if o in option_map]
                                        picked = res.iloc[selected_pos] if selected_pos else res.iloc[0:0]
                                        extracted = _worker_df_to_wa_targets(picked, st.session_state.wa_history)
                                        _adopt_wa_worker_targets(extracted)
                                        st.toast(f"✅ {'تم اعتماد' if is_ar else 'Loaded'} {len(extracted)} {'عامل' if is_ar else 'workers'}")
                                        st.rerun()
                                with b2:
                                    if st.button(
                                        f"⚡ {'اعتماد كافة نتائج البحث' if is_ar else 'Load all search results'} ({len(res)})",
                                        key="btn_load_wa_workers_all",
                                        width="stretch",
                                    ):
                                        extracted = _worker_df_to_wa_targets(res, st.session_state.wa_history)
                                        _adopt_wa_worker_targets(extracted)
                                        st.toast(f"✅ {'تم اعتماد كافة' if is_ar else 'Loaded all'} {len(extracted)} {'نتيجة' if is_ar else 'results'}")
                                        st.rerun()
                else:
                    st.info("💡 " + (
                        "اكتب في البحث الذكي (مهنة، جنسية، مدينة، رقم جوال...) ثم اعتمد النتائج لإرسال واتساب."
                        if is_ar else
                        "Type in Smart Search (job, nationality, city, phone...) then load results for WhatsApp sending."
                    ))
            
            # 🛡️ Build review targets only when NOT sending — never interrupt the send loop
            from_worker_db = st.session_state.get('wa_from_worker_db', False)
            if not st.session_state.get('wa_running', False):
                if from_worker_db and not rebuild_review:
                    pass
                elif rebuild_review or (not st.session_state.wa_review_targets and (manual_list or st.session_state.wa_data is not None)):
                    st.session_state.wa_from_worker_db = False
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
                    type="primary",
                    key="save_smart_parts",
                ):
                    _save_smart_parts_from_editor()
                    _st = st.session_state.get("smart_save_status", {}) or {}
                    if _st.get("ok"):
                        st.toast("✅ " + ("تم حفظ التغييرات وتحديث المعاينة بنجاح!" if is_ar else "Changes saved and preview updated!"))
                        st.rerun()
                    else:
                        _err = _st.get("error") or ("تعذر الكتابة" if is_ar else "write failed")
                        st.error("❌ " + ("فشل الحفظ" if is_ar else "Save failed") + f": {_err}")

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
        # 🚀 أزرار الإرسال / الإيقاف
        # ══════════════════════════════════════════════════════════
        btn1, btn2, btn3 = st.columns([1, 1, 2])
        with btn1:
            if st.session_state.get('wa_running', False):
                if st.button(lbl['stop'], type="primary", width='stretch', key="wa_stop_btn"):
                    st.session_state.wa_running = False
                    if st.session_state.get('wa_temp_path') and os.path.exists(st.session_state.wa_temp_path):
                        try: os.remove(st.session_state.wa_temp_path)
                        except: pass
                    st.toast("🛑 " + ("تم إيقاف الإرسال" if is_ar else "Sending stopped"))
                    st.rerun()
            else:
                has_valid_msg = any(msg.strip() != "" for msg in st.session_state.wa_messages) or st.session_state.get('wa_smart_mode', False)
                ready = len(final_targets) > 0 and has_valid_msg

                if st.session_state.get('wa_done', False) and current_fp == st.session_state.get('wa_sent_fingerprint', ''):
                    st.button(lbl['sent_done'], disabled=True, width='stretch')
                else:
                    if st.button(lbl['send'].format(len(final_targets)), disabled=not ready, width='stretch', type="primary", key="wa_send_btn"):
                        # Check WhatsApp connection
                        wa_stat = st.session_state.wa_service.get_status() if st.session_state.wa_service else "Stopped"
                        if wa_stat != "Connected":
                            st.error("⚠️ " + ("يرجى تشغيل محرك واتساب ومسح الباركود أولاً للاتصال" if is_ar else "Please start WhatsApp engine and scan QR first to connect"))
                        else:
                            temp_path = None
                            if attachment:
                                import tempfile
                                suffix = os.path.splitext(attachment.name)[1]
                                base_no_dot = os.path.join(os.getcwd(), "whatsapp_session")
                                base_with_dot = os.path.join(os.getcwd(), ".whatsapp_session")
                                temp_dir = base_no_dot if os.path.exists(base_no_dot) else (base_with_dot if os.path.exists(base_with_dot) else base_no_dot)
                                os.makedirs(temp_dir, exist_ok=True)
                                try:
                                    t_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=temp_dir)
                                    t_file.write(attachment.getvalue())
                                    t_file.close()
                                    temp_path = t_file.name
                                    st.session_state.wa_temp_path = temp_path
                                except Exception as att_err:
                                    st.error(f"❌ {'فشل حفظ الملف المرفق: ' if is_ar else 'Failed to save attachment: '}{str(att_err)}")
                                    temp_path = None
                            else:
                                # 🛡️ تنظيف المسار القديم إذا لم يوجد مرفق
                                st.session_state.wa_temp_path = None

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
                    final_msg = re.sub(r'\n{3,}', '\n\n', final_msg).strip()

                temp_path = st.session_state.get('wa_temp_path')

                # إزالة سطر HR Manager المكرر في الأعلى إن كان التوقيع نفسه
                # موجوداً بالأسفل (تكرار واضح) — مع الحفاظ على باقي المتن
                _sig_tail_re = r'(?:Best regards|Kind regards|Warm regards|Sincerely|With respect),?\nAbu Fahd\nHR Manager\s*$'
                if re.search(r'^HR Manager\s*(\n|$)', final_msg) and re.search(_sig_tail_re, final_msg):
                    final_msg = re.sub(r'^HR Manager\s*\n+', '', final_msg, count=1)

                # إضافة التوقيع الإنجليزي لواتساب ماركتنج
                signature = "\n\nBest regards,\nAbu Fahd\nHR Manager"
                if signature not in final_msg:
                    final_msg += signature

                # 3. Send Message via WhatsApp Service
                # التحقق من حالة الخدمة قبل الإرسال
                if not st.session_state.wa_service or not getattr(st.session_state.wa_service, 'driver', None):
                    ok = False
                    log_msg = "محرك واتساب غير متصل (يرجى تشغيل المحرك أولاً)"
                    st.error("❌ محرك واتساب غير متصل! يرجى الضغط على 'Start Engine' أولاً")
                else:
                    with st.spinner(f"🚀 {'جاري إرسال الرسالة إلى' if is_ar else 'Sending message to'} {n} ({p})..."):
                        ok, log_msg = st.session_state.wa_service.send_message(p, final_msg, attachment_path=temp_path)

                # 4. Record Log
                entry = {
                    "idx": curr_i + 1,
                    "name": n,
                    "phone": p,
                    "status": log_msg if ok else f"فشل ({log_msg})",
                    "ok": ok,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.wa_logs.append(entry)
                if ok:
                    st.session_state.wa_history.add(p)
                    save_wa_history(st.session_state.wa_history)
                    for r_i, r_trg in enumerate(st.session_state.wa_review_targets):
                        if r_trg.get('phone') == p:
                            st.session_state.wa_review_targets[r_i]['is_sent'] = True
                            break

                # 🛡️ إيقاف فوري للحملة إذا تم إرجاع تنبيه أمان لمنع حظر الحساب وحفظ باقي الأرقام
                if not ok and str(log_msg).startswith("🛑"):
                    st.session_state.wa_running = False
                    st.error(f"🛑 تم إيقاف الحملة لحماية الحساب من الحظر: {log_msg}")
                    st.toast("🛑 تم إيقاف الحملة لحماية الحساب", icon="⚠️")
                else:
                    # 5. Move to next index
                    st.session_state.wa_idx += 1

                    # 6. Check if completed
                    if st.session_state.wa_idx >= total_targets:
                        st.session_state.wa_running = False
                        st.session_state.wa_done = True
                        if temp_path and os.path.exists(temp_path):
                            try: os.remove(temp_path)
                            except: pass
                        st.balloons()
                        st.success("🎉 " + ("اكتمل إرسال جميع الرسائل بنجاح!" if is_ar else "All messages sent successfully!"))
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
