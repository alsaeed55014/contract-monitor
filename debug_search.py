import sys
import os
sys.path.insert(0, r'c:\Users\ا\Desktop\non')

# Simulate the exact Streamlit flow
import pandas as pd
from src.core.search import SmartSearchEngine

# Simulating: let's check if the issue is related to the search function
# being called with an empty query on a re-run
print("=== Simulating Streamlit behavior ===")

# Case 1: query is empty string (Streamlit default)
print("\nCase 1: Empty query string")
test_data = pd.DataFrame({
    '__sheet_row': [2, 3, 4, 5],
    'Full Name:': ['Ahmad', 'Maria', 'John', 'Sarah'],
    'Which job are you looking for': ['Driver', 'Barista', 'Chef', 'Waitress'],
    '__sheet_row_backup': [2, 3, 4, 5],
})
eng = SmartSearchEngine(test_data)
res = eng.search("")  # empty string
print(f"  Results: {len(res)} / {len(test_data)} (Expected: ALL)")

# Case 2: query is "شيف"
print("\nCase 2: Query = شيف")
res = eng.search("شيف")
print(f"  Results: {len(res)} / {len(test_data)} (Expected: 1)")

# Case 3: Let's check if the Streamlit text_input returns something weird
# After clicking button, Streamlit reruns. What if query is somehow empty?
print("\nCase 3: Checking query truthiness")
for q in ["شيف", "", None, " ", "  "]:
    print(f"  query='{q}', bool={bool(q)}, stripped_bool={bool(str(q).strip()) if q else False}")

# Case 4: Let's test with actual data structure from DB
print("\nCase 4: Testing with DBClient-like data")
# The DB client adds __sheet_row as first column
test_data2 = pd.DataFrame({
    '__sheet_row': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    'Full Name:': ['Ahmad', 'Maria', 'John', 'Sarah', 'Ali', 'Fatima', 'Omar', 'Lina', 'Hassan', 'Rosa'],
    'Nationality': ['Saudi', 'Filipino', 'American', 'Korean', 'Saudi', 'Saudi', 'Saudi', 'Filipino', 'Pakistani', 'Filipino'],
    'Gender': ['Male', 'Female', 'Male', 'Female', 'Male', 'Female', 'Male', 'Female', 'Male', 'Female'],
    'Phone Number': ['0501234567', '0594223552', '0551112222', '0559998888', '0507777777', '0508888888', '0509999999', '0501010101', '0502020202', '0503030303'],
    'Which job are you looking for': ['Driver', 'Barista', 'Chef', 'Waitress', 'Cleaner', 'Cook', 'Driver', 'Salon', 'Barista', 'Housemaid'],
    '__sheet_row_backup': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
})

eng2 = SmartSearchEngine(test_data2)

queries = ["شيف", "باريستا", "فلبيني", "+966 59 422 3552", "Ahmad", "Driver"]
for q in queries:
    res = eng2.search(q)
    print(f"  Query '{q}': {len(res)}/{len(test_data2)} rows")
    if len(res) > 0 and len(res) < len(test_data2):
        print(f"    Matched: {res['Full Name:'].tolist()}")
