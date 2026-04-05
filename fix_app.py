# Fix script - run this to fix app.py syntax error
import os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
print(f"Reading: {path}")

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print(f"Total lines: {len(lines)}")
print(f"Line 1832 preview: {repr(lines[1831][:40])}...")

# Find and fix the corrupted section
# Line 1832 (index 1831) is corrupted, and lines 1833-1864 are duplicates
# We need to keep lines up to 1831, replace 1832 with "return text", skip 1833-1864
fixed_lines = lines[:1831]  # Keep up to line 1831 (pass)
fixed_lines.append('            return text')  # Fix line 1832
fixed_lines.extend(lines[1864:])  # Skip duplicates, continue from 1865

fixed_content = '\n'.join(fixed_lines)

with open(path, 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print(f"Fixed! New total lines: {len(fixed_lines)}")
print("Syntax error should be resolved now.")
