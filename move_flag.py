import re

with open("c:/Users/ا/Desktop/non2/app.py", "r", encoding="utf-8") as f:
    code = f.read()

# The original line:
# styled_df.insert(idx, flag_col, styled_df[col].apply(get_flag_url))

# We want to change it to idx + 1
new_code = code.replace(
    "styled_df.insert(idx, flag_col, styled_df[col].apply(get_flag_url))",
    "styled_df.insert(idx + 1, flag_col, styled_df[col].apply(get_flag_url))"
)

# And change the comment to be accurate
new_code = new_code.replace(
    "# Position flag before nationality",
    "# Position flag after nationality (which is 'before' in RTL)"
)

# Also check for __apply_pinned_columns, to make sure the pin order doesn't get messed up.
# Actually, the dataframe column order dictates the order of pinned columns.

with open("c:/Users/ا/Desktop/non2/app.py", "w", encoding="utf-8") as f:
    f.write(new_code)

print("Changed flag position to idx + 1")
