with open("c:/Users/ا/Desktop/non2/app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
with open("c:/Users/ا/Desktop/non2/empty_blocks.txt", "w", encoding="utf-8") as out:
    for i, l in enumerate(lines):
        if ('Flag Image' in l or 'flag' in l.lower()) and ('Configuration' in l or 'config' in l.lower()):
            # Show context around it
            for j in range(max(0, i-1), min(len(lines), i+5)):
                out.write(f"{j+1}: {lines[j].rstrip()}\n")
            out.write("---\n")
