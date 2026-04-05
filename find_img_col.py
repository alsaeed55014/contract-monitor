with open("c:/Users/ا/Desktop/non2/app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
with open("c:/Users/ا/Desktop/non2/image_col_lines2.txt", "w", encoding="utf-8") as out:
    for i, l in enumerate(lines):
        if 'ImageColumn' in l:
            out.write(f"{i+1}: {l.strip()}\n")
        if '🚩_' in l and 'ImageColumn' not in l:
            out.write(f"{i+1}: {l.strip()}\n")
