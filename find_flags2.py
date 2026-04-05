with open("c:/Users/ا/Desktop/non2/app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
with open("c:/Users/ا/Desktop/non2/flag_lines.txt", "w", encoding="utf-8") as out:
    for i, l in enumerate(lines):
        if 'flagcdn' in l or 'flag' in l.lower() and 'img' in l.lower():
            out.write(f"{i+1}: {l.strip()}\n")
