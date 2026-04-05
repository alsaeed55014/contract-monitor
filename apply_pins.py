import re

with open("c:/Users/ا/Desktop/non2/app.py", "r", encoding="utf-8") as f:
    code = f.read()

helper_func = """
def __apply_pinned_columns(df_or_style, cfg=None):
    if cfg is None: cfg = {}
    import streamlit as st
    pin_keywords = [
        "حالة العقد", "contract status", "status",
        "وقت", "طابع", "timestamp", "registration",
        "الاسم", "name", 
        "جنسية", "nationality", "🚩",
        "جنس", "gender", "النوع"
    ]
    
    # Handle both DataFrame and Styler
    if hasattr(df_or_style, 'data'):
        cols = df_or_style.data.columns
    elif hasattr(df_or_style, 'columns'):
        cols = df_or_style.columns
    else:
        return cfg
        
    for col in cols:
        col_str = str(col).lower()
        should_pin = any(kw in col_str for kw in pin_keywords)
        if should_pin:
            if col not in cfg:
                cfg[col] = st.column_config.Column(pinned=True)
            else:
                try:
                    # Modify existing column config safely
                    existing = cfg[col]
                    if isinstance(existing, dict):
                        existing["pinned"] = True
                    else:
                        # For streamlit object like ImageColumn
                        existing_dict = getattr(existing, "__dict__", {})
                        if "pinned" in existing_dict or hasattr(existing, "pinned"):
                            existing.pinned = True
                        else:
                            # Recreate if setting fails
                            pass
                except:
                    pass
    return cfg
"""

if "__apply_pinned_columns" not in code:
    code = code.replace("def render_dashboard_content():", helper_func + "\ndef render_dashboard_content():")

# Replace dashboard
code = re.sub(r'column_config=final_cfg,', r'column_config=__apply_pinned_columns(styled_final, final_cfg),', code)
# Replace search
code = re.sub(r'column_config=column_config,', r'column_config=__apply_pinned_columns(style_df(res_display), column_config),', code)
# Replace bengali
code = re.sub(r'column_config=col_cfg_b\)', r'column_config=__apply_pinned_columns(df_bengali_search, col_cfg_b))', code)

# Replace order processing columns configs
code = re.sub(r'column_config=col_cfg_city,', r'column_config=__apply_pinned_columns(df_city, col_cfg_city),', code)
code = re.sub(r'column_config=col_cfg_reg,', r'column_config=__apply_pinned_columns(df_reg, col_cfg_reg),', code)
code = re.sub(r'column_config=col_cfg_other,', r'column_config=__apply_pinned_columns(df_other, col_cfg_other),', code)

# For those missing column_config
code = re.sub(r'st\.dataframe\(style_df\(df_users\), use_container_width=True\)', r'st.dataframe(style_df(df_users), use_container_width=True, column_config=__apply_pinned_columns(style_df(df_users)))', code)

with open("c:/Users/ا/Desktop/non2/app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Modifications done!")
