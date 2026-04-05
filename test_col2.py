import streamlit as st
col = st.column_config.ImageColumn("Flag", width="small")
print(type(col))
try:
    if isinstance(col, dict):
        col["pinned"] = True
        print("Success setting as dict")
    else:
        print("Not a dict")
except Exception as e:
    print("Error:", e)
