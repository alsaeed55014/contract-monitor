import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# ============================================
# إعدادات الصفحة
# ============================================
st.set_page_config(
    page_title="Contract Monitor",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# ملف قاعدة بيانات المستخدمين
# ============================================
USERS_FILE = "users_database.json"

# ============================================
# دالة للتحقق من وجود أحرف عربية
# ============================================
def has_arabic(text):
    """التحقق مما إذا كان النص يحتوي على أحرف عربية"""
    if not text:
        return False
    return any('\u0600' <= char <= '\u06FF' for char in str(text))

# ============================================
# دالة تحميل المستخدمين
# ============================================
def load_users():
    """تحميل قاعدة بيانات المستخدمين مع التحديث التلقائي"""
    default_users = {
        "admin": {
            "password": "admin123",
            "role": "admin",
            "full_name": "System Administrator",
            "full_name_ar": "مدير النظام",
            "full_name_en": "System Administrator"
        }
    }
    
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
            
            # تحديث تلقائي للمستخدمين القدامى
            updated = False
            for username, user_data in users.items():
                # إذا لم يكن لديه full_name_ar، أضفه من full_name
                if 'full_name_ar' not in user_data:
                    users[username]['full_name_ar'] = user_data.get('full_name', username)
                    updated = True
                
                # إذا لم يكن لديه full_name_en، أضفه من full_name
                if 'full_name_en' not in user_data:
                    users[username]['full_name_en'] = user_data.get('full_name', username)
                    updated = True
            
            # حفظ التحديثات إذا حدثت
            if updated:
                with open(USERS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(users, f, ensure_ascii=False, indent=2)
                st.success("تم تحديث قاعدة بيانات المستخدمين تلقائياً!")
            
            return users
            
        except Exception as e:
            st.error(f"خطأ في تحميل قاعدة البيانات: {e}")
            return default_users
    else:
        # إنشاء ملف افتراضي
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_users, f, ensure_ascii=False, indent=2)
        return default_users

# ============================================
# دالة حفظ المستخدمين
# ============================================
def save_users(users):
    """حفظ قاعدة بيانات المستخدمين"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# ============================================
# دالة الحصول على اسم العرض حسب اللغة
# ============================================
def get_display_name(username, users, language='ar'):
    """
    الحصول على اسم العرض المناسب حسب اللغة
    
    Args:
        username: اسم المستخدم
        users: قاموس المستخدمين
        language: 'ar' للعربية، 'en' للإنجليزية
    
    Returns:
        الاسم المناسب للغة المختارة
    """
    if username not in users:
        return username
    
    user_data = users[username]
    
    if language == 'ar':
        # للغة العربية: استخدم الاسم العربي أو الاسم العام أو اسم المستخدم
        name = user_data.get('full_name_ar', '') or user_data.get('full_name', '') or username
        return name
    
    else:  # language == 'en'
        # للغة الإنجليزية: تحقق من الاسم الإنجليزي
        name_en = user_data.get('full_name_en', '')
        
        # إذا كان الاسم الإنجليزي فارغاً أو يحتوي على عربية، استخدم اسم المستخدم
        if not name_en or has_arabic(name_en):
            return username
        
        return name_en

# ============================================
# تهيئة حالة الجلسة
# ============================================
if 'users' not in st.session_state:
    st.session_state.users = load_users()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

if 'language' not in st.session_state:
    st.session_state.language = 'ar'

# ============================================
# النصوص متعددة اللغات
# ============================================
TEXTS = {
    'ar': {
        'welcome': 'مرحباً بك يا',
        'welcome_back': 'مرحباً بعودتك يا',
        'login': 'تسجيل الدخول',
        'logout': 'تسجيل الخروج',
        'username': 'اسم المستخدم',
        'password': 'كلمة المرور',
        'permissions': 'شاشة الصلاحيات',
        'update_names': 'تحديث أسماء المستخدمين',
        'full_name_ar': 'الاسم الكامل بالعربي',
        'full_name_en': 'الاسم الكامل بالإنجليزي',
        'save': 'حفظ التحديثات',
        'select_user': 'اختر المستخدم',
        'current_name': 'الاسم الحالي',
        'admin_panel': 'لوحة التحكم',
        'contracts': 'العقود',
        'settings': 'الإعدادات',
        'language': 'اللغة',
        'arabic': 'العربية',
        'english': 'الإنجليزية'
    },
    'en': {
        'welcome': 'Welcome',
        'welcome_back': 'Welcome back',
        'login': 'Login',
        'logout': 'Logout',
        'username': 'Username',
        'password': 'Password',
        'permissions': 'Permissions',
        'update_names': 'Update User Names',
        'full_name_ar': 'Full Name (Arabic)',
        'full_name_en': 'Full Name (English)',
        'save': 'Save Updates',
        'select_user': 'Select User',
        'current_name': 'Current Name',
        'admin_panel': 'Admin Panel',
        'contracts': 'Contracts',
        'settings': 'Settings',
        'language': 'Language',
        'arabic': 'Arabic',
        'english': 'English'
    }
}

def t(key):
    """الحصول على النص حسب اللغة الحالية"""
    return TEXTS[st.session_state.language].get(key, key)

# ============================================
# صفحة تسجيل الدخول
# ============================================
def login_page():
    st.title(t('login'))
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        username = st.text_input(t('username'))
        password = st.text_input(t('password'), type='password')
        
        if st.button(t('login'), use_container_width=True):
            users = st.session_state.users
            
            if username in users and users[username]['password'] == password:
                st.session_state.logged_in = True
                st.session_state.current_user = username
                st.success(f"تم تسجيل الدخول بنجاح!")
                st.rerun()
            else:
                st.error("اسم المستخدم أو كلمة المرور غير صحيحة")

# ============================================
# الشريط الجانبي مع رسالة الترحيب
# ============================================
def sidebar():
    with st.sidebar:
        # اختيار اللغة
        lang = st.radio(
            "Language / اللغة",
            ['ar', 'en'],
            format_func=lambda x: 'العربية' if x == 'ar' else 'English',
            index=0 if st.session_state.language == 'ar' else 1
        )
        
        if lang != st.session_state.language:
            st.session_state.language = lang
            st.rerun()
        
        st.divider()
        
        # رسالة الترحيب - هنا الإصلاح الرئيسي!
        if st.session_state.logged_in and st.session_state.current_user:
            display_name = get_display_name(
                st.session_state.current_user,
                st.session_state.users,
                st.session_state.language
            )
            
            # عرض رسالة الترحيب
            if st.session_state.language == 'ar':
                st.markdown(f"### {t('welcome_back')} {display_name} 👋")
            else:
                st.markdown(f"### {t('welcome_back')}, {display_name} 👋")
        
        st.divider()
        
        # قائمة التنقل
        if st.session_state.logged_in:
            page = st.radio(
                "القائمة / Menu",
                ['contracts', 'permissions', 'settings'],
                format_func=lambda x: {
                    'contracts': '📋 ' + t('contracts'),
                    'permissions': '🔑 ' + t('permissions'),
                    'settings': '⚙️ ' + t('settings')
                }.get(x, x)
            )
            
            st.session_state.page = page
            
            if st.button(t('logout'), use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.current_user = None
                st.rerun()

# ============================================
# صفحة الصلاحيات مع تحديث الأسماء
# ============================================
def permissions_page():
    st.title('🔑 ' + t('permissions'))
    
    users = st.session_state.users
    
    # قسم تحديث أسماء المستخدمين
    st.header(t('update_names'))
    
    selected_user = st.selectbox(
        t('select_user'),
        list(users.keys()),
        format_func=lambda x: f"{x} - {users[x].get('full_name_ar', users[x].get('full_name', x))}"
    )
    
    if selected_user:
        user_data = users[selected_user]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🇸🇦 " + t('full_name_ar') + "**")
            current_ar = user_data.get('full_name_ar', user_data.get('full_name', ''))
            st.info(f"{t('current_name')}: {current_ar}")
            new_name_ar = st.text_input(
                "الاسم الجديد بالعربية",
                value=current_ar,
                key="name_ar"
            )
        
        with col2:
            st.markdown("**🇬🇧 " + t('full_name_en') + "**")
            current_en = user_data.get('full_name_en', user_data.get('full_name', ''))
            st.info(f"{t('current_name')}: {current_en}")
            new_name_en = st.text_input(
                "New name in English",
                value=current_en,
                key="name_en"
            )
        
        if st.button(t('save'), use_container_width=True):
            users[selected_user]['full_name_ar'] = new_name_ar
            users[selected_user]['full_name_en'] = new_name_en
            
            # تحديث الاسم العام أيضاً
            users[selected_user]['full_name'] = new_name_ar
            
            save_users(users)
            st.session_state.users = users
            st.success("تم حفظ التحديثات بنجاح! / Updates saved successfully!")

# ============================================
# الصفحة الرئيسية
# ============================================
def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        sidebar()
        
        page = st.session_state.get('page', 'contracts')
        
        if page == 'contracts':
            st.title(t('contracts'))
            st.info("صفحة العقود / Contracts page")
            
        elif page == 'permissions':
            permissions_page()
            
        elif page == 'settings':
            st.title(t('settings'))
            st.info("صفحة الإعدادات / Settings page")

# ============================================
# تشغيل التطبيق
# ============================================
if __name__ == "__main__":
    main()
