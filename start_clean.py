import streamlit as st
import os

st.set_page_config(page_title="Test App", layout="wide")

st.title("🚀 اختبار تشغيل النظام")
st.success("إذا ظهرت لك هذه الرسالة، فهذا يعني أن Streamlit يعمل بنجاح!")

st.write("المسار الحالي للمشروع:")
st.code(os.getcwd())

if st.button("اضغط هنا لتجربة التفاعل"):
    st.balloons()
    st.write("التفاعل يعمل!")
