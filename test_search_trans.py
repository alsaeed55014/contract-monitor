import sys
sys.path.insert(0, "c:/Users/ا/Desktop/non2")
from src.core.translation import TranslationManager

tm = TranslationManager()

test_queries = [
    "مصفف شعر",       
    "مصفف",           
    "مصففة شعر",      
    "كوافيرة",        
    "سائق",           
    "فلبيني سائق",    
    "نجار",           
    "كهربائي",        
    "خياط",           
]

with open("c:/Users/ا/Desktop/non2/test_result.txt", "w", encoding="utf-8") as f:
    for q in test_queries:
        bundles = tm.analyze_query(q)
        f.write(f"  '{q}' => {bundles}\n\n")
print("Done!")
