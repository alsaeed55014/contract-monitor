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
    "بنت باريستا فلبينيه",
    "ولد باريستا فلبيني",
    "باريستا افريقي",
    "عاملة نظافة افريقيه",
    "شيف مطعم ايطالي",
    "سكرتيرة",
    "بدكير ومنكير",
    "فني كاميرا",
    "أعمال مكتبيه"
]

for q in test_queries:
    bundles = tm.analyze_query(q)
    print(f"Query: {q}")
    print(f"Bundles: {bundles}")
    print("-" * 30)
