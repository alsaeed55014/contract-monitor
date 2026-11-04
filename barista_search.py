# -*- coding: utf-8 -*-
"""
برنامج بحث عن باريستا واستخراج سنوات/أشهر الخبرة المرتبطة به.
المنطق:
1. يكشف إذا كان النص يذكر "باريستا" (باريستا / باريتسا / برستانس / barista ...)
2. يستخرج سنوات/أشهر الخبرة المرتبطة تحديداً بـ "باريستا"
3. يستخرج الخبرة العامة (أخرى) إذا كان الباريستا ضمن مهارات متعددة
4. يدعم التصفية حسب نطاق سنوات خبرة الباريستا (مثلاً من 2 إلى 5 سنوات)
"""

import re
import sys
import os
from dataclasses import dataclass
from typing import Optional, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# -------------------- أدوات مساعدة --------------------

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

WORD_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1,
}

EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001f926-\U0001f937"
    "\U0001F900-\U0001F9FF"
    "\U00002600-\U000026FF"
    "\U00002500-\U00002BEF"
    "\ufe0f"
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(s: str) -> str:
    return EMOJI_RE.sub("", s)


def to_ascii_digits(s: str) -> str:
    return s.translate(ARABIC_DIGITS)


def word_to_digit(s: str) -> str:
    def repl(m):
        return str(WORD_NUM.get(m.group(0).lower(), m.group(0)))
    return re.sub(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|a|an)\b",
        repl, s, flags=re.I,
    )


def normalize(text: str) -> str:
    t = strip_emoji(text)
    t = to_ascii_digits(t)
    t = word_to_digit(t)
    return t


# -------------------- كشف الباريستا --------------------

BARISTA_RE = re.compile(
    r"باريستا|باريتسا|برستانس|باريستي|باريتستا|باريستات|bari[st]?sta|barista",
    flags=re.I,
)


def contains_barista(text: str) -> bool:
    return bool(BARISTA_RE.search(text))


# -------------------- استخراج خبرة الباريستا تحديداً --------------------

# أنماط استخراج سنوات/أشهر بجوار كلمة باريستا
_BARISTA_YEAR_PATTERNS = [
    # X سنوات/years ... باريستا
    re.compile(rf"(\d+(?:\.\d+)?)\s*(?:سنة|سنوات|year|years|yr|yrs)\s*(?:como|as|في|ك)?\s*bari?sta", flags=re.I),
    # باريستا ... X سنوات/years
    re.compile(rf"bari?sta\s*(?:는|는)?\s*(\d+(?:\.\d+)?)\s*(?:سنة|سنوات|year|years|yr|yrs)", flags=re.I),
    # باريستا: X سنوات
    re.compile(rf"bari?sta\s*[:/]\s*(\d+(?:\.\d+)?)\s*(?:سنة|سنوات|year|years|yr|yrs)", flags=re.I),
    # X سنوات باريستا (باريستا في النهاية)
    re.compile(rf"(\d+(?:\.\d+)?)\s*(?:سنة|سنوات|year|years|yr|yrs)\s*bari?sta", flags=re.I),
    # باريستا X سنوات (باريستا في البداية)
    re.compile(rf"bari?sta\s*(\d+(?:\.\d+)?)\s*(?:سنة|سنوات|year|years|yr|yrs)", flags=re.I),
]

_BARISTA_MONTH_PATTERNS = [
    re.compile(rf"(\d+)\s*(?:شهر|shahr|month|months)\s*bari?sta", flags=re.I),
    re.compile(rf"bari?sta\s*(\d+)\s*(?:شهر|shahr|month|months)", flags=re.I),
    re.compile(rf"bari?sta\s*[:/]\s*(\d+)\s*(?:شهر|shahr|month|months)", flags=re.I),
]


def extract_barista_experience(text: str) -> Tuple[Optional[float], Optional[int], str]:
    """
    يعيد (years, months, note) لخبرة الباريستا تحديداً.
    إذا لم يُعثر على خبرة مخصصة للباريستا يعيد (None, None, note).
    """
    tl = normalize(text).lower()

    years: Optional[float] = None
    months: Optional[int] = None
    note_parts: List[str] = []

    # 1) أنماط السنوات المخصصة للباريستا
    for pat in _BARISTA_YEAR_PATTERNS:
        m = pat.search(tl)
        if m:
            v = float(m.group(1))
            if years is None or v > years:
                years = v
                note_parts.append(f"خبرة باريستا مباشرة: {m.group(0)}")
            break  # نأخذ أول سلسلة سنوات明確ة

    # 2) أنماط الأشهر المخصصة للباريستا
    for pat in _BARISTA_MONTH_PATTERNS:
        m = pat.search(tl)
        if m:
            v = int(m.group(1))
            if months is None or v > months:
                months = v
                note_parts.append(f"أشهر باريستا مباشرة: {m.group(0)}")
            break

    # 3) صيغة "X سنوات و Y أشهر" بجوار الباريستا
    if years is None and months is None:
        m = re.search(
            rf"(\d+(?:\.\d+)?)\s*(?:سنة|سنوات|year|years)\s*(?:و|and)\s*(\d+)\s*(?:شهر|months)\s*bari?sta",
            tl,
        )
        if m:
            years = float(m.group(1)) + int(m.group(2)) / 12.0
            months = int(m.group(2))
            note_parts.append(f"باريستا سنوات وأشهر: {m.group(0)}")
        else:
            m = re.search(
                rf"bari?sta\s*(\d+(?:\.\d+)?)\s*(?:سنة|سنوات|year|years)\s*(?:و|and)\s*(\d+)\s*(?:شهر|months)",
                tl,
            )
            if m:
                years = float(m.group(1)) + int(m.group(2)) / 12.0
                months = int(m.group(2))
                note_parts.append(f"باريستا سنوات وأشهر (معكوس): {m.group(0)}")

    note = " | ".join(note_parts) if note_parts else "لا توجد خبرة مخصصة للباريستا"
    return years, months, note


# -------------------- استخراج الخبرة العامة (الأخرى) --------------------

YEAR_WORDS = r"سنة|سنوات|year|years|yr|yrs|year's|Years|Year|yers|yeats|yeara|tahun"
MONTH_WORDS = r"شهر|أشهر|شهور|month|months|manch|mant|monthe"


def extract_general_experience(text: str) -> Tuple[Optional[float], Optional[int], str]:
    """المنطق السابق لاستخراج إجمالي الخبرة من النص."""
    tl = normalize(text).lower()
    years: Optional[float] = None
    months: Optional[int] = None
    note = ""

    def set_years(v, n=""):
        nonlocal years, note
        if years is None or v > years:
            years = v
            note = n

    def set_months(v, n=""):
        nonlocal months, years, note
        if months is None or v > months:
            months = v
            if years is None:
                years = v / 12.0
            note = n

    # X سنوات و Y أشهر
    m = re.search(
        rf"(\d+(?:\.\d+)?)\s*(?:{YEAR_WORDS})\s*(?:و|and)\s*(\d+)\s*(?:{MONTH_WORDS})", tl,
    )
    if m:
        set_years(float(m.group(1)) + int(m.group(2)) / 12.0,
                  f"{m.group(1)} سنة و {m.group(2)} شهر")
        months = int(m.group(2))

    # X+ سنوات
    if years is None:
        m = re.search(rf"(\d+(?:\.\d+)?)\s*\+\s*(?:{YEAR_WORDS})?", tl)
        if m:
            set_years(float(m.group(1)), f"{m.group(1)} سنة وأكثر")

    # more than / over X سنوات
    if years is None:
        m = re.search(
            rf"(?:more than|over|above|more then)\s*(\d+(?:\.\d+)?)\s*(?:{YEAR_WORDS})?", tl,
        )
        if m:
            set_years(float(m.group(1)), f"أكثر من {m.group(1)} سنة")

    # X سنوات
    if years is None:
        m = re.search(rf"(\d+(?:\.\d+)?)\s*(?:{YEAR_WORDS})", tl)
        if m:
            set_years(float(m.group(1)), f"{m.group(1)} سنة")

    # X أشهر
    if years is None and months is None:
        m = re.search(rf"(\d+)\s*(?:{MONTH_WORDS})", tl)
        if m:
            set_months(int(m.group(1)), f"{m.group(1)} شهر")

    # رقم منفرد (1-100)
    if years is None and months is None:
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", tl)
        if m:
            v = float(m.group(1))
            if 1 <= v <= 100:
                set_years(v, f"{v} سنة (رقم منفرد)")

    total = years
    if total is None:
        return None, None, "غير محدد"
    elif total < 1:
        md = int(round(total * 12))
        return total, md, f"{md} شهر (أقل من سنة)"
    else:
        return total, None, f"{total:g} سنة"


# -------------------- هيكل نتيجة التحليل --------------------

@dataclass
class BaristaResult:
    original: str
    has_barista: bool
    barista_years: Optional[float]
    barista_months: Optional[int]
    barista_note: str
    general_years: Optional[float]
    general_months: Optional[int]
    general_note: str
    category: str  # "باريستا أساسي", "باريستا ضمن مهارات أخرى", "غير محدد"


def analyze(text: str) -> BaristaResult:
    has_barista = contains_barista(text)
    b_years, b_months, b_note = extract_barista_experience(text)
    g_years, g_months, g_note = extract_general_experience(text)

    if has_barista and (b_years is not None or b_months is not None):
        category = "باريستا أساسي"
    elif has_barista:
        category = "باريستا ضمن مهارات أخرى"
    else:
        category = "غير محدد (لا يذكر باريستا)"

    return BaristaResult(
        original=text,
        has_barista=has_barista,
        barista_years=b_years,
        barista_months=b_months,
        barista_note=b_note,
        general_years=g_years,
        general_months=g_months,
        general_note=g_note,
        category=category,
    )


# -------------------- قائمة النصوص التجريبية (نفس المرفق) --------------------

RAW = [
    "5 years", "+ 4 years", "+5 Years", "06", "10", "10 Month", "10 months", "10 years",
    "10+", "10+ years", "10month", "10yr", "10yrs", "11 years", "11 years and 9 months",
    "12", "12 years", "14 month", "14 years", "15", "15 years", "17", "17 years",
    "20years", "21 years", "26 months", "3", "3 months", "3 tahun", "3 Year", "3 year ",
    "3 year plus ", "3 year's", "3 years", "3 years ", "3 Years", "3 years 7 month ",
    "3 years and 5 month ", "3 years and half", "3 years as barista at Dunkin",
    "3 years experience ", "3 years expirience in Qiddiya office",
    "3 years in saudi", "3 years in Speciality coffee industry",
    "3 yers 6 mant", "3 yours plus", "3 yrs", "3_ year's ", "3-4 years",
    "3.5 year ", "3+ Years ", "30", "3000", "3years", "3years ", "3years and 4months",
    "3years barista ", "3yrs", "4", "4 months", "4 year", "4 year  experimce",
    "4 year more", "4 year up", "4 year's ", "4 years", "4 years ", "4 Years ",
    "4 years 6 month ", "4 years 7 months ", "4 years and 4 months ",
    "4 years barista  and waiter 10 year ", "4 years in Saudi Arabia ",
    "4 years of experience", "4 years plus Experience ", "4-5 years experience as a Supervisor Headbarista ",
    "4.5 year", "4.5 years ", "4months", "4year ", "4years", "4years ",
    "4years us a waitress and barista/tea girl 1year in half", "4yrs", "5", "5 year ",
    "5 Year as a barista still active working ", "5 year plus", "5 year's ",
    "5 year's in Dunkin Donuts ", "5 years", "5 years ", "5 years as a barista in ksa in tishreen cafe",
    "5 years experience barista in saudi Arabia ( kyan cafe)",
    "5 years for teaboy and 2 years for barista", "5 years plus ",
    "5سنوات في مجال الأغذية والمشروبات ", "5y", "5years", "5yer", "5yrs", "5yrs experience ",
    "6", "6 months", "6 year", "6 Year", "6 years", "6 years ", "6 Years",
    "6 years exp in restaurants", "6 years experience barista ",
    "6 years in total ", "6 years of experience, I do have! ", "6 yrs",
    "6 yrs of experience", "6.5 years ", "6months", "6years", "6years and 7months", "6yrs",
    "7", "7 month ", "7 year's ", "7 years", "7 years ", "7 Years",
    "7 years 6 month ", "7 years 6 month Saudi Arabia ", "7 years experience ",
    "7 years+", "7year waiter ", "7years ", "7yrs", "8", "8 month ", "8 months",
    "8 months ", "8 months Barista , 2years Teaboy", "8 years", "8 years ", "8 yrs",
    "8 yrs, Im a working student in McDonald's for almost 5 years my position is crew chief, 6months ojt in shakeys as a waiter, 2yrs in Wildflour restaurant casual dining for 2 years as a waiter ",
    "8 yrs.", "8year", "8years ", "8yrs", "8yrs as a barista ", "9", "9 month",
    "9 year", "9 years", "9 years ", "9 years experience ", "9 years in food industry",
    "9-10 months ", "9manch for Saudi Arabia ", "9yeard", "9years", "9years experience ",
    "9yrs", "Above 9years ", "Almost 10 years im. In the coffee shop", "Almost 5 years ",
    "almost 6 months ", "Almost 7yrs", "Almost 8 years ",
    "as a barista working in abroad, almost 6 years",
    "As barista 4years and as a professional caregiver 1 year experienced in the Philippines and in 2 weeks I will finish my certification as nurse aid.",
    "At least 2000", "Barista 4 years. Burger chef 6 years ",
    "barista 6 years bartender 1 and 6 months ",
    "Barista: 4 Years/ Tea boy: 2 Years/ Waiter: 2 Years",
    "I had experience as a waiter for over 5 years and for barista is 1 year experience ",
    "I have 10 years of experience in the field of Barista.",
    "I have 3 years experience in coffee shop work",
    "I have 4 years experience in UAE, 5 years experience in Saudi Arabia ",
    "I have 4 years work experience ", "I have 5 years experience in the hospitality ",
    "I have 7 years and 6 months of experience in the field.",
    "I have a 4-day scientific course and a 1-week training course.",
    "I have almost 7yrs experience of this field",
    "I have experience 5 years barista And accounted ",
    "I have experienced almost 14 years Barista job",
    "I have expirinance 12 years in Saudi Arabia ",
    "I have over 5 years of hands-on experience in the Specialty Coffee industry.",
    "i have total of 10yrs experience in hospitality",
    "I was working Dose caffee more than 6 years I have lot of experience in the coffee shop .",
    "I've been here in Saudi Arabia for almost 9 months as a barista but it's the same as a teaboy because I also make Saudi coffee. And my experience in the Philippines is 3 years plus",
    "Im working as barista for 4 years in crepe affaire dammam ",
    "in barista is 9 months ,in waiter is approx 7yrs ",
    "In Saudi 4 year total of 6 year in speciality in commercial coffee ",
    "Ive been working for 6 years for different multitasking jobs like waiter, barista, cashier as well as making coffee",
    "l have 3 years experience in beresta ",
    "Management - 12 years in KSA", "More 15 years", "More than 10 ",
    "More than 10 years", "More than 20 years", "More than 3 years", "More than 3 yrs",
    "More than 4 yers ", "More than 4years", "more than 5 years", "More than 6 monthe",
    "More than 6 years ", "More than 7 years ", "More than 8 years ", "More than 9 years",
    "More then 5 years", "My experience in 6 years", "Nearly 3 years ",
    "One year and 6months ", "Over 3 years ", "Over 3years", "Over 6 years ",
    "Overall 6 years ",
    "Tea girl 9 yrs, barista more than 6 months, cleaning  more than 2 yrs. ",
    "Waiter 6years/ Barista No",
]


# -------------------- تشغيل التحليل --------------------

def main():
    results = [analyze(r) for r in RAW]

    print("=" * 100)
    print("تحليل النصوص بحثاً عن باريستا واستخراج سنوات الخبرة")
    print("=" * 100)
    print(f"{'#':<4} {'يذكر باريستا':<12} {'خبرة باريستا':<18} {'خبرة عامة/أخرى':<18} {'التصنيف':<22} {'النص الأصلي'}")
    print("-" * 100)

    for i, r in enumerate(results, 1):
        b_disp = f"{r.barista_years:g} سنة" if r.barista_years is not None else (
            f"{r.barista_months} شهر" if r.barista_months is not None else "—")
        g_disp = f"{r.general_years:g} سنة" if r.general_years is not None else (
            f"{r.general_months} شهر" if r.general_months is not None else "—")
        print(f"{i:<4} {'نعم' if r.has_barista else 'لا':<12} {b_disp:<18} {g_disp:<18} {r.category:<22} {strip_emoji(r.original)[:55]}")

    # ملخص
    print("\n" + "=" * 100)
    print("ملخص")
    print("=" * 100)
    from collections import Counter
    cnt = Counter(r.category for r in results)
    for cat, c in cnt.items():
        print(f"{cat}: {c}")
    print(f"إجمالي السطور: {len(results)}")

    # -------------------- فلتر: باريستا بين 2 و 5 سنوات --------------------
    print("\n" + "=" * 100)
    print("فلتر: نصوص تذكر باريستا وتتراوح خبرة الباريستا بين 2 و 5 سنوات (شامل)")
    print("=" * 100)
    filtered = [
        r for r in results
        if r.has_barista and r.barista_years is not None and 2 <= r.barista_years <= 5
    ]
    print(f"عدد النتائج: {len(filtered)}")
    for r in filtered:
        b_disp = f"{r.barista_years:g} سنة" if r.barista_years is not None else (
            f"{r.barista_months} شهر" if r.barista_months is not None else "—")
        print(f"  - {b_disp:<18} | {strip_emoji(r.original)[:70]}")

    # حفظ النتيجة في ملف UTF-8
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "barista_result.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("نتيجة تحليل الباريستا والخبرة\n")
        f.write("=" * 100 + "\n")
        f.write(f"{'#':<4} {'يذكر باريستا':<12} {'خبرة باريستا':<18} {'خبرة عامة/أخرى':<18} {'التصنيف':<22} {'النص الأصلي'}\n")
        f.write("-" * 100 + "\n")
        for i, r in enumerate(results, 1):
            b_disp = f"{r.barista_years:g} سنة" if r.barista_years is not None else (
                f"{r.barista_months} شهر" if r.barista_months is not None else "—")
            g_disp = f"{r.general_years:g} سنة" if r.general_years is not None else (
                f"{r.general_months} شهر" if r.general_months is not None else "—")
            f.write(f"{i:<4} {'نعم' if r.has_barista else 'لا':<12} {b_disp:<18} {g_disp:<18} {r.category:<22} {strip_emoji(r.original)}\n")
        f.write("\n" + "=" * 100 + "\n")
        f.write("فلتر: باريستا بين 2 و 5 سنوات\n")
        f.write("=" * 100 + "\n")
        for r in filtered:
            b_disp = f"{r.barista_years:g} سنة" if r.barista_years is not None else (
                f"{r.barista_months} شهر" if r.barista_months is not None else "—")
            f.write(f"  - {b_disp:<18} | {strip_emoji(r.original)}\n")
    print(f"\nتم حفظ النتيجة التفصيلية في: {out_path}")


if __name__ == "__main__":
    main()
