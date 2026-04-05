import re

with open("c:/Users/ا/Desktop/non2/app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Pattern: empty for/if blocks for flag nationality config
# These create empty col_cfg dicts then have empty for/if loops
patterns = [
    # Pattern 1: col_cfg_X = {} then empty for/if
    (r'                        col_cfg_city = \{\}\r?\n                        for col in city_df\.columns:\r?\n                            if any\(kw in str\(col\)\.lower\(\) for kw in \["nationality", "الجنسية"\]\):\r?\n',
     '                        col_cfg_city = {}\r\n'),
    (r'                        col_cfg_reg = \{\}\r?\n                        for col in reg_df\.columns:\r?\n                            if any\(kw in str\(col\)\.lower\(\) for kw in \["nationality", "الجنسية"\]\):\r?\n',
     '                        col_cfg_reg = {}\r\n'),
    (r'                        col_cfg_oth = \{\}\r?\n                        for col in other_df\.columns:\r?\n                            if any\(kw in str\(col\)\.lower\(\) for kw in \["nationality", "الجنسية"\]\):\r?\n',
     '                        col_cfg_oth = {}\r\n'),
    (r'                    col_cfg_match = \{\}\r?\n                    for col in match_df\.columns:\r?\n                        if any\(kw in str\(col\)\.lower\(\) for kw in \["nationality", "الجنسية"\]\):\r?\n',
     '                    col_cfg_match = {}\r\n'),
    (r'                    col_cfg_b = \{\}\r?\n                    for col in df_bengali_search\.columns:\r?\n                        if any\(kw in str\(col\)\.lower\(\) for kw in \["nationality", "الجنسية"\]\):\r?\n',
     '                    col_cfg_b = {}\r\n'),
]

for pat, repl in patterns:
    content = re.sub(pat, repl, content)

with open("c:/Users/ا/Desktop/non2/app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed empty for/if blocks!")
