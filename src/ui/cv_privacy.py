import io
import os
import re
import json
import base64
import streamlit as st
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import pdfplumber
import numpy as np

# reportlab is optional: used to render cleaned text into a clean PDF.
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from src.core.i18n import t
except ImportError:
    from core.i18n import t

# python-docx (Word) support — optional, falls back gracefully
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DocxDocument = None
    DOCX_AVAILABLE = False

# AI translation (deep-translator / Google Translate) — optional
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    GoogleTranslator = None
    TRANSLATOR_AVAILABLE = False

# Fallback: googletrans (free, no API key) — optional
try:
    from googletrans import Translator as GoogleTransTranslator
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GoogleTransTranslator = None
    GOOGLETRANS_AVAILABLE = False

# --- Offline English → Arabic dictionary for CV/resume terms ---
# Used when online translation services are blocked/unavailable.
CV_EN_AR_DICT = {
    # Sections & headers
    "RESUME": "السيرة الذاتية",
    "RESUME OF": "السيرة الذاتية لـ",
    "OF": "لـ",
    "PROFESSIONAL SUMMARY": "ملخص مهني",
    "SUMMARY": "ملخص",
    "CAREER OBJECTIVE": "الهدف الوظيفي",
    "OBJECTIVE": "الهدف",
    "SKILLS": "المهارات",
    "SKILL": "مهارة",
    "EXPERIENCE": "الخبرة العملية",
    "WORK EXPERIENCE": "الخبرة العملية",
    "PROFESSIONAL EXPERIENCE": "الخبرة المهنية",
    "EMPLOYMENT HISTORY": "تاريخ التوظيف",
    "EDUCATION": "التعليم",
    "ACADEMIC BACKGROUND": "الخلفية الأكاديمية",
    "QUALIFICATIONS": "المؤهلات",
    "CERTIFICATIONS": "الشهادات",
    "CERTIFICATES": "الشهادات",
    "LANGUAGES": "اللغات",
    "CONTACT": "معلومات الاتصال",
    "CONTACT INFORMATION": "معلومات الاتصال",
    "PERSONAL INFORMATION": "المعلومات الشخصية",
    "REFERENCES": "المراجع",
    "ACHIEVEMENTS": "الإنجازات",
    "AWARDS": "الجوائز",
    "PUBLICATIONS": "المنشورات",
    "PROJECTS": "المشاريع",
    "VOLUNTEER EXPERIENCE": "الخبرة التطوعية",
    "INTERESTS": "الاهتمامات",
    "HOBBIES": "الهوايات",

    # Common CV words
    "Name": "الاسم",
    "Email": "البريد الإلكتروني",
    "Phone": "الهاتف",
    "Mobile": "الجوال",
    "Address": "العنوان",
    "Location": "الموقع",
    "City": "المدينة",
    "Country": "الدولة",
    "Nationality": "الجنسية",
    "Date of Birth": "تاريخ الميلاد",
    "Gender": "النوع",
    "Marital Status": "الحالة الاجتماعية",
    "Current Position": "المنصب الحالي",
    "Current Company": "الشركة الحالية",
    "Previous Position": "المنصب السابق",
    "Previous Company": "الشركة السابقة",
    "Employer": "صاحب العمل",
    "Job Title": "المسمى الوظيفي",
    "Position": "المنصب",
    "Role": "الدور",
    "Responsibilities": "المسؤوليات",
    "Duties": "المهام",
    "Duration": "المدة",
    "Period": "الفترة",
    "From": "من",
    "To": "إلى",
    "Present": "حتى الآن",
    "Current": "حالياً",
    "Previous": "سابقاً",
    "Company": "الشركة",
    "Organization": "المنظمة",
    "Institution": "المؤسسة",
    "University": "الجامعة",
    "College": "الكلية",
    "School": "المدرسة",
    "Degree": "الشهادة العلمية",
    "Bachelor": "بكالوريوس",
    "Master": "ماجستير",
    "PhD": "دكتوراه",
    "Diploma": "دبلوم",
    "Certificate": "شهادة",
    "Training": "تدريب",
    "Course": "دورة",
    "Workshop": "ورشة عمل",
    "Seminar": "ندوة",
    "Language": "لغة",
    "Native": "اللغة الأم",
    "Fluent": "إجادة تامة",
    "Intermediate": "متوسط",
    "Basic": "مبتدئ",
    "Reading": "قراءة",
    "Writing": "كتابة",
    "Speaking": "محادثة",
    "Listening": "استماع",

    # Common action verbs / phrases
    "To serve": "لخدمة",
    "In a responsible position": "في منصب مسؤول",
    "At an organization": "في منظمة",
    "And successfully apply": "والتطبيق الناجح لـ",
    "Acquired interpersonal skills": "المهارات الشخصية المكتسبة",
    "To enhance": "لتعزيز",
    "Organizational efficiencies": "الكفاءة التنظيمية",
    "Produced": "إنتاج",
    "High-volume": "حجم كبير",
    "Coffee orders": "طلبات القهوة",
    "Quickly and accurately": "بسرعة ودقة",
    "Meeting customer demand": "لتلبية طلب العملاء",
    "Described": "وصف",
    "Coffee blends": "خلطات القهوة",
    "Preparation": "التحضير",
    "Customers": "العملاء",
    "Assisting": "مساعدة",
    "Choices": "الخيارات",
    "Based on": "اعتماداً على",
    "Personal tastes": "الأذواق الشخصية",
    "Educated": "تثقيف",
    "Coworkers": "زملاء العمل",
    "About": "حول",
    "New products": "منتجات جديدة",
    "Increasing": "زيادة",
    "Cafe": "مقهى",
    "Sales": "مبيعات",
    "Checked in": "تسجيل الوصول",
    "During meals": "أثناء الوجبات",
    "Orders were received": "تم استلام الطلبات",
    "Barista": "باريستا",
    "Waiter": "نادل",
    "At": "في",
    "Hotel": "فندق",
    "Course Form": "نموذج الدورة",
    "Sep": "سبتمبر",
    "Dec": "ديسمبر",
    "Hotel Management": "إدارة الفنادق",

    # Additional common CV/resume terms to improve offline translation quality
    "Tertiary": "التعليم العالي",
    "Secondary": "الثانوي",
    "School": "المدرسة",
    "College": "الكلية",
    "University": "الجامعة",
    "Board": "المجلس",
    "GPA": "المعدل التراكمي",
    "Passing Year": "سنة التخرج",
    "Institute": "المعهد",
    "Humanities": "الآداب",
    "Produced": "أنتج",
    "quickly": "بسرعة",
    "accurately": "بدقة",
    "meet": "لتلبية",
    "demand": "طلب",
    "Described": "وصف",
    "blends": "خلطات",
    "assisting": "مساعدة",
    "choices": "الخيارات",
    "based": "اعتماداً على",
    "personal": "شخصية",
    "tastes": "الأذواق",
    "Educated": "أثقف",
    "coworkers": "زملاء العمل",
    "products": "منتجات",
    "increasing": "زيادة",
    "sales": "مبيعات",
    "Checked": "فحص",
    "during": "أثناء",
    "received": "تم استلام",
    "correctly": "بشكل صحيح",
    "expectations": "التوقعات",
    "Welcomed": "رحب",
    "warmth": "دفء",
    "enthusiasm": "حماس",
    "recommending": "يوصي بـ",
    "beverage": "مشروبات",
    "snack": "وجبات خفيفة",
    "options": "خيارات",
    "preferences": "التفضيلات",
    "Strength": "نقاط القوة",
    "Excellent": "ممتاز",
    "written": "كتابة",
    "oral": "شفهي",
    "communication": "تواصل",
    "skills": "المهارات",
    "Bengali": "البنغالية",
    "English": "الإنجليزية",
    "language": "اللغة",
    "Strong": "قوي",
    "computer": "الكمبيوتر",
    "applications": "التطبيقات",
    "proficiency": "إتقان",
    "Arabic": "العربية",
    "Self-Appraisal": "التقييم الذاتي",
    "Energetic": "نشيط",
    "Self-motivated": "متحمس ذاتياً",
    "Ambitious": "طموح",
    "Co-operative": "تعاوني",
    "Honest": "صادق",
    "Punctual": "منتظم في المواعيد",
    "Quick": "سريع",
    "learner": "متعلم",
    "Like": "يحب",
    "challenge": "تحدي",
    "Personal": "شخصي",
    "Details": "التفاصيل",
    "Father's": "الوالد",

    # Additional words from the user's CV
    "Service Crew": "طاقم الخدمة",
    "Damak": "داماك",
    "Nepal": "نيبال",
    "Permanent Address": "العنوان الدائم",
    "Type": "النوع",
    "Male": "ذكر",
    "Married": "متزوج",
    "Hindi": "الهندية",
    "Nepali": "النيبالية",
    "Height": "الطول",
    "Bachelor": "بكالوريوس",
    "Passed": "ناجح",
    "Computer": "الكمبيوتر",
    "Barista": "باريستا",
    "Hygienic": "النظافة الشخصية",
    "Certified": "معتمد",
    "Store": "المتجر",
    "Learning": "التعلم",
    "Food": "الطعام",
    "Safety": "السلامة",
    "Team player": "فريق عمل",
    "Fast": "سريع",
    "decision making": "اتخاذ القرار",
    "Good": "جيد",
    "communication": "التواصل",
    "Able": "قادر",
    "to": "على",
    "work": "العمل",
    "in": "في",
    "any": "أي",
    "pressure": "ضغط",
    "situation": "موقف",
    "lead": "قيادة",
    "the": "الـ",
    "group": "المجموعة",
    "for": "لـ",
    "good": "جيد",
    "results": "النتائج",
    "Supervisor": "مشرف",
    "Caribou Coffee": "كاريبو كوفي",
    "Tasks": "المهام",
    "and": "و",
    "Responsibilities": "المسؤوليات",
    "Welcomes": "يرحب",
    "by": "بواسطة",
    "determining": "تحديد",
    "their": "خاصتهم",
    "coffee": "القهوة",
    "interests": "الاهتمامات",
    "needs": "الاحتياجات",
    "Promotes": "يروج",
    "consumption": "الاستهلاك",
    "educating": "تثقيف",
    "selling": "بيع",
    "grinding": "طحن",
    "brewing": "تحضير",
    "equipment": "المعدات",
    "accessories": "الإكسسوارات",
    "supplies": "المستلزمات",
    "preparing": "تحضير",
    "serving": "تقديم",
    "variety": "مجموعة متنوعة",
    "of": "من",
    "drinks": "المشروبات",
    "along": "مع",
    "pastries": "المخبوزات",
    "cookies": "البسكويت",
    "menu": "القائمة",
    "answering": "الإجابة",
    "questions": "الأسئلة",
    "Sells": "يبيع",
    "differences": "الاختلافات",
    "beans": "الحبوب",
    "machines": "الآلات",
    "demonstrating": "إظهار",
    "how": "كيف",
    "operates": "يعمل",
    "follows": "يتبع",
    "prescribed": "الموصوفة",
    "recipes": "الوصفات",
    "techniques": "التقنيات",
    "such": "مثل",
    "as": "مثل",
    "espresso": "إسبريسو",
    "lungo": "لونغو",
    "caffe": "كافيه",
    "latte": "لاتيه",
    "cappuccino": "كابتشينو",
    "Generates": "يولد",
    "revenues": "الإيرادات",
    "attracting": "جذب",
    "new": "جديد",
    "defining": "تحديد",
    "expanded": "الموسعة",
    "services": "الخدمات",
    "products": "المنتجات",
    "Maintains": "يحافظ",
    "inventories": "المخزونات",
    "replenishing": "إعادة تعبئة",
    "bean": "حبة",
    "supply": "الإمداد",
    "stocking": "تخزين",
    "maintaining": "الحفاظ",
    "Keeps": "يحافظ",
    "operating": "التشغيل",
    "instructions": "التعليمات",
    "troubleshooting": "استكشاف الأخطاء",
    "breakdowns": "الأعطال",
    "performing": "أداء",
    "preventive": "الوقائي",
    "maintenance": "الصيانة",
    "calling": "طلب",
    "repairs": "الإصلاحات",
    "safe": "آمن",
    "healthy": "صحي",
    "environment": "البيئة",
    "organization": "المنظمة",
    "standards": "المعايير",
    "sanitation": "النظافة",
    "regulations": "اللوائح",
    "Improves": "يحسن",
    "quality": "الجودة",
    "studying": "دراسة",
    "evaluating": "تقييم",
    "re-designing": "إعادة تصميم",
    "processes": "العمليات",
    "implementing": "تنفيذ",
    "changes": "التغييرات",
    "improving": "تحسين",
    "appearance": "المظهر",
    "store": "المتجر",
    "bar": "البار",
    "Updates": "يحدث",
    "job": "الوظيفة",
    "knowledge": "المعرفة",
    "participating": "المشاركة",
    "educational": "التعليمية",
    "opportunities": "الفرص",
    "reading": "قراءة",
    "retail": "تجزئة",
    "trade": "تجارة",
    "food service": "خدمة الطعام",
    "publications": "المنشورات",
    "networks": "الشبكات",
    "Enhances": "يعزز",
    "shop": "المتجر",
    "reputation": "السمعة",
    "accepting": "قبول",
    "ownership": "المسؤولية",
    "accomplishing": "إنجاز",
    "different": "مختلف",
    "requests": "الطلبات",
    "exploring": "استكشاف",
    "add": "إضافة",
    "value": "قيمة",
    "accomplishments": "الإنجازات",
    "Waiter": "نادل",
    "prepare": "تحضير",
    "all": "جميع",
    "Food": "الطعام",
    "beverages": "المشروبات",
    "mise-en-place": "الإعداد المسبق",
    "prior": "قبل",
    "service": "الخدمة",
    "provide": "توفير",
    "warm": "دافئ",
    "welcome": "ترحيب",
    "fond": "مودة",
    "farewell": "وداع",
    "guests": "الضيوف",
    "Greet": "تحية",
    "according": "وفقاً",
    "ensure": "ضمان",
    "superior": "متميز",
    "Anticipate": "توقع",
    "guest": "الضيف",
    "ascertain": "تأكد",
    "satisfaction": "الرضا",
    "respond": "استجابة",
    "urgently": "بسرعة",
    "appropriately": "بشكل مناسب",
    "concerns": "المخاوف",
    "Possess": "امتلاك",
    "knowledge": "المعرفة",
    "different": "مختلف",
    "kind": "نوع",
    "silverware": "الأدوات الفضية",
    "maintaining": "الحفاظ",
    "type": "نوع",
    "E.P.N.S": "النيكل المطلية بالكهرباء",
    "Electro": "كهربائي",
    "Plated": "مطلية",
    "Nickel": "النيكل",
    "Silver": "فضي",
    "used": "مستخدم",
    "restaurant": "المطعم",
    "Set": "ضبط",
    "up": "فوق",
    "table": "الطاولة",
    "plan": "الخطة",
    "cover": "الغطاء",
    "layout": "التخطيط",
    "defined": "محدد",
    "management": "الإدارة",
    "Make": "جعل",
    "sure": "تأكد",
    "assigned": "محدد",
    "completed": "مكتمل",
    "Attend": "حضور",
    "briefings": "الإحاطات",
    "each": "كل",
    "meal": "الوجبة",
    "period": "الفترة",
    "Know": "معرفة",
    "Specials": "العروض الخاصة",
    "day": "اليوم",
    "Offer": "عرض",
    "Wine": "النبيذ",
    "List": "القائمة",
    "attend": "الاهتمام",
    "napkins": "المناديل",
    "Take": "أخذ",
    "orders": "الطلبات",
    "Serve": "تقديم",
    "check": "فحص",
    "clear": "مسح",
    "station": "المحطة",
    "during": "أثناء",
    "after": "بعد",
    "If": "إذا",
    "required": "مطلوب",
    "assist": "مساعدة",
    "bringing": "جلب",
    "from": "من",
    "kitchen": "المطبخ",
    "ensuring": "ضمان",
    "accuracy": "الدقة",
    "timeliness": "السرعة",
    "Handle": "معالجة",
    "complaints": "الشكاوى",
    "professional": "مهني",
    "manner": "طريقة",
    "soiled": "متسخ",
    "operating": "التشغيل",
    "designated": "المحدد",
    "wash-up": "غسيل",
    "storage": "التخزين",
    "area": "المنطقة",
    "generate": "إنشاء",
    "final": "النهائي",
    "bill": "الفاتورة",
    "POS": "نقاط البيع",
    "system": "النظام",
    "offer": "عرض",
    "settlement": "التسوية",
    "re-set": "إعادة ضبط",
    "tables": "الطاولات",
    "according": "وفقاً",
    "instructions": "التعليمات",
    "clean": "تنظيف",
    "linen": "الكتان",
    "Report": "تقرير",
    "theft": "السرقة",
    "damages": "الأضرار",
    "Manager": "المدير",
    "Assistant": "مساعد",
    "completion": "الإكمال",
    "shift": "الوردية",
    "Help": "مساعدة",
    "other": "أخرى",
    "areas": "المناطق",
    "such": "مثل",
    "answering": "الإجابة",
    "completing": "إكمال",
    "financial": "المالي",
    "transactions": "المعاملات",
    "Print": "طباعة",
    "closing": "الإغلاق",
    "report": "تقرير",
    "drop": "إيداع",
    "cash": "نقد",
    "with": "مع",
    "front": "الواجهة",
    "office": "المكتب",
    "accounts": "الحسابات",
    "department": "القسم",
    "Tally": "مطابقة",
    "Credit": "ائتمان",
    "Card": "بطاقة",
    "settlements": "التسويات",
    "batch": "دفعة",
    "EDC": "الجهاز الإلكتروني",
    "machine": "الآلة",
    "Close": "إغلاق",
    "terminal": "المحطة",
    "report": "تقرير",
    "duty": "الواجب",
    "regularly": "بشكل منتظم",
    "on": "في",
    "time": "الوقت",
    "wearing": "ارتداء",
    "correct": "صحيح",
    "uniform": "الزي",
    "name": "الاسم",
    "badge": "الشارة",
    "at": "في",
    "times": "الأوقات",
    "have": "امتلاك",
    "complete": "كامل",
    "understanding": "الفهم",
    "operating": "التشغيل",
    "policies": "السياسات",
    "procedures": "الإجراءات",
    "Must": "يجب",
    "participate": "المشاركة",
    "staff": "الموظفين",
    "maintain": "الحفاظ",
    "high": "عالي",
    "standard": "المعيار",
    "relationship": "العلاقة",
    "colleagues": "الزملاء",
    "chairs": "الكراسي",
    "china": "الخزف",
    "glass": "الزجاج",
    "silver": "الفضة",
    "items": "العناصر",
    "smaller": "أصغر",
    "toast": "الخبز المحمص",
    "soup": "الشوربة",
    "carry": "حمل",
    "carry out": "تنفيذ",
    "reasonable": "معقول",
    "assigned": "محدد",
    "Declaration": "إقرار",
    "I": "أنا",
    "take": "أخذ",
    "with": "مع",
    "great": "عظيم",
    "sense": "إحساس",
    "responsibility": "المسؤولية",
    "enjoy": "استمتع",
    "the": "الـ",
    "challenge": "التحدي",
    "new": "جديد",
    "situations": "المواقف",
    "expect": "توقع",
    "make": "جعل",
    "positive": "إيجابي",
    "contribution": "مساهمة",
    "your": "لك",
    "acquire": "اكتساب",
    "that": "أن",
    "above": "أعلاه",
    "are": "هي",
    "correct": "صحيح",
    "best": "الأفضل",
    "my": "لي",
    "shall": "سوف",
    "most": "الأكثر",
    "obliged": "ملزم",
    "submit": "تقديم",
    "supporting": "الداعم",
    "documents": "الوثائق",
    "when": "عندما",
    "required": "مطلوب",
    "do": "يفعل",
    "so": "لذلك",
    "Date": "التاريخ",
    "Birth": "الميلاد",
    "Religion": "الدين",
    "Islam": "الإسلام",
    "Marital": "الحالة الاجتماعية",
    "Status": "الحالة",
    "Unmarried": "غير متزوج",
    "Blood": "فصيلة الدم",
    "Group": "المجموعة",
    "Nationality": "الجنسية",
    "Bangladeshi": "بنغلاديشي",
    "Gender": "النوع",
    "Male": "ذكر",
    "Iqama": "الإقامة",
    "Transferable": "قابلة للنقل",
    "Skill": "المهارة",
    "Word": "وورد",
    "Excel": "إكسل",
    "Driving": "القيادة",
    "License": "الرخصة",
    "Available": "متوفر",
    "Declaration": "إقرار",
    "Authenticity": "الأصالة",
    "declare": "أعلن",
    "information": "معلومات",
    "true": "صحيح",
    "knowledge": "علم",
    "required": "مطلوب",
    "applicable": "قابل للتطبيق",
    "document": "وثيقة",
    "supported": "مدعوم",
    "appropriate": "مناسب",
    "authentic": "أصلي",
    "certificate": "شهادة",
    "papers": "وثائق",
    "Signature": "توقيع",

    # English connectors/prepositions that appear in mixed translations
    " and ": " و",
    " And ": " و",
    " AND ": " و",
    " with ": " مع ",
    " With ": " مع ",
    " to ": " إلى ",
    " To ": " إلى ",
    " in ": " في ",
    " In ": " في ",
    " by ": " بواسطة ",
    " By ": " بواسطة ",
    " for ": " لـ ",
    " For ": " لـ ",
    " of ": " من ",
    " Of ": " من ",
    " the ": " الـ",
    " The ": " الـ",
    " check ": " فحص ",
    " Check ": " فحص ",
    " take ": " أخذ ",
    " Take ": " أخذ ",
    " all ": " جميع ",
    " All ": " جميع ",
    " here ": " هنا ",
    " Here ": " هنا ",
    " that ": " بأن ",
    " this ": " هذا ",
    " is ": " هو ",
    " are ": " هم ",
    " do ": " ",
    " by ": " بواسطة ",
    " if ": " إذا ",
    " If ": " إذا ",
    " where ": " حيث ",
    " Where ": " حيث ",
    " can ": " يمكن ",
    " my ": " ",
    " met ": " استوفى ",
    "Ho Management": "إدارة الفنادق",
    "Ho": "فندق",
    "cusإلىmer": "العميل",
    "expectفيions": "توقعات",
    "guests'": "توقعات الضيوف",
    "guests": "الضيوف",
    "Fفيher": "والد",
    "Higher Secondary Certificate": "شهادة الثانوية العليا",
    "Higher Secondary": "الثانوي العالي",
    "Secondary School Certificate": "شهادة المدرسة الثانوية",
    "Secondary School": "المدرسة الثانوية",
    "H.S.C": "شهادة الثانوية العليا",
    "S.S.C": "شهادة المدرسة الثانوية",
    "And College": "والكلية",
    "and College": "والكلية",
    "High School": "المدرسة الثانوية",
    "MS Word": "مايكروسوفت وورد",
    "MS Excel": "مايكروسوفت إكسل",
    "MS": "مايكروسوفت",
    "KSA": "المملكة العربية السعودية",
    "IN KSA": "في المملكة العربية السعودية",
    "Riyadh": "الرياض",
    "RIYADH": "الرياض",
    "By Birth": "بالميلاد",
    "accuray": "بدقة",
    "accuracy": "بدقة",

    # Leftover connectors / special cases
    "Educational Qualifications": "المؤهلات التعليمية",
    "Educational": "التعليمي",
    "educational": "التعليمي",
    "met guests": "استوفى توقعات الضيوف",
    "met guest": "استوفى توقعات الضيف",
    "customer preferences": "تفضيلات العميل",
    "customer": "العميل",
    "guests'": "الضيوف",
    "High School And College": "المدرسة الثانوية والكلية",
    "High School": "المدرسة الثانوية",
    "Ffather": "الوالد",
    "Father": "الوالد",
    "father": "الوالد",
    "can be": "يمكن أن يكون",
    "here by": "هنا",
    "I do": "أُقر بأن",
}

def translate_offline_en_to_ar(text):
    """
    Translate English CV text to Arabic using an offline dictionary.
    Replaces whole phrases first (longest match), then individual words.
    Works on mixed Arabic+English text: only English parts get translated.
    Preserves line structure.
    Returns (translated_text, success_flag).
    success is True if at least one replacement was made.
    """
    if not text or not text.strip():
        return text, False

    result = text
    replaced = False

    # Sort phrases by length descending to replace longest first
    sorted_phrases = sorted(CV_EN_AR_DICT.keys(), key=len, reverse=True)

    result_lines = []
    for line in result.split("\n"):
        orig_line = line
        new_line = line
        for phrase in sorted_phrases:
            # Case-insensitive replace — use word boundaries for short words
            # to avoid replacing partial words
            phrase_stripped = phrase.strip()
            if len(phrase_stripped) <= 3 and phrase_stripped.isalpha():
                # Short words: only replace if surrounded by non-alpha (word boundary)
                pattern = re.compile(r'(?<![a-zA-Z])' + re.escape(phrase) + r'(?![a-zA-Z])', re.IGNORECASE)
            else:
                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            new_line, n = pattern.subn(CV_EN_AR_DICT[phrase], new_line)
            if n > 0:
                replaced = True
        result_lines.append(new_line)

    return "\n".join(result_lines), replaced


# Regex detecting Arabic-script characters (used to preserve Arabic parts
# in mixed Arabic+English CV text during translation).
_ARABIC_CHAR_RE = re.compile(r'[\u0600-\u06FF]')


def _has_arabic(text):
    """Return True if text contains any Arabic-script character."""
    return bool(text) and bool(_ARABIC_CHAR_RE.search(text))


def _translate_mixed_text_to_arabic(text, translator):
    """
    Translate a text line that may contain a mix of Arabic and English (common
    after OCR of CVs). Arabic-script runs are preserved as-is; only the
    English/Latin runs are translated to Arabic. This prevents Google Translate's
    auto-detect from garbling mixed-language lines (e.g. "expectفيions",
    "cus到mer pالمراجع").
    """
    parts = []
    current = ""
    current_ar = None
    for ch in text:
        ch_ar = bool(_ARABIC_CHAR_RE.match(ch))
        if current_ar is None:
            current_ar = ch_ar
            current = ch
        elif ch.isspace():
            # Whitespace joins the current run regardless of script.
            current += ch
        elif ch_ar == current_ar:
            current += ch
        else:
            parts.append((current, current_ar))
            current = ch
            current_ar = ch_ar
    if current:
        parts.append((current, current_ar))

    out = []
    for part, is_ar in parts:
        if is_ar or not part.strip():
            out.append(part)
        else:
            try:
                tr = translator.translate(part)
                out.append(tr if tr else part)
            except Exception:
                out.append(part)
    return "".join(out)


def translate_text_to_arabic_ai(text):
    """
    Translate text to Arabic using AI (online services) with offline dictionary fallback.
    Returns a dict: {'text': translated_text_or_original, 'success': True/False}

    Strategy:
      1. Online deep-translator (Google), source='auto' -> target='ar'.
         Mixed Arabic+English lines are handled by translating only the
         English runs and preserving the Arabic runs as-is.
      2. Fallback: googletrans (if installed).
      3. Offline fallback: CV_EN_AR_DICT phrase/word replacement (enhanced).
      4. All failed -> return offline result regardless so user can edit manually.
    """
    if not text or not text.strip():
        return {'text': '', 'success': False}

    # Try online deep-translator first (source='auto' handles mixed/non-English text better)
    if TRANSLATOR_AVAILABLE:
        try:
            translator = GoogleTranslator(source='auto', target='ar')
            lines = text.split("\n")
            translated_lines = []
            for line in lines:
                if not line.strip():
                    translated_lines.append(line)
                    continue
                try:
                    if _has_arabic(line):
                        # Mixed line: translate only English parts, preserve Arabic
                        translated_lines.append(
                            _translate_mixed_text_to_arabic(line, translator)
                        )
                    else:
                        tr = translator.translate(line)
                        translated_lines.append(tr if tr else line)
                except Exception:
                    translated_lines.append(line)
            result = "\n".join(translated_lines)
            if result.strip() != text.strip():
                return {'text': result, 'success': True}
        except Exception:
            pass

    # Fallback: googletrans
    if GOOGLETRANS_AVAILABLE:
        try:
            gt = GoogleTransTranslator()
            result = gt.translate(text, src='auto', dest='ar').text
            if result and result.strip() != text.strip():
                return {'text': result, 'success': True}
        except Exception:
            pass

    # Offline fallback — enhanced dictionary translation
    offline_text, replaced = translate_offline_en_to_ar(text)
    print(f"[DEBUG] offline replaced={replaced}", flush=True)
    # Always return the offline result (even if partial) — better than nothing
    if replaced:
        ar_chars = len(re.findall(r'[\u0600-\u06FF]', offline_text))
        en_chars = len(re.findall(r'[a-zA-Z]', offline_text))
        total = ar_chars + en_chars
        en_ratio = (en_chars / total) if total else 1.0
        if en_ratio > 0.40:
            # Partial translation — return it but mark as not fully successful
            return {'text': offline_text, 'success': False}
        return {'text': offline_text, 'success': True}

    # All translation methods failed — return original so user can edit manually
    return {'text': text, 'success': False}
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# PyMuPDF (fitz) is optional: guard the import
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    fitz = None
    FITZ_AVAILABLE = False

# Application Base Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Background Template Keys ─────────────────────────────────────────────────
BG_KEYS = [
    'cv_bg_bytes', 'cv_bg_ext', 'cv_bg_name',
    'cv_bg_header_px', 'cv_bg_footer_px',
    'cv_bg_left_cm', 'cv_bg_right_cm',
    'cv_bg_cv_scale', 'cv_bg_cv_align',
]

# Supported Image Extensions
IMAGE_EXTS = ["jpg", "jpeg", "png", "webp", "bmp", "tiff", "jfif"]

# Supported Word Document Extensions (.doc binary and .docx Office Open XML)
DOC_EXTS = ["doc", "docx"]

# --- Patterns for Sensitive Data Detection ---
EMAIL_PATTERN = r'[a-zA-Z0-9._%+\u200b-]+@[a-zA-Z0-9.\u200b-]+\.[a-zA-Z]{2,}'

PHONE_PATTERNS = [
    # International with country code: +966547125873, +966 54 712 5873, +63 9...
    r'\+\d{1,4}[\s\-.\u200b]?\(?\d{1,4}\)?[\s\-.\u200b]?\d{2,4}[\s\-.\u200b]?\d{2,4}[\s\-.\u200b]?\d{2,4}',
    r'\+\d{7,15}',
    # Saudi mobile: 056 036 2968 / 0560362968 / 056-036-2968 / 05...
    r'05\d{2}[\s\-.\u200b]?\d{3}[\s\-.\u200b]?\d{3}',
    r'05\d{8}',
    # General continuous 9 to 15 digit numbers (handles international without +)
    r'(?:\+|00)?\d{9,14}',
    # Parentheses format: (+966) 56 036 2968
    r'\(\+?\d{1,4}\)[\s\-.\u200b]?\d{2,4}[\s\-.\u200b]?\d{2,4}[\s\-.\u200b]?\d{2,4}',
    # General spaced format: 56 036 2968
    r'\d{2,3}[\s\-.\u200b]\d{3}[\s\-.\u200b]\d{4}',
]

LABEL_PATTERNS = [
    r'Email\s*:', r'Email', r'E-mail\s*:', r'E-mail',
    r'Mobile No\s*\.\s*', r'Mobile No\s*', r'Mobile\s*:', r'Mobile',
    r'Phone\s*:', r'Phone', r'Tel\s*:', r'Tel',
    r'Contact\s*:', r'Contact No\s*:',
]


# ── Background Template Helpers ───────────────────────────────────────────────

def _pdf_page_to_image(pdf_bytes, dpi=150):
    """Render first page of a PDF to a PIL Image at the given DPI."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img


def _detect_header_footer_height(bg_img: Image.Image):
    """
    Auto-detect header & footer heights (in pixels) from a letterhead image
    by scanning for the last 'non-white' row from the top/bottom.
    Uses a whiteness threshold to find where the design ends.
    Returns (header_px, footer_px).
    """
    arr = np.array(bg_img.convert("RGB"))
    h, w = arr.shape[:2]

    def row_is_content(row):
        """True if the row has at least one pixel darker than threshold."""
        return bool(np.any(row < 220))

    # Scan from top → find last 'content' row in top 35% of page
    header_px = 0
    for y in range(int(h * 0.35)):
        if row_is_content(arr[y]):
            header_px = y + 1

    # Scan from bottom → find last 'content' row in bottom 25% of page
    footer_px = 0
    for y in range(h - 1, int(h * 0.75), -1):
        if row_is_content(arr[y]):
            footer_px = (h - y)

    # Add a comfortable safety margin
    header_px = int(header_px * 1.05) + 10
    footer_px = int(footer_px * 1.05) + 10

    return max(header_px, 20), max(footer_px, 20)


def _detect_horizontal_line_position(bg_img: Image.Image):
    """
    Detect the horizontal line below the header in the letterhead.
    Returns the y-position (pixels) of the line, or None if not found.
    """
    import numpy as np
    arr = np.array(bg_img.convert("RGB"))
    h, w = arr.shape[:2]

    # Scan top 40% of the page for horizontal lines
    search_h = int(h * 0.4)

    for y in range(search_h):
        row = arr[y]
        # Check if this row has a horizontal line (dark pixels spanning most of width)
        dark_pixels = np.sum(row < 200, axis=1)
        if len(dark_pixels) > 0 and np.max(dark_pixels) > w * 0.6:
            # Found a potential horizontal line
            # Verify it's continuous (not just scattered pixels)
            line_pixels = np.where(row < 200)[0]
            if len(line_pixels) > 0:
                max_gap = np.max(np.diff(line_pixels)) if len(line_pixels) > 1 else 0
                if max_gap < 50:  # Maximum gap of 50 pixels
                    return y + 1  # Return position below the line

    return None


def _calculate_content_area(bg_img: Image.Image, header_px, footer_px, line_y=None, left_cm=1.0, right_cm=1.0):
    """
    Calculate the optimal content area for placing the CV.
    If a horizontal line is detected, use it to determine margins.
    Returns (content_top, content_bottom, content_width, margin_sides_px).
    """
    arr = np.array(bg_img.convert("RGB"))
    h, w = arr.shape[:2]

    # If line is detected, use it as the starting point
    if line_y is not None:
        content_top = line_y + int(h * 0.05)  # 5% of page height below the line
    else:
        content_top = header_px

    content_bottom = h - footer_px

    # Calculate 5 cm in pixels (assuming 150 DPI, 1 cm ≈ 59 pixels)
    cm_to_px = 59
    margin_bottom = 5 * cm_to_px  # 5 cm

    # Adjust content_bottom to leave 5 cm margin before footer
    content_bottom = min(content_bottom, h - footer_px - margin_bottom)

    # Convert cm to pixels for side margins
    left_margin_px = int(left_cm * cm_to_px)
    right_margin_px = int(right_cm * cm_to_px)

    # Content width (full width minus margins)
    content_width = w - (left_margin_px + right_margin_px)

    return content_top, content_bottom, content_width, left_margin_px


def merge_cv_on_background(cv_bytes, bg_bytes, bg_ext,
                            header_px, footer_px,
                            cv_is_pdf=False,
                            left_cm=1.0, right_cm=1.0,
                            cv_scale=1.0, cv_align='center'):
    """
    Overlay a CV (image or PDF page) onto a background letterhead image,
    respecting header_px and footer_px safe zones.
    For multi-page PDFs, creates multiple merged pages.

    cv_scale: multiplier applied to the fitted scale (1.0 = fit to content area,
              >1.0 = enlarge, <1.0 = shrink). Width is the primary driver.
    cv_align: horizontal placement of the scaled CV ('left', 'center', 'right').

    Returns: merged_image_bytes (PNG - first page only), merged_pdf_bytes (all pages)
    """
    # ── Load background ──────────────────────────────────────────────────────
    if bg_ext == 'pdf':
        bg_img = _pdf_page_to_image(bg_bytes, dpi=150)
    else:
        bg_img = Image.open(io.BytesIO(bg_bytes)).convert("RGB")

    bg_w, bg_h = bg_img.size

    # ── Load CV page(s) ─────────────────────────────────────────────────────────
    if cv_is_pdf and FITZ_AVAILABLE:
        doc = fitz.open(stream=cv_bytes, filetype="pdf")
        cv_pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            mat = fitz.Matrix(150 / 72, 150 / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            cv_page_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            cv_pages.append(cv_page_img)
        doc.close()
    else:
        cv_img = Image.open(io.BytesIO(cv_bytes)).convert("RGBA")
        cv_pages = [cv_img]

    # ── Define safe content area on the background ───────────────────────────
    content_top = header_px
    content_bottom = bg_h - footer_px
    content_h = content_bottom - content_top

    # Apply side margins from cm to pixels
    cm_to_px = 59
    left_margin_px = int(left_cm * cm_to_px)
    right_margin_px = int(right_cm * cm_to_px)
    content_w = bg_w - (left_margin_px + right_margin_px)

    if content_h <= 0:
        content_h = max(bg_h // 2, 100)
        content_top = header_px

    # ── Process each CV page ───────────────────────────────────────────────────────
    merged_pages = []
    for page_idx, cv_img in enumerate(cv_pages):
        cv_w, cv_h = cv_img.size

        # ── Scale CV to fit inside safe content area ──────────────────────────────
        fit_scale = min(content_w / cv_w, content_h / cv_h)
        scale = fit_scale * cv_scale
        new_w = int(cv_w * scale)
        new_h = int(cv_h * scale)

        # When aligning RIGHT and user asked to enlarge (cv_scale > 1.0),
        # let the CV expand to fill more of the available width so it is not
        # left small/narrow on the left side. Cap at content_w so it stays
        # inside the safe area, but keep the right-edge anchor.
        if cv_align == 'right' and cv_scale > 1.0 and new_w < content_w:
            # Try to grow width to fill content area while respecting height
            max_w_by_height = int(cv_w * (content_h / cv_h))
            new_w = min(max_w_by_height, content_w)
            new_h = int(cv_h * (new_w / cv_w))

        # Clamp so the CV never overflows the safe content area horizontally/vertically
        if new_w > content_w:
            new_w = content_w
            new_h = int(cv_h * (new_w / cv_w))
        if new_h > content_h:
            new_h = content_h
            new_w = int(cv_w * (new_h / cv_h))

        cv_scaled = cv_img.resize((new_w, new_h), Image.LANCZOS)

        # Position the CV horizontally according to cv_align.
        # RIGHT: anchor at right edge of content area (leaves gap on left if smaller).
        # LEFT: anchor at left edge.
        # CENTER: centre in content area.
        if cv_align == 'right':
            paste_x = left_margin_px + content_w - new_w
        elif cv_align == 'left':
            paste_x = left_margin_px
        else:  # center
            paste_x = left_margin_px + (content_w - new_w) // 2
        paste_y = content_top

        # ── Compose this page ──────────────────────────────────────────────────────
        merged = bg_img.copy()
        if cv_scaled.mode == "RGBA":
            merged.paste(cv_scaled, (paste_x, paste_y), cv_scaled)
        else:
            merged.paste(cv_scaled.convert("RGBA"), (paste_x, paste_y))

        # ── Add page number at bottom ───────────────────────────────────────────
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(merged)
        page_num_text = f"Page {page_idx + 1} of {len(cv_pages)}"

        # Try to use a system font, fallback to default
        try:
            font_paths = []

            # 1. Check project fonts directory first
            fonts_dir = os.path.join(BASE_DIR, "fonts")
            if os.path.exists(fonts_dir):
                font_paths.extend([
                    os.path.join(fonts_dir, "NotoSansArabic-Regular.ttf"),
                    os.path.join(fonts_dir, "DejaVuSans.ttf"),
                ])

            # 2. Windows fonts
            if os.name == 'nt':
                windir = os.environ.get("WINDIR", r"C:\Windows")
                font_paths.extend([
                    os.path.join(windir, "Fonts", "arial.ttf"),
                    os.path.join(windir, "Fonts", "arialbd.ttf"),
                    os.path.join(windir, "Fonts", "tahoma.ttf"),
                ])

            # 3. Linux system fonts
            font_paths.extend([
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            ])

            font = None
            for fp in font_paths:
                if os.path.exists(fp):
                    font = ImageFont.truetype(fp, 16)
                    break
            if font is None:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        # Calculate text position (right-aligned at bottom, above footer)
        text_bbox = draw.textbbox((0, 0), page_num_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = bg_w - text_width - 20  # 20px from right edge
        text_y = bg_h - footer_px - 30  # 30px above footer

        # Draw text with shadow for better visibility
        draw.text((text_x + 1, text_y + 1), page_num_text, font=font, fill=(200, 200, 200))
        draw.text((text_x, text_y), page_num_text, font=font, fill=(100, 100, 100))

        merged_pages.append(merged)

    # ── Output: First page as PNG, all pages as PDF ─────────────────────────────
    img_out = io.BytesIO()
    merged_pages[0].save(img_out, format="PNG")
    merged_img_bytes = img_out.getvalue()

    # Convert all pages to PDF using fitz (PyMuPDF)
    pdf_out = io.BytesIO()
    if FITZ_AVAILABLE:
        doc = fitz.open()
        for page_img in merged_pages:
            # Convert PIL image to PDF page
            img_bytes = io.BytesIO()
            page_img.convert("RGB").save(img_bytes, format="PNG")
            img_bytes.seek(0)
            page = doc.new_page(width=page_img.width, height=page_img.height)
            page.insert_image(fitz.Rect(0, 0, page_img.width, page_img.height), stream=img_bytes.read())
        doc.save(pdf_out)
        doc.close()
    else:
        # Fallback: save first page only as PDF
        merged_pages[0].convert("RGB").save(pdf_out, format="PDF")
    merged_pdf_bytes = pdf_out.getvalue()

    return merged_img_bytes, merged_pdf_bytes


def _render_background_uploader(is_ar: bool):
    """
    Renders the background template upload section.
    Returns True when a valid background has been stored in session_state.
    """
    st.markdown("---")
    st.subheader("🖼️ " + ("رفع خلفية الورقة المؤسسية" if is_ar else "Upload Letterhead Background"))
    st.caption(
        "ارفع ورقة الشركة (PDF أو صورة) لتظهر السيرة الذاتية المنظفة فوقها مع مراعاة الترويسة والذيل." if is_ar else
        "Upload a company letterhead (PDF or image) to overlay the cleaned CV on it, respecting header & footer."
    )

    bg_uploader_col, bg_preview_col = st.columns([1, 1])

    with bg_uploader_col:
        bg_file = st.file_uploader(
            "📂 " + ("اختر ورقة الخلفية (PDF / صورة)" if is_ar else "Choose letterhead file (PDF / image)"),
            type=["pdf"] + IMAGE_EXTS,
            key="cv_bg_uploader",
            help="PDF أو JPG أو PNG..." if is_ar else "PDF or JPG or PNG..."
        )

        if bg_file is not None:
            new_name = bg_file.name
            if st.session_state.get("cv_bg_name") != new_name:
                for k in BG_KEYS + ['cv_bg_header_px', 'cv_bg_footer_px', 'cv_merged_img_bytes', 'cv_merged_pdf_bytes', 'cv_extracted_img_bytes', 'cv_extracted_pdf_bytes']:
                    st.session_state.pop(k, None)
            if "cv_bg_bytes" not in st.session_state:
                raw = bg_file.getvalue()
                ext = new_name.split(".")[-1].lower()
                st.session_state.cv_bg_bytes = raw
                st.session_state.cv_bg_ext = ext
                st.session_state.cv_bg_name = new_name

                # Auto-detect margins
                try:
                    if ext == "pdf" and FITZ_AVAILABLE:
                        bg_pil = _pdf_page_to_image(raw, dpi=72)
                    else:
                        bg_pil = Image.open(io.BytesIO(raw)).convert("RGB")
                    h_px, f_px = _detect_header_footer_height(bg_pil)
                    # Convert from 72-DPI preview to 150-DPI render coords
                    scale_factor = 150 / 72 if ext == "pdf" else 1.0
                    header_val = min(int(h_px * scale_factor), 1000)
                    footer_val = min(int(f_px * scale_factor), 1000)
                    st.session_state.cv_bg_header_px = header_val
                    st.session_state.cv_bg_footer_px = footer_val
                    # Set default side margins to 1 cm
                    st.session_state.cv_bg_left_cm = 1.0
                    st.session_state.cv_bg_right_cm = 1.0
                except Exception:
                    st.session_state.cv_bg_header_px = 195
                    st.session_state.cv_bg_footer_px = 225
                    st.session_state.cv_bg_left_cm = 1.0
                    st.session_state.cv_bg_right_cm = 1.0

        # Manual margin controls (shown when a background is loaded)
        if "cv_bg_bytes" in st.session_state:
            st.markdown("**⚙️ " + ("ضبط الهوامش" if is_ar else "Adjust margins") + "**")

            # Vertical margins (Header & Footer)
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                header_val = int(st.session_state.get("cv_bg_header_px", 195))
                header_val = min(header_val, 1000)  # Clamp to max
                st.session_state.cv_bg_header_px = st.number_input(
                    "↕️ " + ("الترويسة (بالبكسل)" if is_ar else "Header (px)"),
                    min_value=0, max_value=1000,
                    value=header_val,
                    step=5, key="cv_bg_header_input"
                )
            with m_col2:
                footer_val = int(st.session_state.get("cv_bg_footer_px", 225))
                footer_val = min(footer_val, 1000)  # Clamp to max
                st.session_state.cv_bg_footer_px = st.number_input(
                    "↕️ " + ("الذيل (بالبكسل)" if is_ar else "Footer (px)"),
                    min_value=0, max_value=1000,
                    value=footer_val,
                    step=5, key="cv_bg_footer_input"
                )

            # Horizontal margins (Left & Right in cm)
            st.markdown("**" + ("الهوامش الجانبية" if is_ar else "Side margins") + "**")
            h_col1, h_col2 = st.columns(2)
            with h_col1:
                left_cm = st.session_state.get("cv_bg_left_cm", 1.0)
                st.session_state.cv_bg_left_cm = st.number_input(
                    "⬅️ " + ("يسار (سم)" if is_ar else "Left (cm)"),
                    min_value=0.0, max_value=10.0,
                    value=left_cm,
                    step=0.1, key="cv_bg_left_cm_input"
                )
            with h_col2:
                right_cm = st.session_state.get("cv_bg_right_cm", 1.0)
                st.session_state.cv_bg_right_cm = st.number_input(
                    "➡️ " + ("يمين (سم)" if is_ar else "Right (cm)"),
                    min_value=0.0, max_value=10.0,
                    value=right_cm,
                    step=0.1, key="cv_bg_right_cm_input"
                )
            st.caption(
                "ℹ️ " + ("القيمة الافتراضية لكل من اليمين واليسار: 1 سم" if is_ar else "Default for both Right and Left: 1 cm")
            )

            # CV display size & alignment on the background
            st.markdown("**" + ("حجم السيرة الذاتية على الخلفية" if is_ar else "CV display size on background") + "**")
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                cv_scale_val = st.session_state.get("cv_bg_cv_scale", 1.0)
                st.session_state.cv_bg_cv_scale = st.slider(
                    "📏 " + ("عرض السيرة (نسبة من عرض الورقة)" if is_ar else "CV width (% of sheet width)"),
                    min_value=0.5, max_value=2.0,
                    value=cv_scale_val,
                    step=0.05,
                    help="1.00 = تعبئة عرض المنطقة المخصصة. زِد القيمة لتكبير السيرة إذا ظهرت صغيرة." if is_ar else "1.00 = fill the reserved content width. Increase if the CV appears too small/narrow.",
                    key="cv_bg_cv_scale_input"
                )
            with s_col2:
                cv_align_val = st.session_state.get("cv_bg_cv_align", "center")
                st.session_state.cv_bg_cv_align = st.selectbox(
                    "📐 " + ("محاذاة السيرة أفقياً" if is_ar else "CV horizontal alignment"),
                    options=["center", "right", "left"],
                    index=["center", "right", "left"].index(cv_align_val) if cv_align_val in ["center", "right", "left"] else 0,
                    format_func=lambda x: ("وسط" if x == "center" else ("يمين" if x == "right" else "يسار")) if is_ar else ("Center" if x == "center" else ("Right" if x == "right" else "Left")),
                    key="cv_bg_cv_align_input"
                )

            # Show auto-detection info
            st.caption("ℹ️ " + ("سيتم كشف الخط الأفقي تلقائياً وتحديد المنطقة المحجوزة (5 سم قبل الذيل)" if is_ar else "Horizontal line will be auto-detected with 5cm margin before footer"))

            if st.button(
                "🗑️ " + ("حذف الخلفية" if is_ar else "Remove background"),
                key="cv_bg_remove_btn"
            ):
                for k in BG_KEYS + ['cv_bg_header_px', 'cv_bg_footer_px', 'cv_bg_left_cm', 'cv_bg_right_cm', 'cv_merged_img_bytes', 'cv_merged_pdf_bytes', 'cv_extracted_img_bytes', 'cv_extracted_pdf_bytes']:
                    st.session_state.pop(k, None)
                st.rerun()

    with bg_preview_col:
        if "cv_bg_bytes" in st.session_state:
            st.caption("🔍 " + ("معاينة الخلفية" if is_ar else "Background preview"))
            bg_bytes = st.session_state.cv_bg_bytes
            bg_ext = st.session_state.cv_bg_ext
            if bg_ext == "pdf" and FITZ_AVAILABLE:
                preview_img = _pdf_page_to_image(bg_bytes, dpi=72)
                preview_buf = io.BytesIO()
                preview_img.save(preview_buf, format="PNG")
                st.image(preview_buf.getvalue(), use_container_width=True)
            else:
                st.image(bg_bytes, use_container_width=True)

            # Show safe-area overlay indicators
            h_px = st.session_state.get("cv_bg_header_px", 160)
            f_px = st.session_state.get("cv_bg_footer_px", 80)
            st.caption(
                f"📐 " + ("منطقة الترويسة المحجوزة" if is_ar else "Reserved header zone") +
                f": {h_px}px  |  " +
                ("الذيل" if is_ar else "Footer") + f": {f_px}px"
            )

    return "cv_bg_bytes" in st.session_state


def _extract_profile_image(img_bytes):
    """
    Extract profile picture from CV image.
    Scans the top area of the page for any non-white rectangular region that could be a profile photo.
    Returns profile image bytes or None.
    """
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        w, h = img.size

        # Focus on top 50% of the page where profile photos usually appear
        top_h = int(h * 0.50)

        # Strategy 1: Grid scan — divide top area into cells and look for non-white cells
        grid_w = max(1, w // 10)
        grid_h = max(1, top_h // 8)

        best_region = None
        best_score = 0

        for gx in range(0, w, grid_w):
            for gy in range(0, top_h, grid_h):
                x2 = min(w, gx + grid_w)
                y2 = min(top_h, gy + grid_h)
                cell = img.crop((gx, gy, x2, y2))
                cw, ch = cell.size
                if cw * ch < 100:
                    continue

                pixels = list(cell.getdata())
                if not pixels:
                    continue

                # Count non-white pixels (any channel < 245)
                non_white = sum(1 for p in pixels if p[0] < 245 or p[1] < 245 or p[2] < 245)
                non_white_ratio = non_white / len(pixels)

                # A profile photo cell will have a meaningful amount of non-white content
                # but not be entirely filled (that would be a text block)
                if 0.15 < non_white_ratio < 0.95:
                    score = non_white_ratio * (cw * ch)
                    if score > best_score:
                        best_score = score
                        best_region = (gx, gy, x2, y2)

        if best_region and best_score > 2000:
            x1, y1, x2, y2 = best_region
            # Expand region slightly to capture full photo
            pad = max(10, (x2 - x1) // 4)
            sx1 = max(0, x1 - pad)
            sy1 = max(0, y1 - pad)
            sx2 = min(w, x2 + pad)
            sy2 = min(top_h, y2 + pad)
            profile_img = img.crop((sx1, sy1, sx2, sy2))

            cw, ch = profile_img.size
            if cw < 40 or ch < 40:
                # Too small to be a useful profile photo
                pass
            else:
                # Resize keeping original aspect ratio (no square crop)
                target_w = 150
                target_h = int(ch * target_w / cw)
                profile_img = profile_img.resize((target_w, target_h), Image.LANCZOS)

                out = io.BytesIO()
                profile_img.save(out, format="PNG")
                return out.getvalue()

        # Strategy 2: Fallback — crop top-right corner (profile photo usually on right side)
        fallback = img.crop((int(w * 0.70), 0, w, min(top_h, int(top_h * 0.70))))
        fw, fh = fallback.size
        if fw >= 40 and fh >= 40:
            # Check if there's any meaningful content (not pure white)
            pixels = list(fallback.getdata())
            non_white = sum(1 for p in pixels if p[0] < 245 or p[1] < 245 or p[2] < 245)
            if non_white > len(pixels) * 0.10:
                # Resize keeping original aspect ratio
                target_w = 150
                target_h = int(fh * target_w / fw)
                fallback = fallback.resize((target_w, target_h), Image.LANCZOS)

                out = io.BytesIO()
                fallback.save(out, format="PNG")
                return out.getvalue()

        return None
    except Exception as e:
        print(f"Error extracting profile: {e}")
        return None


def _render_text_on_background(text_lines, bg_bytes, bg_ext, header_px, footer_px, profile_img_bytes=None, left_cm=1.0, right_cm=1.0):
    """
    Render extracted text lines on background with optional profile image.
    Returns merged image bytes and PDF bytes.
    """
    # Load background
    if bg_ext == 'pdf':
        bg_img = _pdf_page_to_image(bg_bytes, dpi=150)
    else:
        bg_img = Image.open(io.BytesIO(bg_bytes)).convert("RGB")

    bg_w, bg_h = bg_img.size

    # Detect horizontal line for better content area calculation
    line_y = _detect_horizontal_line_position(bg_img)

    # Get side margins from session state
    left_cm_val = st.session_state.get("cv_bg_left_cm", left_cm)
    right_cm_val = st.session_state.get("cv_bg_right_cm", right_cm)

    # Calculate optimal content area
    content_top, content_bottom, content_width, margin_sides = _calculate_content_area(
        bg_img, header_px, footer_px, line_y, left_cm_val, right_cm_val
    )

    # Create drawing context
    draw = ImageDraw.Draw(bg_img)

    # Load multiple fonts for different sizes
    try:
        from PIL import ImageFont
        # Priority order: Project fonts directory -> Windows fonts -> Linux system fonts -> default
        font_paths = []

        # 1. Check project fonts directory first (for Streamlit Cloud)
        fonts_dir = os.path.join(BASE_DIR, "fonts")
        if os.path.exists(fonts_dir):
            font_paths.extend([
                os.path.join(fonts_dir, "NotoSansArabic-Regular.ttf"),
                os.path.join(fonts_dir, "NotoSansArabic-Bold.ttf"),
                os.path.join(fonts_dir, "DejaVuSans.ttf"),
            ])

        # 2. Windows fonts (for local development)
        if os.name == 'nt':
            windir = os.environ.get("WINDIR", r"C:\Windows")
            font_paths.extend([
                os.path.join(windir, "Fonts", "arial.ttf"),
                os.path.join(windir, "Fonts", "tahoma.ttf"),
                os.path.join(windir, "Fonts", "calibri.ttf"),
                os.path.join(windir, "Fonts", "segoeui.ttf"),
            ])

        # 3. Linux system fonts (for cloud)
        font_paths.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ])

        font_path = None
        for fp in font_paths:
            if os.path.exists(fp):
                font_path = fp
                break

        if font_path:
            title_font = ImageFont.truetype(font_path, 28)
            header_font = ImageFont.truetype(font_path, 20)
            body_font = ImageFont.truetype(font_path, 18)
            small_font = ImageFont.truetype(font_path, 12)
        else:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
    except Exception:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Arabic reshaper + Bidi for proper Arabic text rendering
    try:
        import arabic_reshaper as _ar
        from bidi.algorithm import get_display as _bidi_display
        def _shape_arabic(line):
            return _bidi_display(_ar.reshape(line))
        _HAS_ARABIC = True
    except Exception as e:
        print(f"[DEBUG] Arabic libraries not available: {e}")
        _HAS_ARABIC = False
        def _shape_arabic(line):
            return line

    # Draw profile image if available (top-left of content area, like original CV)
    if profile_img_bytes:
        try:
            profile_img = Image.open(io.BytesIO(profile_img_bytes)).convert("RGBA")
            # Keep profile_img at its extracted size (already resized in _extract_profile_image)
            profile_w, profile_h = profile_img.size
            paste_x = margin_sides + 20  # Align to left side
            paste_y = content_top + 20
            bg_img.paste(profile_img, (paste_x, paste_y), profile_img)
            # Text starts to the right of profile image
            text_start_x = paste_x + profile_w + 20
        except Exception:
            text_start_x = margin_sides + 20
    else:
        text_start_x = margin_sides + 20

    # Reserve horizontal space for profile image on left side (so wrapped text doesn't overlap)
    profile_w_reserved = 0
    if profile_img_bytes:
        try:
            _pi = Image.open(io.BytesIO(profile_img_bytes)).convert("RGBA")
            profile_w_reserved = _pi.size[0] + 20
        except Exception:
            pass

    # Helper: wrap a single line to fit within available width
    def _wrap_line(line, font, max_width):
        """Split line into sub-lines that fit within max_width pixels."""
        words = line.split(' ')
        if not words:
            return ['']
        lines = []
        current = words[0]
        for w in words[1:]:
            test = current + ' ' + w
            try:
                bbox = draw.textbbox((0, 0), test, font=font)
                tw = bbox[2] - bbox[0]
            except Exception:
                tw = len(test) * 10
            if tw <= max_width:
                current = test
            else:
                lines.append(current)
                current = w
        lines.append(current)
        return lines

    # Draw text lines with better formatting
    y_pos = content_top + 20
    line_height = 25

    # Available horizontal space for text
    text_area_left = margin_sides + 20 + profile_w_reserved
    text_area_right = bg_w - margin_sides - 20
    max_text_width = text_area_right - text_area_left

    for line in text_lines:
        if y_pos + line_height > content_bottom:
            break

        # Skip empty lines
        if not line.strip():
            y_pos += 10
            continue

        # Determine if this is a header (CAPS or short line)
        is_header = len(line) < 50 and line.isupper() or any(keyword in line.upper() for keyword in ['OBJECTIVE', 'EXPERIENCE', 'EDUCATION', 'SKILLS', 'CERTIFICATE', 'INFORMATION', 'BACKGROUND'])

        # Wrap long lines so they don't overflow the page
        if is_header:
            font = header_font
        else:
            font = body_font

        wrapped_lines = _wrap_line(line, font, max_text_width)

        for sub_line in wrapped_lines:
            if y_pos + line_height > content_bottom:
                break

            try:
                # Shape Arabic text and align within margins
                if _HAS_ARABIC and _has_arabic(sub_line):
                    display_line = _shape_arabic(sub_line)
                    bbox = draw.textbbox((0, 0), display_line, font=font)
                    text_w = bbox[2] - bbox[0]
                    # Right-align Arabic within content area, respecting right margin
                    text_x = max(text_area_left, text_area_right - text_w)
                else:
                    display_line = sub_line
                    text_x = text_area_left

                # For Arabic text, try RTL rendering
                if _has_arabic(sub_line):
                    try:
                        # Right-align Arabic text
                        bbox = draw.textbbox((0, 0), display_line, font=font)
                        text_w = bbox[2] - bbox[0]
                        text_x = text_area_right - text_w
                    except:
                        text_x = text_area_left

                draw.text((text_x, y_pos), display_line, fill=(0, 0, 0), font=font)

                if is_header:
                    y_pos += line_height + 5  # Extra space after headers
                else:
                    y_pos += line_height
            except Exception:
                # Fallback for unsupported characters
                draw.text((text_area_left, y_pos), sub_line, fill=(0, 0, 0), font=body_font)
                y_pos += line_height

    # Output as PNG bytes using reportlab for better Arabic support
    img_out = io.BytesIO()
    if REPORTLAB_AVAILABLE:
        try:
            # Use reportlab to render the image with proper Arabic support
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import Paragraph
            from reportlab.lib.enums import TA_RIGHT, TA_LEFT
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # Register Arabic font if available
            if font_path and font_path.endswith('.ttf'):
                try:
                    pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
                    font_name = 'ArabicFont'
                except:
                    font_name = 'Helvetica'
            else:
                font_name = 'Helvetica'
            
            # Create PDF with Arabic text
            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=(bg_w, bg_h))
            
            # Draw background image
            img_reader = ImageReader(io.BytesIO(bg_img.convert("RGB").tobytes()))
            c.drawImage(img_reader, 0, 0, width=bg_w, height=bg_h, mask='auto')
            
            # Draw text lines with Arabic support
            from reportlab.pdfbase.pdfmetrics import stringWidth
            from reportlab.lib.enums import TA_RIGHT
            
            c.setFont(font_name, 12)
            c.setFillColorRGB(0, 0, 0)
            
            y_pos = content_top + 20
            line_height = 25
            
            for line in text_lines:
                if y_pos + line_height > content_bottom:
                    break
                
                if not line.strip():
                    y_pos += 10
                    continue
                
                # Check if Arabic and use right alignment
                if _has_arabic(line):
                    c.drawRightString(text_area_right, y_pos, line, font_name, 12)
                else:
                    c.drawString(text_area_left, y_pos, line, font_name, 12)
                
                y_pos += line_height
            
            c.save()
            merged_img_bytes = pdf_buffer.getvalue()
        except Exception as e:
            print(f"[DEBUG] Reportlab rendering failed: {e}")
            # Fallback to PIL
            img_out = io.BytesIO()
            bg_img.save(img_out, format="PNG")
            merged_img_bytes = img_out.getvalue()
    else:
        img_out = io.BytesIO()
        bg_img.save(img_out, format="PNG")
        merged_img_bytes = img_out.getvalue()

    # Output as PDF bytes using fitz (PyMuPDF) for proper PDF generation
    pdf_out = io.BytesIO()
    if FITZ_AVAILABLE:
        doc = fitz.open()
        # Convert PIL image to PDF page
        img_bytes = io.BytesIO()
        bg_img.convert("RGB").save(img_bytes, format="PNG")
        img_bytes.seek(0)
        page = doc.new_page(width=bg_img.width, height=bg_img.height)
        page.insert_image(fitz.Rect(0, 0, bg_img.width, bg_img.height), stream=img_bytes.read())
        doc.save(pdf_out)
        doc.close()
    else:
        # Fallback: save as PDF using PIL
        bg_img.convert("RGB").save(pdf_out, format="PDF")
    merged_pdf_bytes = pdf_out.getvalue()

    return merged_img_bytes, merged_pdf_bytes


def _arabic_text_to_image_bytes(text, width=1240, bg_color=(255, 255, 255), text_color=(0, 0, 0)):
    """
    Render Arabic text into a white PNG image bytes using PIL.
    Tries to use an Arabic-capable font (e.g. Arabic Typesetting, Amiri, Noto).
    Falls back to reportlab PDF→image if available.
    Returns PNG bytes or None on failure.
    """
    from PIL import ImageFont, Image as PILImage, ImageDraw as PILDraw
    import os, io as _io

    # Try to find an Arabic-capable font - priority: project fonts -> Windows -> Linux
    arabic_font_candidates = []

    # 1. Project fonts directory (for Streamlit Cloud)
    fonts_dir = os.path.join(BASE_DIR, "fonts")
    if os.path.exists(fonts_dir):
        arabic_font_candidates.extend([
            os.path.join(fonts_dir, "NotoSansArabic-Regular.ttf"),
            os.path.join(fonts_dir, "NotoSansArabic-Bold.ttf"),
            os.path.join(fonts_dir, "Amiri-Regular.ttf"),
            os.path.join(fonts_dir, "Amiri-Bold.ttf"),
            os.path.join(fonts_dir, "DejaVuSans.ttf"),
        ])

    # 2. Windows fonts
    if os.name == 'nt':
        windir = os.environ.get("WINDIR", r"C:\Windows")
        arabic_font_candidates.extend([
            os.path.join(windir, "Fonts", "arabtype.ttf"),   # Arabic Typesetting
            os.path.join(windir, "Fonts", "times.ttf"),
            os.path.join(windir, "Fonts", "tahoma.ttf"),
            os.path.join(windir, "Fonts", "arial.ttf"),
            os.path.join(windir, "Fonts", "calibri.ttf"),
            os.path.join(windir, "Fonts", "segoeui.ttf"),
        ])

    # 3. Linux system fonts
    arabic_font_candidates.extend([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ])
    font_path = None
    for fp in arabic_font_candidates:
        if os.path.exists(fp):
            font_path = fp
            break

    # Try arabic-reshaper + bidi for proper Arabic shaping
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        def shape_arabic(line):
            reshaped = arabic_reshaper.reshape(line)
            return get_display(reshaped)
        has_reshaper = True
    except ImportError:
        has_reshaper = False
        def shape_arabic(line):
            return line

    lines = text.split("\n")
    font_size = 18
    line_height = 30
    padding = 40

    if font_path:
        try:
            font = ImageFont.truetype(font_path, font_size)
            small_font = ImageFont.truetype(font_path, font_size - 4)
        except Exception:
            font = ImageFont.load_default()
            small_font = font
    else:
        font = ImageFont.load_default()
        small_font = font

    # Calculate image height needed
    img_height = max(padding * 2 + len(lines) * line_height, 400)

    img = PILImage.new("RGB", (width, img_height), bg_color)
    draw = PILDraw.Draw(img)

    y = padding
    for line in lines:
        if y + line_height > img_height:
            break
        if not line.strip():
            y += int(line_height * 0.5)
            continue

        display_line = shape_arabic(line) if has_reshaper else line

        # Measure text width to right-align Arabic
        try:
            bbox = draw.textbbox((0, 0), display_line, font=font)
            text_w = bbox[2] - bbox[0]
        except Exception:
            text_w = len(display_line) * 10

        # Right-align Arabic text
        x = max(padding, width - text_w - padding)
        try:
            draw.text((x, y), display_line, fill=text_color, font=font)
        except Exception:
            try:
                draw.text((x, y), line, fill=text_color, font=font)
            except Exception:
                pass
        y += line_height

    out = _io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _arabic_text_to_pdf_reportlab(text):
    """
    Render Arabic text to PDF bytes using reportlab with proper RTL support.
    Returns PDF bytes or None on failure.
    """
    if not REPORTLAB_AVAILABLE:
        return None
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os, io as _io

        # Try to register an Arabic font
        arabic_font_candidates = [
            (os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arabtype.ttf"), "ArabicTypesetting"),
            (os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "tahoma.ttf"), "Tahoma"),
            (os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf"), "Arial"),
        ]
        arabic_font_name = "Helvetica"
        for fp, fname in arabic_font_candidates:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont(fname, fp))
                    arabic_font_name = fname
                    break
                except Exception:
                    continue

        # Apply arabic-reshaper + bidi
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            def shape_line(ln):
                reshaped = arabic_reshaper.reshape(ln)
                return get_display(reshaped)
            has_reshaper = True
        except ImportError:
            has_reshaper = False
            def shape_line(ln):
                return ln

        buffer = _io.BytesIO()
        style_ar = ParagraphStyle(
            'Arabic',
            fontName=arabic_font_name,
            fontSize=13,
            leading=22,
            alignment=TA_RIGHT,
            wordWrap='RTL',
            spaceAfter=4,
        )
        style_title = ParagraphStyle(
            'ArabicTitle',
            fontName=arabic_font_name,
            fontSize=16,
            leading=26,
            alignment=TA_CENTER,
            spaceAfter=8,
            spaceBefore=4,
        )

        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )
        story = []
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if not line.strip():
                story.append(Spacer(1, 6))
                continue
            shaped = shape_line(line) if has_reshaper else line
            # Escape HTML special chars for reportlab
            shaped = shaped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Use title style for first few lines (name/title)
            st_to_use = style_title if i < 3 else style_ar
            try:
                story.append(Paragraph(shaped, st_to_use))
            except Exception:
                story.append(Spacer(1, 8))
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        print(f"[DEBUG] _arabic_text_to_pdf_reportlab error: {e}", flush=True)
        return None


def _render_merge_section(is_ar: bool):
    """
    Renders the 'Merge CV on Background' action button and result display.
    Should only be called when both a cleaned CV and a background exist.
    """
    st.markdown("---")
    st.subheader("🔗 " + ("دمج السيرة الذاتية مع الخلفية" if is_ar else "Merge CV with Letterhead"))

    if st.button(
        "🖨️ " + ("دمج وعرض السيرة على ورقة الشركة" if is_ar else "Overlay CV on Company Letterhead"),
        type="primary", width="stretch", key="cv_merge_btn"
    ):
        try:
            bg_bytes = st.session_state.cv_bg_bytes
            bg_ext = st.session_state.cv_bg_ext
            header_px = min(int(st.session_state.get("cv_bg_header_px", 160)), 1000)
            footer_px = min(int(st.session_state.get("cv_bg_footer_px", 80)), 1000)
            left_cm = st.session_state.get("cv_bg_left_cm", 1.0)
            right_cm = st.session_state.get("cv_bg_right_cm", 1.0)
            cv_scale = st.session_state.get("cv_bg_cv_scale", 1.0)
            cv_align = st.session_state.get("cv_bg_cv_align", "center")

            # Determine CV source bytes and type
            if "cv_cleaned_image_bytes" in st.session_state:
                cv_bytes = st.session_state.cv_cleaned_image_bytes
                cv_is_pdf = False
            elif "cv_cleaned_pdf_bytes" in st.session_state:
                cv_bytes = st.session_state.cv_cleaned_pdf_bytes
                cv_is_pdf = True
            else:
                st.warning("⚠️ " + ("يرجى تنظيف السيرة الذاتية أولاً." if is_ar else "Please clean the CV first."))
                return

            with st.spinner("⏳ " + ("جارٍ الدمج..." if is_ar else "Merging...")):
                merged_img_bytes, merged_pdf_bytes = merge_cv_on_background(
                    cv_bytes, bg_bytes, bg_ext, header_px, footer_px, cv_is_pdf=cv_is_pdf,
                    left_cm=left_cm, right_cm=right_cm,
                    cv_scale=cv_scale, cv_align=cv_align
                )
                st.session_state.cv_merged_img_bytes = merged_img_bytes
                st.session_state.cv_merged_pdf_bytes = merged_pdf_bytes

            st.success("✅ " + ("تم الدمج بنجاح!" if is_ar else "Merged successfully!"))
        except Exception as e:
            st.error(("خطأ أثناء الدمج: " if is_ar else "Merge error: ") + str(e))

    # Only show download buttons if merged result exists
    if "cv_merged_img_bytes" in st.session_state:
        st.image(
            st.session_state.cv_merged_img_bytes,
            caption="🖼️ " + ("السيرة الذاتية على الخلفية المؤسسية" if is_ar else "CV on Company Letterhead"),
            use_container_width=True
        )
        dl1, dl2 = st.columns(2)
        base_name = os.path.splitext(st.session_state.get("cv_file_name", "cv"))[0]
        with dl1:
            st.download_button(
                label="⬇️ " + ("تحميل كصورة PNG" if is_ar else "Download as PNG"),
                data=st.session_state.cv_merged_img_bytes,
                file_name=f"letterhead_{base_name}.png",
                mime="image/png",
                width="stretch",
                key="cv_dl_merged_png"
            )
        with dl2:
            st.download_button(
                label="⬇️ " + ("تحميل كـ PDF" if is_ar else "Download as PDF"),
                data=st.session_state.cv_merged_pdf_bytes,
                file_name=f"letterhead_{base_name}.pdf",
                mime="application/pdf",
                width="stretch",
                key="cv_dl_merged_pdf"
            )

        # AI Translation to Arabic — for merged CV cleaned text
        if st.session_state.get('cv_cleaned_text'):
            st.markdown("---")
            tr_col1, tr_col2 = st.columns([1, 1])
            with tr_col1:
                if st.button(
                    "🤖 " + ("ترجمة النص بالذكاء الاصطناعي إلى العربية" if is_ar else "Translate to Arabic (AI)"),
                    key="cv_translate_ai_btn_merged",
                    width='stretch',
                ):
                    with st.spinner("جارٍ الترجمة..." if is_ar else "Translating..."):
                        result = translate_text_to_arabic_ai(st.session_state.cv_cleaned_text)
                        st.session_state.cv_translated_text = result['text']
                        st.session_state.cv_translated_success = result['success']
                        if result['success']:
                            st.success("تمت الترجمة!" if is_ar else "Translation complete!")
                        else:
                            st.warning("⚠️ " + ("تعذر الترجمة تلقائياً. يمكنك تعديل النص أدناه يدوياً." if is_ar else "Automatic translation failed. You can edit the text below manually."))
            with tr_col2:
                if st.session_state.get('cv_translated_text'):
                    st.download_button(
                        label="⬇️ " + ("تحميل النص المترجم (.txt)" if is_ar else "Download Translated Text (.txt)"),
                        data=st.session_state.cv_translated_text.encode('utf-8'),
                        file_name=f"translated_{base_name}.txt",
                        mime="text/plain",
                        width='stretch',
                        key="cv_dl_translated_txt_merged"
                    )

            # Display translated (or editable) text
            if st.session_state.get('cv_translated_text'):
                st.markdown("---")
                st.subheader("🌐 " + ("النص المترجم إلى العربية (ذكاء اصطناعي)" if is_ar else "Translated Text to Arabic (AI)"))
                st.text_area(
                    "Translated Text",
                    st.session_state.cv_translated_text,
                    height=200,
                    key="cv_translated_txt_prev_merged",
                )
                st.caption("ℹ️ " + ("يمكنك تعديل النص يدوياً إذا لم تنجح الترجمة الآلية" if is_ar else "You can edit the text manually if automatic translation fails"))

                # Merge translated Arabic text on background
                st.markdown("---")
                st.subheader("🔗 " + ("دمج النص المترجم على الخلفية" if is_ar else "Merge Translated Text on Background"))
                st.caption(
                    "يتم إنشاء PDF بالعربية ودمجه مع ورقة الخلفية — النص يظهر بشكل صحيح باللغة العربية." if is_ar else
                    "A proper Arabic PDF is created and merged with the letterhead — Arabic text renders correctly."
                )
                if st.button(
                    "🖨️ " + ("دمج وعرض النص المترجم على ورقة الشركة" if is_ar else "Overlay Translated Text on Company Letterhead"),
                    type="secondary", width='stretch', key="cv_merge_translated_btn_merged",
                ):
                    if "cv_bg_bytes" not in st.session_state:
                        st.warning("⚠️ " + ("يرجى رفع ورقة الخلفية أولاً." if is_ar else "Please upload background first."))
                    else:
                        translated_text = st.session_state.cv_translated_text
                        bg_bytes = st.session_state.cv_bg_bytes
                        bg_ext = st.session_state.cv_bg_ext
                        header_px = min(int(st.session_state.get("cv_bg_header_px", 160)), 1000)
                        footer_px = min(int(st.session_state.get("cv_bg_footer_px", 80)), 1000)
                        left_cm = st.session_state.get("cv_bg_left_cm", 1.0)
                        right_cm = st.session_state.get("cv_bg_right_cm", 1.0)
                        cv_scale = st.session_state.get("cv_bg_cv_scale", 1.0)
                        cv_align = st.session_state.get("cv_bg_cv_align", "center")
                        try:
                            with st.spinner("جارٍ إنشاء PDF العربي ودمجه على الخلفية..." if is_ar else "Creating Arabic PDF and merging on background..."):
                                # Step 1: Try to create a proper Arabic PDF using reportlab
                                ar_pdf_bytes = _arabic_text_to_pdf_reportlab(translated_text)

                                if ar_pdf_bytes and FITZ_AVAILABLE:
                                    # Step 2: Merge the Arabic PDF onto the background
                                    t_img, t_pdf = merge_cv_on_background(
                                        ar_pdf_bytes, bg_bytes, bg_ext, header_px, footer_px,
                                        cv_is_pdf=True,
                                        left_cm=left_cm, right_cm=right_cm,
                                        cv_scale=cv_scale, cv_align=cv_align
                                    )
                                else:
                                    # Fallback: render Arabic text as image then merge
                                    ar_img_bytes = _arabic_text_to_image_bytes(translated_text)
                                    if ar_img_bytes:
                                        t_img, t_pdf = merge_cv_on_background(
                                            ar_img_bytes, bg_bytes, bg_ext, header_px, footer_px,
                                            cv_is_pdf=False,
                                            left_cm=left_cm, right_cm=right_cm,
                                            cv_scale=cv_scale, cv_align=cv_align
                                        )
                                    else:
                                        # Last resort: draw text directly on background
                                        translated_lines = translated_text.split("\n")
                                        # Extract profile image from cleaned CV if available
                                        _cv_bytes = st.session_state.get("cv_cleaned_image_bytes") or st.session_state.get("cv_cleaned_pdf_bytes")
                                        _profile_img = _extract_profile_image(_cv_bytes) if _cv_bytes else None
                                        t_img, t_pdf = _render_text_on_background(
                                            translated_lines, bg_bytes, bg_ext, header_px, footer_px, _profile_img,
                                            left_cm=left_cm, right_cm=right_cm
                                        )
                                st.session_state.cv_translated_merged_img_bytes = t_img
                                st.session_state.cv_translated_merged_pdf_bytes = t_pdf
                            st.success("✅ " + ("تم دمج النص المترجم على الخلفية بنجاح!" if is_ar else "Translated text merged on background!"))
                        except Exception as e:
                            st.error(("خطأ أثناء الدمج: " if is_ar else "Merge error: ") + str(e))

                if st.session_state.get('cv_translated_merged_img_bytes'):
                    st.image(
                        st.session_state.cv_translated_merged_img_bytes,
                        caption="📄 " + ("النص المترجم على الخلفية" if is_ar else "Translated Text on Background"),
                        use_container_width=True
                    )
                    dl1, dl2 = st.columns(2)
                    base_name = os.path.splitext(st.session_state.get("cv_file_name", "cv"))[0]
                    with dl1:
                        st.download_button(
                            label="⬇️ " + ("تحميل كصورة PNG" if is_ar else "Download as PNG"),
                            data=st.session_state.cv_translated_merged_img_bytes,
                            file_name=f"translated_merged_{base_name}.png",
                            mime="image/png",
                            width='stretch',
                            key="cv_dl_translated_merged_png"
                        )
                    with dl2:
                        st.download_button(
                            label="⬇️ " + ("تحميل كـ PDF" if is_ar else "Download as PDF"),
                            data=st.session_state.cv_translated_merged_pdf_bytes,
                            file_name=f"translated_merged_{base_name}.pdf",
                            mime="application/pdf",
                            width='stretch',
                            key="cv_dl_translated_merged_pdf"
                        )

    # New button: Extract text and profile, render on background
    st.markdown("---")
    st.subheader("📝 " + ("تفريغ النص والبروفيل على الخلفية" if is_ar else "Extract Text & Profile on Background"))
    st.caption(
        "استخراج النص وصورة البروفيل من السيرة الذاتية وعرضها على ورقة الخلفية بدون خلفية السيرة الأصلية." if is_ar else
        "Extract text and profile picture from CV and display on letterhead without original CV background."
    )

    # Manual text editor option
    with st.expander("✏️ " + ("أو اكتب/الصق النص يدوياً" if is_ar else "Or type/paste text manually"), expanded=False):
        manual_text = st.text_area(
            ("النص المخصص" if is_ar else "Custom text"),
            height=300,
            key="cv_manual_text_input",
            placeholder=("اكتب أو الصق النص هنا ليظهر على الخلفية..." if is_ar else "Type or paste text here to appear on background...")
        )
        if st.button(
            "📋 " + ("استخدام النص اليدوي" if is_ar else "Use Manual Text"),
            key="cv_use_manual_text_btn"
        ):
            if manual_text.strip():
                st.session_state.cv_manual_text = manual_text
                st.success("✅ " + ("تم حفظ النص اليدوي!" if is_ar else "Manual text saved!"))
            else:
                st.warning("⚠️ " + ("الرجاء إدخال نص!" if is_ar else "Please enter text!"))

    if st.button(
        "✨ " + ("تفريغ الكلمات والصورة على ورقة الخلفية" if is_ar else "Extract Text & Profile on Letterhead"),
        type="primary", width="stretch", key="cv_extract_render_btn"
    ):
        try:
            if "cv_bg_bytes" not in st.session_state:
                st.warning("⚠️ " + ("يرجى رفع ورقة الخلفية أولاً." if is_ar else "Please upload background first."))
                return

            # Get CV bytes
            if "cv_image_bytes" in st.session_state:
                cv_bytes = st.session_state.cv_image_bytes
            elif "cv_pdf_bytes" in st.session_state:
                cv_bytes = st.session_state.cv_pdf_bytes
            else:
                st.warning("⚠️ " + ("يرجى رفع السيرة الذاتية أولاً." if is_ar else "Please upload CV first."))
                return

            bg_bytes = st.session_state.cv_bg_bytes
            bg_ext = st.session_state.cv_bg_ext
            header_px = min(int(st.session_state.get("cv_bg_header_px", 160)), 1000)
            footer_px = min(int(st.session_state.get("cv_bg_footer_px", 80)), 1000)
            left_cm = st.session_state.get("cv_bg_left_cm", 1.0)
            right_cm = st.session_state.get("cv_bg_right_cm", 1.0)

            with st.spinner("⏳ " + ("جارٍ استخراج النص والصورة..." if is_ar else "Extracting text and profile...")):
                # Check if manual text is provided
                if st.session_state.get('cv_manual_text'):
                    # Use manual text
                    manual_text = st.session_state.cv_manual_text
                    cleaned_lines = manual_text.split('\n')
                    # Clean each line
                    final_lines = []
                    for line in cleaned_lines:
                        cleaned_line, _, _, _ = remove_emails_and_phones_from_text(line)
                        if cleaned_line.strip():
                            final_lines.append(cleaned_line)
                    cleaned_lines = final_lines
                    cv_bytes_for_ocr = cv_bytes  # For profile extraction
                else:
                    # Extract from CV
                    # Convert PDF to image if needed for OCR
                    cv_bytes_for_ocr = cv_bytes
                    if "cv_pdf_bytes" in st.session_state and FITZ_AVAILABLE:
                        doc = fitz.open(stream=cv_bytes, filetype="pdf")
                        mat = fitz.Matrix(150 / 72, 150 / 72)
                        pix = doc[0].get_pixmap(matrix=mat, alpha=False)
                        # Convert pixmap to PIL Image then to bytes
                        img_data = pix.tobytes("png")
                        cv_bytes_for_ocr = img_data
                        doc.close()

                    # Extract text using OCR with position info
                    ocr_data = extract_text_and_boxes_from_image(cv_bytes_for_ocr, "cv_img.jpg")
                    words = ocr_data.get('words', [])

                    # Sort words by position (top to bottom, left to right)
                    words_sorted = sorted(words, key=lambda w: (w.get('top', 0), w.get('left', 0)))

                    # Group words into lines based on y-position
                    lines = []
                    current_line = []
                    current_y = None
                    y_threshold = 15  # Pixels to consider same line

                    for word in words_sorted:
                        text = word.get('text', '').strip()
                        if not text:
                            continue

                        word_y = word.get('top', 0)
                        if current_y is None:
                            current_y = word_y
                            current_line = [text]
                        elif abs(word_y - current_y) < y_threshold:
                            current_line.append(text)
                        else:
                            if current_line:
                                lines.append(' '.join(current_line))
                            current_line = [text]
                            current_y = word_y

                    if current_line:
                        lines.append(' '.join(current_line))

                    # Clean text: remove all phone numbers and emails from each line
                    cleaned_lines = []
                    for line in lines:
                        cleaned_line, _, _, _ = remove_emails_and_phones_from_text(line)
                        if cleaned_line.strip():
                            cleaned_lines.append(cleaned_line)

                # Extract profile image (use converted image if PDF)
                profile_img = _extract_profile_image(cv_bytes_for_ocr)

                # Render on background
                merged_img_bytes, merged_pdf_bytes = _render_text_on_background(
                    cleaned_lines, bg_bytes, bg_ext, header_px, footer_px, profile_img,
                    left_cm=left_cm, right_cm=right_cm
                )
                st.session_state.cv_extracted_img_bytes = merged_img_bytes
                st.session_state.cv_extracted_pdf_bytes = merged_pdf_bytes

                # Show stats
                total_phones = 0
                total_emails = 0
                # Use original lines for stats (before cleaning)
                source_lines = st.session_state.get('cv_manual_text', '').split('\n') if st.session_state.get('cv_manual_text') else lines
                for line in source_lines:
                    _, p, e, _ = remove_emails_and_phones_from_text(line)
                    total_phones += len(p)
                    total_emails += len(e)

                if total_phones > 0 or total_emails > 0:
                    stats = []
                    if total_phones > 0:
                        stats.append(f"📞 {total_phones} " + ("رقم" if is_ar else "number(s)"))
                    if total_emails > 0:
                        stats.append(f"✉️ {total_emails} " + ("إيميل" if is_ar else "email(s)"))
                    st.info("✅ " + ("تم حذف: " if is_ar else "Removed: ") + " | ".join(stats))

            st.success("✅ " + ("تم الاستخراج والعرض بنجاح!" if is_ar else "Extracted and rendered successfully!"))
        except Exception as e:
            st.error(("خطأ أثناء الاستخراج: " if is_ar else "Extraction error: ") + str(e))

    # Only show download buttons if extracted result exists
    if "cv_extracted_img_bytes" in st.session_state:
        st.image(
            st.session_state.cv_extracted_img_bytes,
            caption="📝 " + ("النص المستخرج على الخلفية" if is_ar else "Extracted Text on Background"),
            use_container_width=True
        )
        dl1, dl2 = st.columns(2)
        base_name = os.path.splitext(st.session_state.get("cv_file_name", "cv"))[0]
        with dl1:
            st.download_button(
                label="⬇️ " + ("تحميل كصورة PNG" if is_ar else "Download as PNG"),
                data=st.session_state.cv_extracted_img_bytes,
                file_name=f"extracted_{base_name}.png",
                mime="image/png",
                width="stretch",
                key="cv_dl_extracted_png"
            )
        with dl2:
            st.download_button(
                label="⬇️ " + ("تحميل كـ PDF" if is_ar else "Download as PDF"),
                data=st.session_state.cv_extracted_pdf_bytes,
                file_name=f"extracted_{base_name}.pdf",
                mime="application/pdf",
                width="stretch",
                key="cv_dl_extracted_pdf"
            )

        # AI Translation to Arabic — for extracted CV cleaned text
        if st.session_state.get('cv_cleaned_text'):
            st.markdown("---")
            tr_col1, tr_col2 = st.columns([1, 1])
            with tr_col1:
                if st.button(
                    "🤖 " + ("ترجمة النص بالذكاء الاصطناعي إلى العربية" if is_ar else "Translate to Arabic (AI)"),
                    key="cv_translate_ai_btn_extracted",
                    width='stretch',
                ):
                    with st.spinner("جارٍ الترجمة..." if is_ar else "Translating..."):
                        result = translate_text_to_arabic_ai(st.session_state.cv_cleaned_text)
                        st.session_state.cv_translated_text = result['text']
                        st.session_state.cv_translated_success = result['success']
                        if result['success']:
                            st.success("تمت الترجمة!" if is_ar else "Translation complete!")
                        else:
                            st.warning("⚠️ " + ("تعذر الترجمة تلقائياً. يمكنك تعديل النص أدناه يدوياً." if is_ar else "Automatic translation failed. You can edit the text below manually."))
                with tr_col2:
                    if st.session_state.get('cv_translated_text'):
                        st.download_button(
                            label="⬇️ " + ("تحميل النص المترجم (.txt)" if is_ar else "Download Translated Text (.txt)"),
                            data=st.session_state.cv_translated_text.encode('utf-8'),
                            file_name=f"translated_{base_name}.txt",
                            mime="text/plain",
                            width='stretch',
                            key="cv_dl_translated_txt_extracted"
                        )

                # Display translated (or editable) text
                if st.session_state.get('cv_translated_text'):
                    st.markdown("---")
                    st.subheader("🌐 " + ("النص المترجم إلى العربية (ذكاء اصطناعي)" if is_ar else "Translated Text to Arabic (AI)"))
                    st.text_area(
                        "Translated Text",
                        st.session_state.cv_translated_text,
                        height=200,
                        key="cv_translated_txt_prev_extracted",
                    )
                    st.caption("ℹ️ " + ("يمكنك تعديل النص يدوياً إذا لم تنجح الترجمة الآلية" if is_ar else "You can edit the text manually if automatic translation fails"))


def _load_image_clean(img_bytes):
    """Load image, correct EXIF orientation, and ensure standard color mode."""
    img = Image.open(io.BytesIO(img_bytes))
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
    return img

def remove_emails_and_phones_from_text(text):
    """Remove emails, phone numbers, and their labels from text."""
    cleaned = text
    phones_found = []
    emails_found = []
    labels_found = []

    # Remove labels first
    for pattern in LABEL_PATTERNS:
        matches = re.findall(pattern, cleaned, flags=re.IGNORECASE)
        for match in sorted(set(matches), key=len, reverse=True):
            if match not in labels_found:
                labels_found.append(match)
            cleaned = cleaned.replace(match, "")

    # Find and remove emails (replace with empty string so nothing remains visible)
    emails_found = re.findall(EMAIL_PATTERN, cleaned)
    for email in sorted(set(emails_found), key=len, reverse=True):
        cleaned = cleaned.replace(email, "")

    # Find and remove phones (longest matches first) — replace with empty string
    all_phones = []
    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, cleaned)
        for match in matches:
            if match not in all_phones:
                all_phones.append(match)
    for phone in sorted(set(all_phones), key=len, reverse=True):
        if phone not in phones_found:
            phones_found.append(phone)
        cleaned = cleaned.replace(phone, "")

    # Collapse leftover multiple spaces / separators caused by removals
    cleaned = re.sub(r'\s*[|•·/,\-]\s*', ' ', cleaned)  # remove leftover separators
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()     # collapse multiple spaces

    return cleaned, phones_found, emails_found, labels_found

def clean_pdf_preserve_format(pdf_bytes):
    """Remove emails and phone numbers from PDF while preserving images, fonts, layout, and formatting.
    Returns cleaned PDF bytes."""
    if not FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) is not installed in this environment; PDF format-preserving cleaning is unavailable.")
    fitz_module = fitz
    doc = fitz_module.open(stream=pdf_bytes, filetype="pdf")
    total_emails = 0
    total_phones = 0

    for page_num in range(len(doc)):
        page = doc[page_num]

        # ── Also redact link annotations (clickable hyperlinks like mailto:) ──
        try:
            for link in page.get_links() or []:
                link_uri = link.get("uri", "") or ""
                if "@" in link_uri or "mailto:" in link_uri.lower():
                    rect = fitz_module.Rect(link.get("from", link.get("rect", [0, 0, 0, 0])))
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                    total_emails += 1
        except Exception:
            pass

        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                line_has_email = False
                line_bbox = line.get("bbox", None)
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    span_bbox = span.get("bbox", None)

                    # ── Emails: aggressive — if ANY span in the line has '@', redact the whole line ──
                    has_email = ("@" in span_text) or bool(re.findall(EMAIL_PATTERN, span_text))
                    if has_email and line_bbox:
                        rect = fitz_module.Rect(line_bbox)
                        page.add_redact_annot(rect, fill=(1, 1, 1))
                        total_emails += 1
                        line_has_email = True
                        break  # line redacted; move to next line

                    # ── Phones ── (only if this span/line is not an email line)
                    if not line_has_email:
                        phones_in_span = []
                        for pattern in PHONE_PATTERNS:
                            phones_in_span.extend(re.findall(pattern, span_text))
                        for phone in sorted(set(phones_in_span), key=len, reverse=True):
                            instances = page.search_for(phone)
                            if instances:
                                for inst in instances:
                                    rect = fitz_module.Rect(inst)
                                    page.add_redact_annot(rect, fill=(1, 1, 1))
                                    total_phones += 1
                            elif span_bbox:
                                rect = fitz_module.Rect(span_bbox)
                                page.add_redact_annot(rect, fill=(1, 1, 1))
                                total_phones += 1

    if total_emails > 0 or total_phones > 0:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page.apply_redactions()

    output = io.BytesIO()
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    output.seek(0)
    return output.read(), total_emails, total_phones

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF using pdfplumber."""
    text_parts = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


# --- Word (.doc / .docx) → Text / PDF helpers ---

def _docx_to_text(docx_bytes):
    """Extract all text from a .docx file using python-docx (paragraphs + tables)."""
    if not DOCX_AVAILABLE:
        return ""
    try:
        doc = DocxDocument(io.BytesIO(docx_bytes))
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    except Exception:
        return ""


def _extract_images_from_docx(docx_bytes):
    """
    Extract embedded images from a .docx file (which is a ZIP package).
    Returns a list of (image_name, PIL.Image) sorted by size descending.
    """
    images = []
    try:
        import zipfile
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
            media_names = [n for n in z.namelist()
                           if n.lower().startswith("word/media/")]
            for name in media_names:
                try:
                    data = z.read(name)
                    img = Image.open(io.BytesIO(data))
                    img = ImageOps.exif_transpose(img)
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGB')
                    images.append((name, img))
                except Exception:
                    continue
    except Exception:
        pass
    # Sort by size (largest first) — profile photos are usually prominent
    images.sort(key=lambda item: item[1].size[0] * item[1].size[1], reverse=True)
    return images


def _is_doc_binary(data):
    """Quick check whether bytes look like a legacy .doc (OLE Compound File) header."""
    return data[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'


def text_to_pdf_bytes(text, title="CV", profile_img=None):
    """
    Render plain text into a clean A4 PDF using reportlab.
    If profile_img (PIL Image) is provided, place it at the top-left as a profile photo.
    """
    try:
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()
        style = styles["Normal"]
        style.fontName = "Helvetica"
        style.fontSize = 11
        style.leading = 16
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
            title=title,
        )
        story = []

        # Place profile photo at top-left if available
        if profile_img is not None:
            from reportlab.platypus import Image as RLImage
            from reportlab.lib.utils import ImageReader
            img_buf = io.BytesIO()
            profile_img.convert('RGB').save(img_buf, format='PNG')
            img_buf.seek(0)
            rl_img = RLImage(img_buf, width=4 * cm, height=4 * cm)
            story.append(rl_img)
            story.append(Spacer(1, 10))

        for line in text.split("\n"):
            if line.strip():
                story.append(Paragraph(line, style))
            story.append(Spacer(1, 6))
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
    except Exception:
        return b""


def doc_to_pdf(file_bytes, filename="cv.doc"):
    """
    Convert a Word file (.doc or .docx) to PDF bytes.
    - .docx: text extracted via python-docx, embedded images (incl. profile photo)
      are extracted from the docx ZIP and inserted into the PDF so they survive
      cleaning & merge onto the company letterhead.
    - .doc (legacy binary): requires LibreOffice/antiword which are not
      available in this environment — returns empty bytes and a flag so the UI
      can show a helpful message asking the user to re-save as .docx.
    Returns (pdf_bytes, extracted_text, is_convertible).
    """
    name_lower = filename.lower()

    if name_lower.endswith(".docx"):
        if not DOCX_AVAILABLE:
            return b"", "", False
        text = _docx_to_text(file_bytes)
        # Extract embedded images (profile photo etc.) from the docx package
        images = _extract_images_from_docx(file_bytes)
        profile_img = images[0][1] if images else None
        if not text or not text.strip():
            # No text but has image — still build a PDF with the image
            pdf_bytes = text_to_pdf_bytes("", title=os.path.splitext(filename)[0],
                                          profile_img=profile_img)
            return pdf_bytes, text, True
        pdf_bytes = text_to_pdf_bytes(text, title=os.path.splitext(filename)[0],
                                      profile_img=profile_img)
        return pdf_bytes, text, True

    if name_lower.endswith(".doc"):
        # Legacy binary .doc — python-docx cannot read it.
        if _is_doc_binary(file_bytes):
            return b"", "", False  # not convertible without LibreOffice
        # Not a real .doc binary; try treating as docx anyway
        text = _docx_to_text(file_bytes)
        images = _extract_images_from_docx(file_bytes)
        profile_img = images[0][1] if images else None
        if text and text.strip():
            pdf_bytes = text_to_pdf_bytes(text, title=os.path.splitext(filename)[0],
                                          profile_img=profile_img)
            return pdf_bytes, text, True
        return b"", "", False

    return b"", "", False


# --- Multi-Tier Image OCR Extraction ---

def _get_pytesseract():
    """Detect and configure PyTesseract with standard Windows paths."""
    try:
        import pytesseract
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                pytesseract.pytesseract.tesseract_cmd = c
                break
        return pytesseract
    except Exception:
        return None

def _ocr_pytesseract(img_bytes):
    """Tier 1: Local PyTesseract OCR."""
    pyt = _get_pytesseract()
    if not pyt:
        return None
    try:
        img = _load_image_clean(img_bytes)
        data = pyt.image_to_data(img, output_type=pyt.Output.DICT)
        text = pyt.image_to_string(img)
        words = []
        for i in range(len(data.get('text', []))):
            t_word = data['text'][i].strip()
            if t_word:
                words.append({
                    'text': t_word,
                    'left': int(data['left'][i]),
                    'top': int(data['top'][i]),
                    'width': int(data['width'][i]),
                    'height': int(data['height'][i]),
                    'line': t_word
                })
        return {'text': text, 'words': words}
    except Exception:
        return None

def _ocr_space(img_bytes, filename="cv_img.jpg"):
    """Tier 2: OCR.space Free High-Accuracy API with Word Bounding Boxes."""
    import requests
    keys = ["K87899142388957", "helloworld"]
    for key in keys:
        try:
            payload = {
                'apikey': key,
                'language': 'eng',
                'isOverlayRequired': True,
                'detectOrientation': True,
                'scale': True,
                'OCREngine': 2
            }
            files = {'file': (filename, img_bytes, 'image/jpeg')}
            res = requests.post('https://api.ocr.space/parse/image', files=files, data=payload, timeout=12)
            if res.status_code == 200:
                d = res.json()
                if not d.get('IsErroredOnProcessing') and d.get('ParsedResults'):
                    p0 = d['ParsedResults'][0]
                    full_text = p0.get('ParsedText', '')
                    overlay = p0.get('TextOverlay', {})
                    lines = overlay.get('Lines', [])
                    words = []
                    for l in lines:
                        l_txt = l.get('LineText', '')
                        for w in l.get('Words', []):
                            words.append({
                                'text': w.get('WordText', ''),
                                'left': int(w.get('Left', 0)),
                                'top': int(w.get('Top', 0)),
                                'width': int(w.get('Width', 0)),
                                'height': int(w.get('Height', 0)),
                                'line': l_txt
                            })
                    if full_text.strip():
                        return {'text': full_text, 'words': words}
        except Exception:
            continue
    return None

def _ocr_google_vision(img_bytes):
    """Tier 3: Google Cloud Vision API using local credentials.json if enabled."""
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests
        import requests
        creds_path = os.path.join(BASE_DIR, "credentials.json")
        if not os.path.exists(creds_path):
            return None
        scopes = ['https://www.googleapis.com/auth/cloud-vision']
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        req = google.auth.transport.requests.Request()
        creds.refresh(req)
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        res = requests.post(
            "https://vision.googleapis.com/v1/images:annotate",
            headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
            json={"requests": [{"image": {"content": b64}, "features": [{"type": "TEXT_DETECTION"}]}]},
            timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            ann = data.get('responses', [{}])[0].get('textAnnotations', [])
            if ann:
                full_text = ann[0].get('description', '')
                words = []
                for a in ann[1:]:
                    verts = a.get('boundingPoly', {}).get('vertices', [])
                    if len(verts) >= 4:
                        xs = [v.get('x', 0) for v in verts]
                        ys = [v.get('y', 0) for v in verts]
                        l = min(xs); t = min(ys)
                        w = max(xs) - l; h = max(ys) - t
                        words.append({
                            'text': a.get('description', ''),
                            'left': int(l), 'top': int(t), 'width': int(w), 'height': int(h),
                            'line': a.get('description', '')
                        })
                return {'text': full_text, 'words': words}
    except Exception:
        pass
    return None

def extract_text_and_boxes_from_image(img_bytes, filename="cv.jpg"):
    """Multi-tier OCR pipeline for images."""
    res = _ocr_pytesseract(img_bytes)
    if res and res.get('text', '').strip():
        return res
    res = _ocr_space(img_bytes, filename)
    if res and res.get('text', '').strip():
        return res
    res = _ocr_google_vision(img_bytes)
    if res and res.get('text', '').strip():
        return res
    return {'text': '', 'words': []}

def redact_image_sensitive_data(img_bytes, sensitive_boxes, file_ext="jpg"):
    """
    Mask sensitive bounding boxes on image cleanly with matching background color.
    Returns: (cleaned_image_bytes, cleaned_pdf_bytes)
    """
    img = _load_image_clean(img_bytes)
    draw = ImageDraw.Draw(img)
    img_w, img_h = img.size

    for box in sensitive_boxes:
        left = max(0, int(box.get('left', 0)) - 4)
        top = max(0, int(box.get('top', 0)) - 3)
        right = min(img_w, int(box.get('left', 0) + box.get('width', 0)) + 4)
        bottom = min(img_h, int(box.get('top', 0) + box.get('height', 0)) + 3)

        if right <= left or bottom <= top:
            continue

        bg_color = (255, 255, 255)
        try:
            # Sample color from the edge to blend with original background
            sample_x = max(0, left - 6)
            sample_y = max(0, min(img_h - 1, top + (bottom - top) // 2))
            c = img.getpixel((sample_x, sample_y))
            if isinstance(c, tuple):
                bg_color = c[:3]
            elif isinstance(c, int):
                bg_color = (c, c, c)
        except Exception:
            bg_color = (255, 255, 255)

        draw.rectangle([left, top, right, bottom], fill=bg_color)

    # Output as Image bytes
    img_out = io.BytesIO()
    if file_ext.lower() in ['png', 'webp']:
        img.save(img_out, format='PNG')
    else:
        img.convert('RGB').save(img_out, format='JPEG', quality=95)
    cleaned_img_bytes = img_out.getvalue()

    # Output as PDF bytes (wraps clean image inside crisp PDF document)
    pdf_out = io.BytesIO()
    img.convert('RGB').save(pdf_out, format='PDF', quality=95)
    cleaned_pdf_bytes = pdf_out.getvalue()

    return cleaned_img_bytes, cleaned_pdf_bytes

# --- Main UI Function ---

def render_cv_privacy_cleaner_content():
    """CV Privacy Cleaner: Fully handles both PDF documents and all image files."""
    lang = st.session_state.lang
    is_ar = lang == 'ar'

    st.title("🔒 " + t("cv_privacy_title", lang))
    st.markdown(t("cv_privacy_desc", lang))
    st.divider()

    st.info("ℹ️ " + ("هذا القسم يدعم تنظيف ملفات PDF وجميع أنواع الصور (JPG, PNG, JPEG, WEBP, BMP) بالإضافة إلى ملفات وورد (DOCX) التي يتم تحويلها إلى PDF. يتم حذف أرقام الهواتف والإيميلات مع الحفاظ على التنسيق الأصلي والتصميم بالكامل، ويمكن عرض السيرة على ورقة الشركة (الخلفية المؤسسية)." if is_ar else "This tool supports PDF files and all image formats (JPG, PNG, JPEG, WEBP, BMP) plus Word files (DOCX) which are converted to PDF. Phone numbers and email addresses are cleanly removed while preserving original format and design, and the CV can be displayed on the company letterhead background."))
    if not FITZ_AVAILABLE:
        st.warning("⚠️ " + ("PyMuPDF (fitz) غير مثبت في هذه البيئة، لذا تنظيف PDF الذي يحافظ على التنسيق غير متوفر. يرجى استخدام تنظيف الصور أو تنظيف النص فقط." if is_ar else "PyMuPDF (fitz) is not installed in this environment."))

    # Background uploader section
    has_background = _render_background_uploader(is_ar)

    st.divider()

    # File uploader supporting PDF and ALL image formats
    uploaded_file = st.file_uploader(
        t("cv_upload_label", lang),
        type=["pdf"] + IMAGE_EXTS + DOC_EXTS,
        help=t("cv_upload_help", lang)
    )

    if uploaded_file is not None:
        file_ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
        is_pdf = file_ext == "pdf" or ('cv_pdf_bytes' in st.session_state and file_ext in DOC_EXTS)
        is_image = file_ext in IMAGE_EXTS
        is_doc = file_ext in DOC_EXTS

        # Clear old session state when a new CV file is uploaded.
        # IMPORTANT: do NOT clear anything in BG_KEYS so the uploaded
        # letterhead background and its margin/scale/align settings are kept.
        if st.session_state.get('cv_last_file_name') != uploaded_file.name:
            for k in [
                'cv_original_text', 'cv_cleaned_text', 'cv_phones_count', 'cv_emails_count',
                'cv_labels_count', 'cv_file_ext', 'cv_file_name', 'cv_last_file_name',
                'cv_pdf_bytes', 'cv_cleaned_pdf_bytes', 'cv_image_bytes',
                'cv_cleaned_image_bytes', 'cv_image_boxes', 'cv_detected_phones',
                'cv_detected_emails', 'cv_ocr_done',
                'cv_merged_img_bytes', 'cv_merged_pdf_bytes',
                'cv_extracted_img_bytes', 'cv_extracted_pdf_bytes',
                'cv_translated_text', 'cv_manual_text',
            ]:
                st.session_state.pop(k, None)

            st.session_state.cv_last_file_name = uploaded_file.name
            st.session_state.cv_file_ext = file_ext
            st.session_state.cv_file_name = uploaded_file.name

        raw_bytes = uploaded_file.getvalue()

        # Convert Word (.doc / .docx) to PDF so it can be cleaned & merged like a normal CV PDF
        if is_doc and DOCX_AVAILABLE and 'cv_pdf_bytes' not in st.session_state:
            with st.spinner("جاري تحويل ملف وورد إلى PDF..." if is_ar else "Converting Word file to PDF..."):
                conv_pdf_bytes, conv_text, convertible = doc_to_pdf(raw_bytes, uploaded_file.name)
                if convertible and conv_pdf_bytes:
                    st.session_state.cv_pdf_bytes = conv_pdf_bytes
                    st.session_state.cv_original_text = conv_text
                    is_pdf = True  # treat as PDF for the cleaning & merge flow below
                else:
                    if uploaded_file.name.lower().endswith(".doc"):
                        st.error(
                            "ملفات وورد القديمة (.doc) تتطلب تحويلها إلى صيغة .docx أولاً لوجود برنامج LibreOffice غير متوفر في هذا السيرفر. "
                            "يرجى فتح الملف في وورد وحفظه كملف Word (.docx) ثم إعادة رفعه." if is_ar else
                            "Legacy Word (.doc) files require saving as .docx first (LibreOffice is not available on this server). "
                            "Please open the file in Word and save it as Word (.docx), then re-upload."
                        )
                    else:
                        st.error("فشل تحويل ملف وورد إلى PDF" if is_ar else "Failed to convert Word file to PDF")

        if is_pdf and 'cv_pdf_bytes' not in st.session_state:
            st.session_state.cv_pdf_bytes = raw_bytes
        elif is_image:
            st.session_state.cv_image_bytes = raw_bytes

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📄 " + (t("cv_original_text", lang)))

            if is_pdf:
                try:
                    # Always try to extract text if not present or if empty
                    if 'cv_original_text' not in st.session_state or not st.session_state.get('cv_original_text', '').strip():
                        pdf_text = extract_text_from_pdf(io.BytesIO(raw_bytes))
                        st.session_state.cv_original_text = pdf_text
                        # Fallback: if pdfplumber returns empty, try fitz (PyMuPDF)
                        if not pdf_text.strip() and FITZ_AVAILABLE:
                            try:
                                doc = fitz.open(stream=raw_bytes, filetype="pdf")
                                fitz_text = ""
                                for page in doc:
                                    fitz_text += page.get_text()
                                doc.close()
                                if fitz_text.strip():
                                    st.session_state.cv_original_text = fitz_text
                            except:
                                pass
                    st.text_area("PDF Content", st.session_state.get('cv_original_text', ''), height=400, key="cv_original_pdf")
                except Exception as e:
                    st.error(t("cv_error", lang) + ": " + str(e))
            elif is_image:
                st.image(raw_bytes, caption=uploaded_file.name, use_container_width=True)

                # Run OCR extraction once per image
                if 'cv_ocr_done' not in st.session_state:
                    with st.spinner("جارٍ تحليل الصورة واستخراج النص... " if is_ar else "Analyzing image and extracting text..."):
                        ocr_data = extract_text_and_boxes_from_image(raw_bytes, uploaded_file.name)
                        st.session_state.cv_original_text = ocr_data.get('text', '')
                        st.session_state.cv_image_boxes = ocr_data.get('words', [])
                        st.session_state.cv_ocr_done = True

                # Pre-detect sensitive items in extracted text
                extracted_txt = st.session_state.get('cv_original_text', '')
                if extracted_txt.strip():
                    with st.expander("📝 " + ("النص المستخرج من الصورة" if is_ar else "Extracted Image Text"), expanded=False):
                        st.text_area("OCR Text", extracted_txt, height=220, key="cv_original_ocr", disabled=True)

                    _, pre_phones, pre_emails, _ = remove_emails_and_phones_from_text(extracted_txt)
                    st.session_state.cv_detected_phones = pre_phones
                    st.session_state.cv_detected_emails = pre_emails

                    if pre_phones or pre_emails:
                        details = []
                        if pre_phones:
                            details.append(f"📞 {len(pre_phones)} " + ("هاتف" if is_ar else "phones"))
                        if pre_emails:
                            details.append(f"✉️ {len(pre_emails)} " + ("إيميل" if is_ar else "emails"))
                        st.warning("⚠️ " + ("تم رصد بيانات حساسة بالصورة: " if is_ar else "Sensitive data detected: ") + " | ".join(details))
                    else:
                        st.info("ℹ️ " + ("تم استخراج النص من الصورة بنجاح." if is_ar else "Text extracted successfully."))
                else:
                    st.info("ℹ️ " + ("الصورة جاهزة للتنظيف. اضغط على زر 'تنظيف الملف' باليسار لتنظيفها وتحميلها بصيغة صورة أو PDF." if is_ar else "Image ready for cleaning. Click Clean File to process."))

                # Optional custom keyword mask
                with st.expander("🛠️ " + ("حذف كلمات أو أرقام إضافية يدوياً (اختياري)" if is_ar else "Manual removal options (optional)"), expanded=False):
                    st.text_input(
                        "أدخل أي رقم هاتف أو إيميل إضافي ترغب بحذفه من الصورة" if is_ar else "Enter phone or email to redact",
                        key="cv_manual_custom_input",
                        placeholder="+9665... أو user@gmail.com"
                    )

        with col2:
            st.subheader("✨ " + (t("cv_cleaned_text", lang)))

            # Clear / Reset button
            if st.button("🗑️ " + ("مسح البيانات وبدء جديد" if is_ar else "Clear & Start Fresh"), width='stretch', key="cv_clear_btn"):
                for k in [
                    'cv_original_text', 'cv_cleaned_text', 'cv_phones_count', 'cv_emails_count',
                    'cv_labels_count', 'cv_file_ext', 'cv_file_name', 'cv_last_file_name',
                    'cv_pdf_bytes', 'cv_cleaned_pdf_bytes', 'cv_image_bytes',
                    'cv_cleaned_image_bytes', 'cv_image_boxes', 'cv_detected_phones',
                    'cv_detected_emails', 'cv_ocr_done',
                    'cv_merged_img_bytes', 'cv_merged_pdf_bytes',
                    'cv_extracted_img_bytes', 'cv_extracted_pdf_bytes',
                    'cv_translated_text', 'cv_manual_text',
                    'cv_bg_header_px', 'cv_bg_footer_px', 'cv_bg_left_cm', 'cv_bg_right_cm',
                ] + BG_KEYS:
                    st.session_state.pop(k, None)
                st.rerun()

            # Clean File Button
            if st.button(t("cv_clean_btn", lang), type="primary", width='stretch', key="cv_clean_btn"):
                if is_pdf and 'cv_pdf_bytes' in st.session_state:
                    if not FITZ_AVAILABLE:
                        st.error("مكتبة PyMuPDF (fitz) غير مثبتة في هذه البيئة، لذا التنظيف الذي يحفظ تنسيق PDF غير متاح." if is_ar else "PyMuPDF (fitz) is not installed in this environment.")
                    else:
                        try:
                            cleaned_pdf_bytes, email_count, phone_count = clean_pdf_preserve_format(st.session_state.cv_pdf_bytes)
                            st.session_state.cv_cleaned_pdf_bytes = cleaned_pdf_bytes
                            st.session_state.cv_emails_count = email_count
                            st.session_state.cv_phones_count = phone_count

                            # Try to extract text if not already present
                            if not st.session_state.get('cv_original_text', '').strip():
                                pdf_text = extract_text_from_pdf(io.BytesIO(st.session_state.cv_pdf_bytes))
                                if not pdf_text.strip() and FITZ_AVAILABLE:
                                    try:
                                        doc = fitz.open(stream=st.session_state.cv_pdf_bytes, filetype="pdf")
                                        fitz_text = ""
                                        for page in doc:
                                            fitz_text += page.get_text()
                                        doc.close()
                                        if fitz_text.strip():
                                            pdf_text = fitz_text
                                    except:
                                        pass
                                st.session_state.cv_original_text = pdf_text

                            if st.session_state.get('cv_original_text'):
                                c_txt, _, _, l_found = remove_emails_and_phones_from_text(st.session_state.cv_original_text)
                                st.session_state.cv_cleaned_text = c_txt
                                st.session_state.cv_labels_count = len(l_found)
                            st.success(t("cv_cleaned_success", lang))
                        except Exception as e:
                            st.error("خطأ في تنظيف PDF: " + str(e) if is_ar else "Error cleaning PDF: " + str(e))

                elif is_image and 'cv_image_bytes' in st.session_state:
                    try:
                        img_bytes = st.session_state.cv_image_bytes
                        boxes = st.session_state.get('cv_image_boxes', [])
                        orig_text = st.session_state.get('cv_original_text', '')
                        known_phones = st.session_state.get('cv_detected_phones', [])
                        known_emails = st.session_state.get('cv_detected_emails', [])

                        sensitive_boxes = []
                        phones_found = list(known_phones)
                        emails_found = list(known_emails)
                        labels_found = []

                        # Match word boxes
                        for w in boxes:
                            txt = w.get('text', '').strip()
                            line = w.get('line', '').strip()

                            # Check email
                            em = re.findall(EMAIL_PATTERN, txt) or re.findall(EMAIL_PATTERN, line)
                            if em:
                                sensitive_boxes.append(w)
                                emails_found.extend(em)
                                continue

                            # Check phone regex
                            is_p = False
                            for pat in PHONE_PATTERNS:
                                pm = re.findall(pat, txt) or re.findall(pat, line)
                                if pm:
                                    sensitive_boxes.append(w)
                                    phones_found.extend(pm)
                                    is_p = True
                                    break
                            if is_p:
                                continue

                            # Check phone by digit sequence
                            txt_digits = re.sub(r'\D', '', txt)
                            if len(txt_digits) >= 6:
                                for kp in known_phones:
                                    kp_digits = re.sub(r'\D', '', kp)
                                    if kp_digits and (kp_digits in txt_digits or txt_digits in kp_digits):
                                        sensitive_boxes.append(w)
                                        is_p = True
                                        break
                            if is_p:
                                continue

                            # Check labels
                            for lab_pat in LABEL_PATTERNS:
                                if re.search(lab_pat, txt, re.IGNORECASE):
                                    sensitive_boxes.append(w)
                                    labels_found.append(txt)
                                    break

                        # Check manual user input
                        manual_kw = st.session_state.get('cv_manual_custom_input', '').strip()
                        if manual_kw:
                            for kw in [k.strip() for k in re.split(r'[,\s]+', manual_kw) if k.strip()]:
                                for w in boxes:
                                    if kw.lower() in w.get('text', '').lower() or kw.lower() in w.get('line', '').lower():
                                        if w not in sensitive_boxes:
                                            sensitive_boxes.append(w)
                                        if any(ch.isdigit() for ch in kw) and kw not in phones_found:
                                            phones_found.append(kw)
                                        elif '@' in kw and kw not in emails_found:
                                            emails_found.append(kw)

                        # Clean image and generate both Image and PDF outputs
                        cleaned_img, cleaned_pdf = redact_image_sensitive_data(
                            img_bytes, sensitive_boxes, file_ext=file_ext
                        )

                        st.session_state.cv_cleaned_image_bytes = cleaned_img
                        st.session_state.cv_cleaned_pdf_bytes = cleaned_pdf

                        if orig_text:
                            c_txt, p_l, e_l, l_l = remove_emails_and_phones_from_text(orig_text)
                            st.session_state.cv_cleaned_text = c_txt
                            phones_found.extend(p_l)
                            emails_found.extend(e_l)
                            labels_found.extend(l_l)

                        st.session_state.cv_phones_count = len(set(phones_found))
                        st.session_state.cv_emails_count = len(set(emails_found))
                        st.session_state.cv_labels_count = len(set(labels_found))

                        st.success(t("cv_cleaned_success", lang))
                    except Exception as e:
                        st.error(f"خطأ أثناء تنظيف الصورة: {str(e)}" if is_ar else f"Error cleaning image: {str(e)}")

                elif st.session_state.get('cv_original_text'):
                    cleaned_text, phones, emails, labels = remove_emails_and_phones_from_text(st.session_state.cv_original_text)
                    st.session_state.cv_cleaned_text = cleaned_text
                    st.session_state.cv_phones_count = len(phones)
                    st.session_state.cv_emails_count = len(emails)
                    st.session_state.cv_labels_count = len(labels)
                    st.success(t("cv_cleaned_success", lang))
                else:
                    st.warning("الرجاء رفع ملف أولاً" if is_ar else "Please upload a file first")

            # --- Display Results & Download Options ---
            if 'cv_cleaned_image_bytes' in st.session_state:
                st.image(st.session_state.cv_cleaned_image_bytes, caption="معاينة الصورة بعد التنظيف" if is_ar else "Cleaned Image Preview", use_container_width=True)

                # Stats metrics
                c_stats1, c_stats2, c_stats3 = st.columns(3)
                with c_stats1:
                    st.metric(t("cv_phones_removed", lang), st.session_state.get('cv_phones_count', 0))
                with c_stats2:
                    st.metric(t("cv_emails_removed", lang), st.session_state.get('cv_emails_count', 0))
                with c_stats3:
                    st.metric("التسميات المحذوفة" if is_ar else "Labels removed", st.session_state.get('cv_labels_count', 0))

                # Download Buttons
                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    clean_img_fn = "cleaned_" + st.session_state.get('cv_file_name', 'cv.jpg')
                    mime_typ = f"image/{file_ext if file_ext in ['png', 'webp', 'bmp'] else 'jpeg'}"
                    st.download_button(
                        label="⬇️ " + ("تحميل الصورة بعد التنظيف" if is_ar else "Download Cleaned Image"),
                        data=st.session_state.cv_cleaned_image_bytes,
                        file_name=clean_img_fn,
                        mime=mime_typ,
                        width='stretch',
                        key="cv_dl_clean_img"
                    )
                with d_col2:
                    base_raw = os.path.splitext(st.session_state.get('cv_file_name', 'cv'))[0]
                    clean_pdf_fn = f"cleaned_{base_raw}.pdf"
                    st.download_button(
                        label="⬇️ " + ("تحميل كملف PDF" if is_ar else "Download as PDF"),
                        data=st.session_state.cv_cleaned_pdf_bytes,
                        file_name=clean_pdf_fn,
                        mime="application/pdf",
                        width='stretch',
                        key="cv_dl_clean_img_pdf"
                    )

                if st.session_state.get('cv_cleaned_text'):
                    with st.expander("📄 " + ("النص بعد التنظيف" if is_ar else "Cleaned Text Preview")):
                        st.text_area("Cleaned Text", st.session_state.cv_cleaned_text, height=200, key="cv_clean_txt_prev", disabled=True)
                        st.download_button(
                            label="⬇️ " + ("تحميل النص المنظف (.txt)" if is_ar else "Download Text (.txt)"),
                            data=st.session_state.cv_cleaned_text.encode('utf-8'),
                            file_name=f"cleaned_{base_raw}.txt",
                            mime="text/plain",
                            width='stretch',
                            key="cv_dl_clean_txt_from_img"
                        )

                    # AI Translation to Arabic (smart, not literal)
                    if st.session_state.get('cv_cleaned_text'):
                        tr_col1, tr_col2 = st.columns([1, 1])
                        with tr_col1:
                            if st.button(
                                "🤖 " + t("cv_translate_ai_label", lang),
                                key="cv_translate_ai_btn",
                                width='stretch',
                            ):
                                with st.spinner(t("translating_wait", lang)):
                                    result = translate_text_to_arabic_ai(st.session_state.cv_cleaned_text)
                                    st.session_state.cv_translated_text = result['text']
                                    st.session_state.cv_translated_success = result['success']
                                    if result['success']:
                                        st.success(t("translation_complete", lang))
                                    else:
                                        st.warning("⚠️ " + ("تعذر الترجمة تلقائياً. يمكنك تعديل النص أدناه يدوياً." if is_ar else "Automatic translation failed. You can edit the text below manually."))
                        with tr_col2:
                            if st.session_state.get('cv_translated_text'):
                                st.download_button(
                                    label="⬇️ " + t("cv_download_translated", lang),
                                    data=st.session_state.cv_translated_text.encode('utf-8'),
                                    file_name=f"translated_{base_raw}.txt",
                                    mime="text/plain",
                                    width='stretch',
                                    key="cv_dl_translated_txt"
                                )

                        # Display translated (or editable) text
                        if st.session_state.get('cv_translated_text'):
                            st.markdown("---")
                            st.subheader("🌐 " + t("cv_translated_title", lang))
                            st.text_area(
                                "Translated Text",
                                st.session_state.cv_translated_text,
                                height=200,
                                key="cv_translated_txt_prev",
                            )
                            st.caption("ℹ️ " + ("يمكنك تعديل النص يدوياً إذا لم تنجح الترجمة الآلية" if is_ar else "You can edit the text manually if automatic translation fails"))

            elif 'cv_cleaned_pdf_bytes' in st.session_state and is_pdf:
                clean_filename = "cleaned_" + st.session_state.get('cv_file_name', 'cv.pdf')
                st.download_button(
                    label="⬇️ " + t("cv_download_btn", lang),
                    data=st.session_state.cv_cleaned_pdf_bytes,
                    file_name=clean_filename,
                    mime="application/pdf",
                    width='stretch',
                    key="cv_download_cleaned_pdf"
                )
                st.info("ℹ️ " + ("تم حفظ PDF مع الحفاظ على الصور والتنسيق الأصلي. الإيميلات وأرقام الهواتف محذوفة." if is_ar else "PDF saved preserving images and original format. Emails and phone numbers removed."))

                base_raw = os.path.splitext(st.session_state.get('cv_file_name', 'cv.pdf'))[0]

                # Show cleaned text if available
                if st.session_state.get('cv_cleaned_text'):
                    with st.expander("📄 " + ("النص بعد التنظيف" if is_ar else "Cleaned Text Preview")):
                        st.text_area("Cleaned Text", st.session_state.cv_cleaned_text, height=200, key="cv_clean_txt_prev_pdf", disabled=True)
                        st.download_button(
                            label="⬇️ " + ("تحميل النص المنظف (.txt)" if is_ar else "Download Text (.txt)"),
                            data=st.session_state.cv_cleaned_text.encode('utf-8'),
                            file_name=f"cleaned_{base_raw}.txt",
                            mime="text/plain",
                            width='stretch',
                            key="cv_dl_clean_txt_from_pdf"
                        )

                # AI Translation to Arabic (smart, not literal) — for PDF cleaned text
                if st.session_state.get('cv_cleaned_text'):
                    st.markdown("---")
                    tr_col1, tr_col2 = st.columns([1, 1])
                    with tr_col1:
                        if st.button(
                            "🤖 " + t("cv_translate_ai_label", lang),
                            key="cv_translate_ai_btn_pdf",
                            width='stretch',
                        ):
                            with st.spinner(t("translating_wait", lang)):
                                result = translate_text_to_arabic_ai(st.session_state.cv_cleaned_text)
                                st.session_state.cv_translated_text = result['text']
                                st.session_state.cv_translated_success = result['success']
                                if result['success']:
                                    st.success(t("translation_complete", lang))
                                else:
                                    st.warning("⚠️ " + ("تعذر الترجمة تلقائياً. يمكنك تعديل النص أدناه يدوياً." if is_ar else "Automatic translation failed. You can edit the text below manually."))
                    with tr_col2:
                        if st.session_state.get('cv_translated_text'):
                            st.download_button(
                                label="⬇️ " + t("cv_download_translated", lang),
                                data=st.session_state.cv_translated_text.encode('utf-8'),
                                file_name=f"translated_{base_raw}.txt",
                                mime="text/plain",
                                width='stretch',
                                key="cv_dl_translated_txt_pdf"
                            )

                    # Display translated (or editable) text
                    if st.session_state.get('cv_translated_text'):
                        st.markdown("---")
                        st.subheader("🌐 " + t("cv_translated_title", lang))
                        st.text_area(
                            "Translated Text",
                            st.session_state.cv_translated_text,
                            height=200,
                            key="cv_translated_txt_prev_pdf",
                        )
                        st.caption("ℹ️ " + ("يمكنك تعديل النص يدوياً إذا لم تنجح الترجمة الآلية" if is_ar else "You can edit the text manually if automatic translation fails"))

        # Show merge section if both cleaned CV and background exist
        if has_background and ('cv_cleaned_image_bytes' in st.session_state or 'cv_cleaned_pdf_bytes' in st.session_state):
            _render_merge_section(is_ar)
