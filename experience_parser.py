# -*- coding: utf-8 -*-
"""
برنامج تحليل سنوات الخبرة من قائمة نصوص.
القواعد المطلوبة:
- أقل من سنة (من شهر إلى 11 شهر) -> صنف "أقل من سنة" ويُعرض بالأشهر.
- سنة فأكثر -> صنف "سنة أو أكثر" ويُعرض بالسنين.
- الرقم المنفرد يُحسب كسنة (مثال: 10 = 10 سنوات، 2 = 2 سنوات، 06 = 6 سنوات).
- علامة + تعني "وأكثر".
- الأرقام الكبيرة (أكبر من 100) تُعامل على أنها مرتب وليس خبرة وتُتجاهل/تُصنف غير محدد.
"""

import re
import sys
import os
from dataclasses import dataclass
from typing import Optional
from collections import Counter

# تأكد من طباعة UTF-8 (تجنب مشكلات ترميز ويندوز CP1256 مع العربية والرموز)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# إزالة الرموز التعبيرية (emojis) من النص المعروض فقط
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

# تحويل الأرقام العربية-الهندية إلى إنجليزية
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

WORD_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1,
}

YEAR_WORDS = (
    r"year|years|yr|yrs|year's|Years|Year|yers|yeats|yeara|"
    r"tahun|سنة|سنه|سنوات"
)
MONTH_WORDS = (
    r"month|months|شهر|أشهر|شهور|manch|mant|monthe"
)


def to_ascii_digits(s: str) -> str:
    return s.translate(ARABIC_DIGITS)


def word_to_digit(s: str) -> str:
    def repl(m):
        return str(WORD_NUM.get(m.group(0).lower(), m.group(0)))
    return re.sub(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|a|an)\b",
        repl, s, flags=re.I,
    )


@dataclass
class ExpResult:
    original: str
    years: Optional[float]
    months: Optional[int]
    total_years: Optional[float]
    is_minimum: bool
    category: str
    display: str
    note: str


def parse_experience(text: str) -> ExpResult:
    orig = text
    t = to_ascii_digits(text)
    t = word_to_digit(t)
    tl = t.lower().strip()

    years: Optional[float] = None
    months: Optional[int] = None
    is_minimum = False
    note = ""

    def set_years(v: float, minimum: bool = False, n: str = ""):
        nonlocal years, is_minimum, note
        if years is None or v > years:
            years = v
            is_minimum = minimum
            note = n

    # 1) X سنوات و Y أشهر
    m = re.search(
        rf"(\d+(?:\.\d+)?)\s*(?:{YEAR_WORDS})\s*(?:and|و)\s*(\d+)\s*(?:{MONTH_WORDS})",
        tl,
    )
    if m:
        set_years(float(m.group(1)) + int(m.group(2)) / 12.0,
                  n=f"{m.group(1)} سنة و {m.group(2)} شهر")
        months = int(m.group(2))

    # 2) X ونص سنة / X and a half year
    elif years is None and re.search(YEAR_WORDS, tl):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:and a half|and half|نصف)", tl)
        if m:
            set_years(float(m.group(1)) + 0.5,
                      n=f"{m.group(1)} سنة ونصف")

    # 3) X+ سنوات (أدنى)
    if years is None:
        m = re.search(rf"(\d+(?:\.\d+)?)\s*\+\s*(?:{YEAR_WORDS})?", tl)
        if m:
            set_years(float(m.group(1)), minimum=True,
                      n=f"{m.group(1)} سنة وأكثر")

    # 4) more than / over / above X سنوات
    if years is None:
        m = re.search(
            rf"(?:more than|over|above|more then)\s*(\d+(?:\.\d+)?)\s*(?:{YEAR_WORDS})?",
            tl,
        )
        if m:
            set_years(float(m.group(1)), minimum=True,
                      n=f"أكثر من {m.group(1)} سنة")

    # 5) more than / over X أشهر
    if years is None and months is None:
        m = re.search(
            rf"(?:more than|over|above)\s*(\d+)\s*(?:{MONTH_WORDS})", tl,
        )
        if m:
            months = int(m.group(1))
            set_years(int(m.group(1)) / 12.0, minimum=True,
                      n=f"أكثر من {m.group(1)} شهر")

    # 6) almost / nearly X سنوات
    if years is None:
        m = re.search(
            rf"(?:almost|nearly)\s*(\d+(?:\.\d+)?)\s*(?:{YEAR_WORDS})?", tl,
        )
        if m:
            set_years(float(m.group(1)) - 0.1,
                      n=f"تقريباً {m.group(1)} سنة")

    # 7) X سنوات (مع أو بدون مسافة)
    if years is None:
        m = re.search(rf"(\d+(?:\.\d+)?)\s*(?:{YEAR_WORDS})", tl)
        if m:
            set_years(float(m.group(1)), n=f"{m.group(1)} سنة")

    # 8) X أشهر
    if years is None and months is None:
        m = re.search(rf"(\d+)\s*(?:{MONTH_WORDS})", tl)
        if m:
            months = int(m.group(1))
            set_years(int(m.group(1)) / 12.0, n=f"{m.group(1)} شهر")

    # 9) رقم منفرد يُحسب كسنة إذا كان معقولاً (1-100)، وإلا يُحتمل مرتب
    if years is None and months is None:
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", t)
        if m:
            v = float(m.group(1))
            if 1 <= v <= 100:
                set_years(v, n=f"{v} سنة (رقم منفرد)")
            else:
                note = "رقم كبير يُحتمل أنه مرتب وليس خبرة"

    total_years = years

    if total_years is None:
        category = "غير محدد"
        display = "غير محدد"
    elif total_years < 1:
        category = "أقل من سنة"
        mdisplay = int(round(total_years * 12))
        display = f"{mdisplay} شهر (أقل من سنة)"
    else:
        category = "سنة أو أكثر"
        if is_minimum:
            display = f"{total_years:g} سنة وأكثر"
        else:
            display = f"{total_years:g} سنة"

    return ExpResult(orig, years, months, total_years, is_minimum,
                     category, display, note)


def category_order(cat: str) -> int:
    return {"أقل من سنة": 0, "سنة أو أكثر": 1, "غير محدد": 2}.get(cat, 3)


RAW = [
    "5 years", "+ 4 years", "+5 Years", "06", "10", "10", "10", "10", "10",
    "10", "10 yeara", "10 Month", "10 months", "10 years", "10 years",
    "10 years", "10 years", "10 years", "10 years", "10 years",
    "10 years and the experience the working 🫰", "10 years experience",
    "10 years of experience as a head barista", "10+", "10+",
    "10+ years", "10month", "10yr", "10yrs", "10yrs experince", "11 years",
    "11 years and 9 months", "12", "12", "12", "12 years", "12 yeats",
    "13", "14", "14", "14 month", "14 years", "15", "15 years", "15 years",
    "15 years", "17", "17 years", "2000", "2000 riyals", "2000-2500",
    "2000sr", "20years", "21 years", "2400", "2500", "2500+",
    "26 months", "2800-3000SAR", "3", "3", "3", "3", "3", "3", "3", "3",
    "3", "3", "3", "3", "3", "3", "3", "3", "3 months", "3 months ",
    "3 tahun", "3 Year", "3 year ", "3 year ", "3 year ", "3 year ",
    "3 year plus ", "3 year's", "3 year's ", "3 year's ", "3 years",
    "3 years", "3 years", "3 years", "3 years", "3 years", "3 years",
    "3 years", "3 years", "3 years", "3 years", "3 years", "3 years",
    "3 years", "3 years", "3 years", "3 years ", "3 years ", "3 years ",
    "3 years ", "3 years ", "3 years ", "3 years ", "3 years ", "3 years ",
    "3 years ", "3 years ", "3 years ", "3 years ", "3 years ", "3 years ",
    "3 years ", "3 years ", "3 years ", "3 years ", "3 years ", "3 years ",
    "3 years ", "3 years ", "3 Years", "3 Years", "3 years 7 month ",
    "3 years and 5 month ", "3 years and half", "3 years as barista at Dunkin",
    "3 years experience ", "3 years experience ", "3 years expirience in Qiddiya office",
    "3 years in saudi", "3 years in Speciality coffee industry",
    "3 yers 6 mant", "3 yours plus", "3 yrs", "3 yrs", "3 yrs", "3_ year's ",
    "3-4 years", "3,000 to 3,500", "3,500", "3.5", "3.5 year ",
    "3.5 year ", "3+ Years ", "30", "3000", "3000 or 3500", "3200", "3500",
    "3500", "3500 total package", "3years", "3years", "3years", "3years",
    "3years", "3years", "3years", "3years", "3years ", "3years ",
    "3years ", "3years ", "3years and 4months", "3years and 6months",
    "3years barista ", "3yrs", "3yrs", "3yrs", "3yrs", "3yrs", "4", "4",
    "4", "4", "4", "4", "4", "4", "4", "4", "4", "4", "4", "4", "4", "4",
    "4", "4", "4", "4", "4", "4", "4", "4", "4 and a half year",
    "4 months", "4 year", "4 year ", "4 year  experimce", "4 year more",
    "4 year up", "4 year's ", "4 year's ", "4 Year's ", "4 years", "4 years",
    "4 years", "4 years", "4 years", "4 years", "4 years", "4 years",
    "4 years", "4 years", "4 years", "4 years", "4 years", "4 years",
    "4 years", "4 years ", "4 years ", "4 years ", "4 years ", "4 years ",
    "4 years ", "4 years ", "4 years ", "4 years ", "4 years ", "4 years ",
    "4 years ", "4 years ", "4 Years ", "4 years 6 month ",
    "4 years 7 months ", "4 years and 4 months ",
    "4 years barista  and waiter 10 year ", "4 years in Saudi Arabia ",
    "4 years in the Philippines ", "4 years of experience",
    "4 years plus Experience ", "4 yet ", "4-5 years experience as a Supervisor Headbarista ",
    "4.5 year", "4.5 year", "4.5 years ", "4000", "4500", "4500sr",
    "4months", "4months ", "4months ", "4year ", "4years", "4years",
    "4years", "4years", "4years", "4years ", "4years ", "4years ",
    "4years us a waitress and barista/tea girl 1year in half", "4yrs",
    "4yrs", "5", "5", "5", "5", "5", "5", "5", "5", "5", "5", "5", "5",
    "5", "5", "5", "5 year ", "5 year ", "5 year ", "5 year ",
    "5 Year as a barista still active working ", "5 year plus",
    "5 year's ", "5 year's in Dunkin Donuts ", "5 years", "5 years",
    "5 years", "5 years", "5 years", "5 years", "5 years", "5 years",
    "5 years", "5 years", "5 years", "5 years", "5 years", "5 years",
    "5 years", "5 years", "5 years ", "5 years ", "5 years ", "5 years ",
    "5 years ", "5 years ", "5 years ", "5 years ", "5 years ",
    "5 years as a barista in ksa in tishreen cafe",
    "5 years experience barista in saudi Arabia ( kyan cafe)",
    "5 years for teaboy and 2 years for barista", "5 years plus ",
    "5 yers", "5 yrs", "5 yrs", "5سنوات في مجال الأغذية والمشروبات ",
    "5y", "5years", "5years", "5years", "5years", "5years", "5years",
    "5years", "5years", "5years", "5yer", "5yrs", "5yrs", "5yrs", "5yrs",
    "5yrs", "5yrs experience ", "6", "6", "6", "6", "6", "6", "6", "6",
    "6", "6", "6", "6", "6", "6 months", "6 months ", "6 months ",
    "6 year", "6 year ", "6 year ", "6 year ", "6 Year ", "6 Year's",
    "6 years", "6 years", "6 years", "6 years", "6 years", "6 years",
    "6 years", "6 years", "6 Years", "6 Years", "6 years ", "6 years ",
    "6 years ", "6 years ", "6 years ", "6 years ", "6 years ",
    "6 years ", "6 years ", "6 years ", "6 years exp in restaurants",
    "6 years experience barista ", "6 years in total ",
    "6 years of experience, I do have! ", "6 yrs", "6 yrs",
    "6 yrs in Hospitality Industry, ", "6 yrs of experience", "6.5 years ",
    "6months", "6months abovew", "6years", "6years", "6years", "6years ",
    "6years ", "6years and 7months", "6yrs", "7", "7", "7", "7", "7",
    "7", "7", "7 month ", "7 year's ", "7 years", "7 years", "7 years",
    "7 years", "7 years", "7 years", "7 years", "7 Years", "7 years ",
    "7 years ", "7 years ", "7 years ", "7 years ", "7 years ", "7 years ",
    "7 Years ", "7 years 6 month ", "7 years 6 month ", "7 years 6 month Saudi Arabia ",
    "7 years complete ", "7 years experience ", "7 years+",
    "7year waiter ", "7years ", "7yrs", "7yrs", "7yrs", "7yrs", "7yrs",
    "8", "8", "8", "8", "8", "8", "8", "8", "8", "8 month ", "8 months",
    "8 months ", "8 months ", "8 months Barista , 2years Teaboy", "8 years",
    "8 years", "8 years", "8 years", "8 years", "8 years", "8 years ",
    "8 years ", "8 yrs", "8 yrs",
    "8 yrs, Im a working student in McDonald's for almost 5 years my position is crew chief, 6months ojt in shakeys as a waiter, 2yrs in Wildflour restaurant casual dining for 2 years as a waiter ",
    "8 yrs.", "8year", "8years ", "8yrs", "8yrs as a barista ", "9", "9",
    "9", "9 month", "9 year", "9 years", "9 years", "9 years", "9 years",
    "9 years", "9 years", "9 years", "9 years ", "9 years ", "9 years ",
    "9 years ", "9 years ", "9 years experience ", "9 years in food industry",
    "9-10 months ", "9manch for Saudi Arabia ", "9yeard", "9years",
    "9years experience ", "9yrs", "Above 9years ",
    "Almost 10 years im. In the coffee shop", "Almost 5 years ",
    "almost 6 months ", "Almost 7yrs", "Almost 7yrs", "Almost 8 years ",
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
    "I have over 5 years of hands-on experience in the Specialty Coffee industry. I am an expert in manual brewing techniques (including V60, Chemex, and others), precise espresso calibration, and high-level latte art. Additionally, I am highly proficient in preparing premium Matcha and a wide range of categories such as Mojitos, Milkshakes, and Waffles. My focus is on maintaining the highest international brewing standards and delivering a perfect cup with consistency, speed, and creative menu additions.",
    "i have total of 10yrs experience in hospitality",
    "I was working Dose caffee more than 6 years I have lot of experience in the coffee shop .",
    "I've been here in Saudi Arabia for almost 9 months as a barista but it's the same as a teaboy because I also make Saudi coffee. And my experience in the Philippines is 3 years plus",
    "Im working as barista for 4 years in crepe affaire dammam ",
    "in barista is 9 months ,in waiter is approx 7yrs ",
    "In Saudi 4 year total of 6 year in speciality in commercial coffee ",
    "Ive been working for 6 years for different multitasking jobs like waiter, barista, cashier as well as making coffee",
    "l have 3 years experience in beresta ",
    "Management - 12 years in KSA", "More 15 years", "More than 10 ",
    "More than 10 years", "More than 10 years", "More than 10 years ",
    "More than 20 years", "More than 3 years", "More than 3 years",
    "More than 3 yrs", "More than 4 yers ", "More than 4years",
    "more than 5 years", "More than 6 monthe", "More than 6 years ",
    "More than 7 years ", "More than 8 years ", "More than 9 years",
    "More then 5 years", "My experience in 6 years", "Nearly 3 years ",
    "One year and 6months ", "Over 3 years ", "Over 3years",
    "Over 6 years ", "Overall 6 years ",
    "Tea girl 9 yrs, barista more than 6 months, cleaning  more than 2 yrs. ",
    "Waiter 6years/ Barista No",
]


def main():
    results = [parse_experience(r) for r in RAW]

    print("=" * 90)
    print("نتيجة تحليل الخبرة من المرفق")
    print("=" * 90)
    print(f"{'#':<4} {'النص الأصلي':<55} {'النتيجة':<22} {'التصنيف':<16} {'ملاحظة'}")
    print("-" * 90)
    for i, r in enumerate(results, 1):
        print(f"{i:<4} {strip_emoji(r.original)[:52]:<55} {r.display:<22} {r.category:<16} {r.note}")

    print("\n" + "=" * 90)
    print("ملخص الإحصائيات")
    print("=" * 90)
    from collections import Counter
    cnt = Counter(r.category for r in results)
    for cat in ["أقل من سنة", "سنة أو أكثر", "غير محدد"]:
        print(f"{cat}: {cnt.get(cat, 0)}")
    print(f"إجمالي السطور المعالجة: {len(results)}")

    print("\n" + "=" * 90)
    print("تطبيق مثال الصورة: < 1 سنة أو > 5 سنوات أو = 3 سنوات")
    print("=" * 90)

    def filter_exp(op: str, value: float):
        out = []
        for r in results:
            if r.total_years is None:
                continue
            if op == "<" and r.total_years < value:
                out.append(r)
            elif op == ">" and r.total_years > value:
                out.append(r)
            elif op == "=" and abs(r.total_years - value) < 1e-9:
                out.append(r)
        return out

    for op, val in [("<", 1), (">", 5), ("=", 3)]:
        matched = filter_exp(op, val)
        print(f"\n{op} {val} سنة -> عدد النتائج: {len(matched)}")
        for r in matched[:20]:
            print(f"  - {r.display:<22} | {strip_emoji(r.original)[:60]}")
        if len(matched) > 20:
            print(f"  ... و {len(matched) - 20} نتيجة أخرى")

    # فلتر جديد: بين سنة وسنتين (شامل 1 و 2)
    print("\n" + "=" * 90)
    print("نتائج الخبرة بين سنة وسنتين (1 <= سنوات <= 2)")
    print("=" * 90)
    between = [r for r in results if r.total_years is not None and 1 <= r.total_years <= 2]
    print(f"عدد النتائج: {len(between)}")
    for r in between:
        print(f"  - {r.display:<22} | {strip_emoji(r.original)[:70]}")

    # فلتر محدث: بين 2 و 5 سنوات (شامل 2 و 5)
    print("\n" + "=" * 90)
    print("نتائج الخبرة بين 2 و 5 سنوات (2 <= سنوات <= 5)")
    print("=" * 90)
    between_2_5 = [r for r in results if r.total_years is not None and 2 <= r.total_years <= 5]
    print(f"عدد النتائج: {len(between_2_5)}")
    for r in between_2_5:
        print(f"  - {r.display:<22} | {strip_emoji(r.original)[:70]}")

    # حفظ النتيجة في ملف UTF-8 جانب السكريبت لسهولة القراءة (تجنب مشاكل ترميز الشاشة)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experience_result.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("نتيجة تحليل الخبرة من المرفق\n")
        f.write("=" * 90 + "\n")
        f.write(f"{'#':<4} {'النص الأصلي':<55} {'النتيجة':<22} {'التصنيف':<16} {'ملاحظة'}\n")
        f.write("-" * 90 + "\n")
        for i, r in enumerate(results, 1):
            f.write(f"{i:<4} {strip_emoji(r.original)[:52]:<55} {r.display:<22} {r.category:<16} {r.note}\n")
        f.write("\n" + "=" * 90 + "\n")
        f.write("ملخص الإحصائيات\n")
        f.write("=" * 90 + "\n")
        cnt = Counter(r.category for r in results)
        for cat in ["أقل من سنة", "سنة أو أكثر", "غير محدد"]:
            f.write(f"{cat}: {cnt.get(cat, 0)}\n")
        f.write(f"إجمالي السطور المعالجة: {len(results)}\n")
    print(f"\nتم حفظ النتيجة التفصيلية في: {out_path}")


if __name__ == "__main__":
    main()
