import sys
import os

# Add the project root to sys.path
sys.path.append(r'c:\Users\ا\Desktop\non')

try:
    from src.core.translation import TranslationManager
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

tm = TranslationManager()

test_queries = [
    "بنت باريستا فلبينية",
    "ولد باريستا فلبيني",
    "باريستا أفريقي",
    "عاملة نظافة أفريقية",
    "شيف مطعم إيطالي",
    "شيف حلا",
    "خادمة منزلية",
    "مصففة شعر",
    "بدكير ومنكير",
    "عامل PPF",
    "نادلة بنت فلبينية",
    "نادل ذكر",
    "جميع الدول الأفريقية"
]

for q in test_queries:
    bundles = tm.analyze_query(q)
    print(f"Query: {q}")
    print(f"Bundles: {bundles}")
    print("-" * 30)
