import streamlit as st
import os
import json
from datetime import datetime
from src.utils.data_utils import find_matching_column, get_flag_emoji, safe_value

def check_notifications():
    """Checks for new worker entries or customer requests and synchronizes UI data."""
    if 'db' not in st.session_state or not st.session_state.user:
        return

    # initialize session state
    if 'notifications' not in st.session_state: st.session_state.notifications = []
    if 'notif_last_worker_count' not in st.session_state: st.session_state.notif_last_worker_count = None
    if 'notif_last_cust_count' not in st.session_state: st.session_state.notif_last_cust_count = None
    if 'notif_triggered' not in st.session_state: st.session_state.notif_triggered = False

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    STATE_FILE = os.path.join(BASE_DIR, "state.json")
    
    try:
        disk_state = {}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    disk_state = json.load(f)
            except: pass

        df_workers = st.session_state.db.fetch_data(is_notif_check=True)
        current_worker_count = len(df_workers)
        
        last_worker_count = st.session_state.get('notif_last_worker_count')
        if last_worker_count is None:
            last_worker_count = disk_state.get('last_row_candidates')
            
        if last_worker_count is not None and current_worker_count > last_worker_count:
            new_rows = df_workers.tail(current_worker_count - last_worker_count)
            c_name = find_matching_column(df_workers, ['Full Name', 'الاسم'], flexible_arabic=True)
            c_nat = find_matching_column(df_workers, ['Nationality', 'الجنسية'], flexible_arabic=True)
            c_phone = find_matching_column(df_workers, ['Phone Number', 'رقم الهاتف', 'هاتف'], flexible_arabic=True)
            c_job = find_matching_column(df_workers, ['Which job are you looking for', 'الوظيفة'], flexible_arabic=True)
            c_gender = find_matching_column(df_workers, ['Gender', 'الجنس'], flexible_arabic=True)

            for _, row in new_rows.iterrows():
                name = safe_value(row, c_name)
                nat = safe_value(row, c_nat)
                flag = get_flag_emoji(nat)
                st.session_state.notifications.append({
                    'title': "🆕 تسجيل عامل جديد",
                    'msg': f"👤 {name} | {flag} الجنسية: {nat}\n📱 {safe_value(row, c_phone)}\n💼 {safe_value(row, c_job)} | ⚧ {safe_value(row, c_gender)}",
                    'time': datetime.now().strftime("%H:%M")
                })
                st.toast(f"🆕 عامل جديد: {name}", icon="🔔")
                st.session_state.notif_triggered = True
            st.session_state.db.fetch_data(force=True)
            
            disk_state['last_row_candidates'] = current_worker_count
            with open(STATE_FILE, "w") as f: json.dump(disk_state, f, indent=4)

        st.session_state.notif_last_worker_count = current_worker_count

        df_cust = st.session_state.db.fetch_customer_requests(is_notif_check=True)
        current_cust_count = len(df_cust)
        
        last_cust_count = st.session_state.get('notif_last_cust_count')
        if last_cust_count is None:
            last_cust_count = disk_state.get('last_row_customer_requests')
        
        if last_cust_count is not None and current_cust_count > last_cust_count:
            new_rows = df_cust.tail(current_cust_count - last_cust_count)
            
            c_comp = find_matching_column(df_cust, ['اسم الشركه', 'المؤسسة', 'الشركة', 'Company'], flexible_arabic=True)
            c_phone = find_matching_column(df_cust, ['الموبيل', 'جوال', 'هاتف', 'Mobile'], flexible_arabic=True)
            c_salary = find_matching_column(df_cust, ['الراتب المتوقع', 'Expected salary', 'الراتب'], flexible_arabic=True)
            c_nat = find_matching_column(df_cust, ['الجنسية المطلوبة', 'Required nationality', 'الجنسية'], flexible_arabic=True)
            c_loc = find_matching_column(df_cust, ['موقع العمل', 'المدينة'], flexible_arabic=True)
            
            for _, row in new_rows.iterrows():
                comp = safe_value(row, c_comp)
                nat = safe_value(row, c_nat)
                flag = get_flag_emoji(nat)
                st.session_state.notifications.append({
                    'title': "🔔 طلب عميل جديد",
                    'msg': f"🏢 {comp} | 📱 {safe_value(row, c_phone)}\n💰 الراتب المتوقع: {safe_value(row, c_salary)} | {flag} الجنسية المطلوبة: {nat}\n📍 {safe_value(row, c_loc)}",
                    'time': datetime.now().strftime("%H:%M")
                })
                st.toast(f"🔔 طلب جديد: {comp}", icon="☕")
                st.session_state.notif_triggered = True 
            st.session_state.db.fetch_customer_requests(force=True)
            
            disk_state['last_row_customer_requests'] = current_cust_count
            with open(STATE_FILE, "w") as f: json.dump(disk_state, f, indent=4)
        
        st.session_state.notif_last_cust_count = current_cust_count
    except Exception as e:
        print(f"Error checking notifications: {e}")

@st.fragment(run_every="20s")
def silent_notification_monitor():
    if st.session_state.get('user'):
        check_notifications()
