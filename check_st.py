import streamlit as st
try:
    print("HtmlColumn exists:", hasattr(st.column_config, "HtmlColumn"))
    print("Streamlit version:", st.__version__)
except Exception as e:
    print("Error:", e)
