import sys
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'st.dataframe' in line or 'st.data_editor' in line or 'st.table' in line:
        print(f"Line {i+1}: {line.strip()}")
