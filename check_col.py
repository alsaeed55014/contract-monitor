import streamlit as st
import inspect
with open("c:/Users/ا/Desktop/non2/check_col_output.txt", "w", encoding="utf-8") as f:
    f.write(str(inspect.signature(st.column_config.Column)))
