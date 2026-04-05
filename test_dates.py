from dateutil import parser
import pandas as pd

v1 = '2026/02/16 PM 3:30:43'
v2 = '2026/02/16 3:30:43 PM'
v3 = '2026/02/16 AM 3:30:43'

formats = [v1, v2, v3]
for f in formats:
    try:
        print(f"'{f}' -> {parser.parse(f)}")
    except Exception as e:
        print(f"'{f}' failed: {e}")

# Test with pd.to_datetime too
for f in formats:
    try:
        print(f"PD '{f}' -> {pd.to_datetime(f)}")
    except Exception as e:
        print(f"PD '{f}' failed: {e}")
