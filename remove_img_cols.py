import re

with open("c:/Users/ا/Desktop/non2/app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Remove all lines that set up ImageColumn for flag columns
# These are standalone lines like: col_cfg[f"🚩_{col}"] = st.column_config.ImageColumn(...)
# Also remove the for loop that iterates to create them

new_lines = []
skip_next = False
i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    
    # Check if this is a for loop that creates flag ImageColumn configs
    # Pattern: for col in X.columns: + if any(kw... nationality) + cfg[🚩_col] = ImageColumn
    if 'ImageColumn' in stripped and '🚩_' in stripped:
        # Check if previous lines are the for/if pair
        # Remove the for loop (2 lines before) + if check (1 line before) + this line
        # But we need to be careful - check the context
        
        # Look back to find the for/if block
        lookback = min(i, 4)
        block_start = i
        for j in range(i-1, max(i-5, -1), -1):
            prev = lines[j].strip()
            if prev.startswith('for col in') and 'columns' in prev:
                block_start = j
                break
            elif prev.startswith('if any(kw'):
                block_start = j
                # Keep looking for the for loop
        
        # Remove from block_start to i (inclusive)
        # But only remove lines that are part of this flag config block
        removed = False
        for j in range(block_start, i+1):
            check = lines[j].strip()
            if ('for col in' in check and ('nationality' in check or 'columns' in check)) or \
               ('if any(kw' in check and ('nationality' in check or 'الجنسية' in check)) or \
               ('ImageColumn' in check and '🚩_' in check):
                # Mark for removal - don't add to new_lines
                pass
            else:
                new_lines.append(lines[j])
        removed = True
        
        if not removed:
            new_lines.append(line)
        i += 1
        continue
    
    # Also skip the 🚩_ reference in style subset filter - update it
    if '🚩_' in stripped and 'startswith' in stripped and 'subset' in stripped:
        # This line filters out 🚩_ columns from styling - we can simplify it now
        # but flag emojis are now in the nationality column itself, so we can keep the filter
        new_lines.append(line)
        i += 1
        continue
    
    new_lines.append(line)
    i += 1

with open("c:/Users/ا/Desktop/non2/app.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"Done! Removed flag ImageColumn configs. Lines: {len(lines)} -> {len(new_lines)}")
