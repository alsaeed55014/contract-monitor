import streamlit as st

col = st.column_config.ImageColumn("Flag", width="small")
print(col)
try:
    col.pinned = True
    print("Success, pinned =", col.pinned)
except Exception as e:
    print("Error:", e)
