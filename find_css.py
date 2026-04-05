with open("c:/Users/ا/Desktop/non2/app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
with open("c:/Users/ا/Desktop/non2/css_inject.txt", "w", encoding="utf-8") as out:
    for i, l in enumerate(lines):
        if 'st.markdown' in l and '<style>' in l:
            out.write(f"{i+1}: {l.strip()[:100]}\n")
        elif '<style>' in l:
            out.write(f"{i+1}: {l.strip()[:100]}\n")
