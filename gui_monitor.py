import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import threading
import time
import os
import sys
import json
import hashlib
import ctypes
from dateutil import parser
try:
    from tkcalendar import DateEntry
except ImportError:
    pass # Assume user will install it or it's handled

# Branding
PROGRAMMER_NAME = "برمجة: السعيد الوزان"
ICON_PATH = "app_icon.ico"
USER_IMAGE_FILES = ["profile.png", "profile.jpg", "profile.jpeg", "image.png", "image.jpg"]
IGNORED_FILE = "ignored_rows.json"

# Colors
BG_COLOR = "#2c3e50"
SIDEBAR_COLOR = "#1a252f"
TEXT_COLOR = "#ecf0f1"
ACCENT_COLOR = "#e74c3c"
GOLD_COLOR = "#f1c40f"
SUCCESS_COLOR = "#27ae60"

# Bilingual UI Texts
UI_TEXTS = {
    'ar': {
        'search': "البحث والطباعة  ",
        'delete': "حذف الصف المختار  ️",
        'refresh': "تحديث البيانات  ",
        'perms': "شاشة الصلاحيات  ",
        'exit': "خروج من البرنامج  ",
        'alerts': "تنبيهات العقود الوشيكة (أسبوع / يومين)",
        'status': "الحالة: انتظار...",
        'lang_btn': "Switch to English",
        'search_title': "نظام البحث المتقدم",
        'search_subtitle': "Contract Monitoring System",
        'back_to_menu': "العودة للقائمة",
        'search_criteria': "معايير البحث",
        'smart_search': "البحث الشامل:",
        'search_placeholder': "(الاسم، الوظيفة، الجنسية، رقم الجوال...)",
        'reg_date': "تاريخ التسجيل",
        'contract_expiry': "انتهاء العقد",
        'age': "السن",
        'enable': "تفعيل",
        'from': "من",
        'to': "إلى",
        'print_report': "طباعة التقرير ️",
        'search_now': "بحث الآن ",
        'ready': "جاهز للبحث...",
        'alert_expiry_title': "️ تنبيه انتهاء عقود",
        'alert_expiry_header': "️ تنبيه: عقود تنتهي قريباً",
        'close': "إغلاق",
        'days_left': "باقي {days} يوم",
        'week_left': "باقي أسبوع",
        'no_results': "لا توجد نتائج لطباعتها",
        'report_saved': "تم حفظ التقرير باسم:",
        'loading': "جارِ تحميل البيانات، يرجى الانتظار ثانية ثم المحاولة مرة أخرى.",
        'alert_status': "حالة التنبيه",
        'col_name': "الاسم",
        'col_nat': "الجنسية",
        'col_gen': "الجنس",
        'col_phone': "الجوال",
        'col_status': "الحالة",
        'login_title': "تسجيل الدخول",
        'username': "اسم المستخدم",
        'password': "كلمة المرور",
        'login_btn': "دخول",
        'login_error_title': "خطأ",
        'login_error_msg': "اسم المستخدم أو كلمة المرور غير صحيحة",
        'perms_title': "الصلاحيات وإعدادات المستخدم",
        'perms_header': "نظام الصلاحيات والإعدادات",
        'welcome': "مرحباً بك،",
        'add_user': "إضافة مستخدم جديد",
        'can_manage': "صلاحية دخول شاشة الصلاحيات",
        'add_btn': "إضافة مستخدم",
        'change_pass': "تغيير كلمة مرورك",
        'new_pass': "كلمة المرور الجديدة",
        'save_btn': "حفظ التغييرات",
        'back_home': "الرجوع للشاشة الرئيسية",
        'exit_perm': "خروج من البرنامج",
        'user_added': "تم الاضافة",
        'pass_changed': "تم التحديث",
        'user_deleted': "تم الحذف",
        'pass_error': "حدث خطأ أثناء التحديث",
        'fields_required': "يرجى إدخال اسم المستخدم وكلمة المرور",
        'pass_empty': "لا يمكن ترك كلمة المرور فارغة",
        'success': "نجاح",
        'warning_title': "تنبيه",
        'last_update': "آخر تحديث: {t}\n{message}",
        'select_row': "اختر صفاً أولاً",
        'confirm_delete_title': "تأكيد",
        'confirm_delete_msg': "حذف الصف من العرض؟",
        'access_denied_title': "صلاحية مرفوضة",
        'access_denied_msg': "عذراً، ليس لديك الصلاحية لدخول شاشة الصلاحيات"
    },
    'en': {
        'search': "Search & Print  ",
        'delete': "Delete Selected Row  ️",
        'refresh': "Refresh Data  ",
        'perms': "Permissions Screen  ",
        'exit': "Exit Program  ",
        'alerts': "Upcoming Contract Alerts",
        'status': "Status: Waiting...",
        'lang_btn': "التحويل للعربية",
        'search_title': "Advanced Search System",
        'search_subtitle': "Contract Monitoring System",
        'back_to_menu': "Return to Menu",
        'search_criteria': "Search Criteria",
        'smart_search': "Smart Search:",
        'search_placeholder': "(Name, Job, Nationality, Phone...)",
        'reg_date': "Registration Date",
        'contract_expiry': "Contract Expiry",
        'age': "Age",
        'enable': "Enable",
        'from': "From",
        'to': "To",
        'print_report': "Print Report ️",
        'search_now': "Search Now ",
        'ready': "Ready to search...",
        'alert_expiry_title': "️ Contract Expiry Alerts",
        'alert_expiry_header': "️ Alert: Contracts expiring soon",
        'close': "Close",
        'days_left': "{days} days left",
        'week_left': "1 week left",
        'no_results': "No results to print",
        'report_saved': "Report saved as:",
        'loading': "Loading data, please wait a second and try again.",
        'alert_status': "Alert Status",
        'col_name': "Name",
        'col_nat': "Nationality",
        'col_gen': "Gender",
        'col_phone': "Phone",
        'col_status': "Status",
        'login_title': "Login",
        'username': "Username",
        'password': "Password",
        'login_btn': "Login",
        'login_error_title': "Error",
        'login_error_msg': "Invalid username or password",
        'perms_title': "Permissions & Settings",
        'perms_header': "Permissions & Settings System",
        'welcome': "Welcome,",
        'add_user': "Add New User",
        'can_manage': "Access Permissions Screen",
        'add_btn': "Add User",
        'change_pass': "Change Your Password",
        'new_pass': "New Password",
        'save_btn': "Save Changes",
        'back_home': "Back to Home",
        'exit_perm': "Exit Program",
        'user_added': "User Added",
        'pass_changed': "Updated Successfully",
        'user_deleted': "Deleted Successfully",
        'pass_error': "Error during update",
        'fields_required': "Please enter username and password",
        'pass_empty': "Password cannot be empty",
        'success': "Success",
        'success': "نجاح",
        'warning_title': "تنبيه",
        'last_update': "آخر تحديث: {t}\n{message}",
        'select_row': "اختر صفاً أولاً",
        'confirm_delete_title': "تأكيد",
        'confirm_delete_msg': "حذف الصف من العرض؟",
        'access_denied_title': "صلاحية مرفوضة",
        'access_denied_msg': "عذراً، ليس لديك الصلاحية لدخول شاشة الصلاحيات",
        'img_placeholder': "[مكان الصورة]",
        'img_not_found': "[الصورة غير موجودة]"
    },
    'en': {
        'search': "Search & Print  ",
        'delete': "Delete Selected Row  ️",
        'refresh': "Refresh Data  ",
        'perms': "Permissions Screen  ",
        'exit': "Exit Program  ",
        'alerts': "Upcoming Contract Alerts",
        'status': "Status: Waiting...",
        'lang_btn': "التحويل للعربية",
        'search_title': "Advanced Search System",
        'search_subtitle': "Contract Monitoring System",
        'back_to_menu': "Return to Menu",
        'search_criteria': "Search Criteria",
        'smart_search': "Smart Search:",
        'search_placeholder': "(Name, Job, Nationality, Phone...)",
        'reg_date': "Registration Date",
        'contract_expiry': "Contract Expiry",
        'age': "Age",
        'enable': "Enable",
        'from': "From",
        'to': "To",
        'print_report': "Print Report ️",
        'search_now': "Search Now ",
        'ready': "Ready to search...",
        'alert_expiry_title': "️ Contract Expiry Alerts",
        'alert_expiry_header': "️ Alert: Contracts expiring soon",
        'close': "Close",
        'days_left': "{days} days left",
        'week_left': "1 week left",
        'no_results': "No results to print",
        'report_saved': "Report saved as:",
        'loading': "Loading data, please wait a second and try again.",
        'alert_status': "Alert Status",
        'col_name': "Name",
        'col_nat': "Nationality",
        'col_gen': "Gender",
        'col_phone': "Phone",
        'col_status': "Status",
        'login_title': "Login",
        'username': "Username",
        'password': "Password",
        'login_btn': "Login",
        'login_error_title': "Error",
        'login_error_msg': "Invalid username or password",
        'perms_title': "Permissions & Settings",
        'perms_header': "Permissions & Settings System",
        'welcome': "Welcome,",
        'add_user': "Add New User",
        'can_manage': "Access Permissions Screen",
        'add_btn': "Add User",
        'change_pass': "Change Your Password",
        'new_pass': "New Password",
        'save_btn': "Save Changes",
        'back_home': "Back to Home",
        'exit_perm': "Exit Program",
        'user_exists': "Username already exists",
        'user_added': "User added successfully",
        'pass_changed': "Password changed successfully",
        'pass_error': "Error changing password",
        'fields_required': "Please enter username and password",
        'pass_empty': "Password cannot be empty",
        'success': "Success",
        'warning_title': "Warning",
        'last_update': "Last Update: {t}\n{message}",
        'select_row': "Select a row first",
        'confirm_delete_title': "Confirm",
        'confirm_delete_msg': "Delete row from view?",
        'access_denied_title': "Access Denied",
        'access_denied_msg': "Sorry, you don't have permission to access this screen.",
        'img_placeholder': "[Image Placeholder]",
        'img_not_found': "[Image Not Found]"
    }
}

class ContractMonitorApp:
    def __init__(self, root, current_user="admin"):
        self.root = root
        self.current_user = current_user
        self.lang = 'ar'
        self.root.title(f"مراقب العقود - {PROGRAMMER_NAME}")
        if os.path.exists(ICON_PATH):
            try: self.root.iconbitmap(ICON_PATH)
            except: pass
        self.root.geometry("1400x800")
        self.root.state('zoomed') # Maximize on startup
        self.root.configure(bg=BG_COLOR)
        
        # Hide console window if running on Windows (Silent mode)
        if os.name == 'nt':
            try:
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
            except: pass
        
        self.ignored_ids = self.load_ignored()
        self.all_data_raw = [] # Store all data for searching
        self.translator = TranslationManager()
        
        self.center_window(self.root)
        self.setup_styles()
        
        self.main_container = tk.Frame(self.root, bg=BG_COLOR)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.create_sidebar()
        self.create_content_area()
        
        self.log("جارٍ تشغيل البرنامج...")
        self.start_monitoring()

    def exit_app(self):
        # Custom Exit Dialog to enforce "Yes" on Right, "No" on Left
        dialog = tk.Toplevel(self.root)
        dialog.title("خروج")
        dialog.geometry("400x180")
        dialog.configure(bg="white")
        dialog.resizable(False, False)
        
        # Center the dialog
        self.center_window(dialog, self.root)
        dialog.grab_set() # Make modal

        # Icon and Message
        content_frame = tk.Frame(dialog, bg="white")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=20)

        # Try to get a system icon or simple label
        try:
            # Using standard system warning/question icon if possible, or just a Label
            lbl_icon = tk.Label(content_frame, text="؟", font=('Arial', 40, 'bold'), fg="#3498db", bg="white")
            lbl_icon.pack(side=tk.RIGHT, padx=20)
        except: pass

        lbl_msg = tk.Label(content_frame, text="هل أنت متأكد من الخروج من البرنامج؟", font=('Arial', 12), bg="white", fg="black")
        lbl_msg.pack(side=tk.RIGHT, padx=10, pady=15)

        # Buttons (Yes on Right, No on Left)
        btn_frame = tk.Frame(dialog, bg="#f0f0f0")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        def do_exit():
            dialog.destroy()
            self.root.destroy()
            sys.exit()

        # Pack Yes (Right)
        btn_yes = tk.Button(btn_frame, text="نعم", width=10, command=do_exit, font=('Arial', 10), bg="white")
        btn_yes.pack(side=tk.RIGHT, padx=20, pady=10)
        
        # Pack No (Left)
        btn_no = tk.Button(btn_frame, text="لا", width=10, command=dialog.destroy, font=('Arial', 10), bg="white")
        btn_no.pack(side=tk.LEFT, padx=20, pady=10)

    def load_ignored(self):
        if os.path.exists(IGNORED_FILE):
            try:
                with open(IGNORED_FILE, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except: return set()
        return set()

    def save_ignored(self):
        try:
            with open(IGNORED_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(self.ignored_ids), f)
        except: pass

    def center_window(self, window, parent=None, size=None):
        window.update_idletasks()
        if size:
            width, height = size
        else:
            width = window.winfo_width()
            height = window.winfo_height()
        
        if parent:
            parent.update_idletasks()
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x = px + (pw // 2) - (width // 2)
            y = py + (ph // 2) - (height // 2)
        else:
            x = (window.winfo_screenwidth() // 2) - (width // 2)
            y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background="white", foreground="black", rowheight=35, font=('Arial', 10))
        style.configure("Treeview.Heading", font=('Arial', 11, 'bold'), background="#bdc3c7")

    def create_sidebar(self):
        sidebar = tk.Frame(self.main_container, bg=SIDEBAR_COLOR, width=300)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        img_path = self.find_profile_image()
        if img_path:
            try:
                load = Image.open(img_path).resize((180, 180), Image.Resampling.LANCZOS)
                render = ImageTk.PhotoImage(load)
                lbl = tk.Label(sidebar, image=render, bg=SIDEBAR_COLOR); lbl.image = render
                lbl.pack(pady=(40, 10))
            except: pass
        else:
            tk.Label(sidebar, text=UI_TEXTS[self.lang]['img_placeholder'], bg=SIDEBAR_COLOR, fg="gray").pack(pady=40)

        tk.Label(sidebar, text=PROGRAMMER_NAME, bg=SIDEBAR_COLOR, fg=GOLD_COLOR, font=('Segoe UI', 14, 'bold')).pack(pady=5)
        
        # Language Switcher
        def toggle_lang():
            self.lang = 'en' if self.lang == 'ar' else 'ar'
            self.root.destroy()
            new_root = tk.Tk()
            new_app = ContractMonitorApp(new_root, self.current_user)
            new_app.lang = self.lang
            new_app.apply_lang() # Helper to refresh texts
            new_root.mainloop()

        self.btn_lang = tk.Button(sidebar, text=UI_TEXTS[self.lang]['lang_btn'], font=('Segoe UI', 10), bg="#444", fg="white", command=toggle_lang)
        self.btn_lang.pack(fill=tk.X, padx=10, pady=5)

        # Spacer to push buttons to bottom
        tk.Frame(sidebar, bg=SIDEBAR_COLOR).pack(fill=tk.BOTH, expand=True)

        # Buttons (Packed at the bottom area)
        self.btn_search = tk.Button(sidebar, text=UI_TEXTS[self.lang]['search'], font=('Segoe UI', 12, 'bold'), bg="#3498db", fg="white", bd=0, padx=20, pady=10, command=self.open_search_module)
        self.btn_search.pack(fill=tk.X, padx=10, pady=5)

        self.btn_delete = tk.Button(sidebar, text=UI_TEXTS[self.lang]['delete'], font=('Segoe UI', 12, 'bold'), bg="#e67e22", fg="white", bd=0, padx=20, pady=10, command=self.delete_selected)
        self.btn_delete.pack(fill=tk.X, padx=10, pady=5)
        
        self.btn_refresh = tk.Button(sidebar, text=UI_TEXTS[self.lang]['refresh'], font=('Segoe UI', 12, 'bold'), bg="#e74c3c", fg="white", bd=0, padx=20, pady=10, command=self.refresh_manual)
        self.btn_refresh.pack(fill=tk.X, padx=10, pady=5)

        # Permissions Button
        self.btn_perms = tk.Button(sidebar, text=UI_TEXTS[self.lang]['perms'], font=('Segoe UI', 12, 'bold'), bg="#8e44ad", fg="white", bd=0, padx=20, pady=10, command=self.open_permissions)
        self.btn_perms.pack(fill=tk.X, padx=10, pady=5)

        # Status Label (Last Update)
        self.status_label = tk.Label(sidebar, text=UI_TEXTS[self.lang]['status'], bg=SIDEBAR_COLOR, fg="#bdc3c7", font=('Arial', 9))
        self.status_label.pack(pady=10)

        # Exit Button
        self.btn_exit = tk.Button(sidebar, text=UI_TEXTS[self.lang]['exit'], font=('Segoe UI', 12, 'bold'), bg="#c0392b", fg="white", bd=0, padx=20, pady=10, command=self.exit_app)
        self.btn_exit.pack(fill=tk.X, padx=10, pady=(10, 20))

    def apply_lang(self):
        """Refreshes UI texts without restarting if possible, but restart is safer for layout."""
        # This is a bit of a hack to refresh UI if we don't want to restart
        self.btn_lang.config(text=UI_TEXTS[self.lang]['lang_btn'])
        self.btn_search.config(text=UI_TEXTS[self.lang]['search'])
        self.btn_delete.config(text=UI_TEXTS[self.lang]['delete'])
        self.btn_refresh.config(text=UI_TEXTS[self.lang]['refresh'])
        self.btn_perms.config(text=UI_TEXTS[self.lang]['perms'])
        self.btn_exit.config(text=UI_TEXTS[self.lang]['exit'])
        self.status_label.config(text=UI_TEXTS[self.lang]['status'])
        if hasattr(self, 'lbl_title'):
             self.lbl_title.config(text=UI_TEXTS[self.lang]['alerts'])


    def open_permissions(self):
        auth = AuthManager()
        if not auth.has_permission(self.current_user):
            messagebox.showerror(UI_TEXTS[self.lang]['access_denied_title'], UI_TEXTS[self.lang]['access_denied_msg'])
            return
            
        self.root.destroy()
        PermissionsWindow(self.current_user, lang=self.lang)

    def create_content_area(self):
        content = tk.Frame(self.main_container, bg=BG_COLOR)
        content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.lbl_title = tk.Label(content, text=UI_TEXTS[self.lang]['alerts'], bg=BG_COLOR, fg=GOLD_COLOR, font=('Segoe UI', 22, 'bold'))
        self.lbl_title.pack(pady=(0, 20))
        
        f = tk.Frame(content, bg="white")
        f.pack(fill=tk.BOTH, expand=True)
        
        sy = ttk.Scrollbar(f); sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(f, orient="horizontal"); sx.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree = ttk.Treeview(f, yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        sy.config(command=self.tree.yview); sx.config(command=self.tree.xview)
        
        self.tree.tag_configure('warning', background='#ffeb3b')
        self.tree.tag_configure('danger', background='#f44336', foreground='white')

    def find_profile_image(self):
        for f in USER_IMAGE_FILES:
            if os.path.exists(f): return os.path.abspath(f)
        return None

    def log(self, message):
        t = datetime.now().strftime("%H:%M:%S")
        self.status_label.config(text=UI_TEXTS[self.lang]['last_update'].format(t=t, message=message))

    def refresh_manual(self):
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showwarning(UI_TEXTS[self.lang]['warning_title'], UI_TEXTS[self.lang]['select_row'])
        if messagebox.askyesno(UI_TEXTS[self.lang]['confirm_delete_title'], UI_TEXTS[self.lang]['confirm_delete_msg']):
            vals = self.tree.item(sel[0])['values']
            key = "|".join([str(v) for v in vals[1:7]])
            self.ignored_ids.add(key)
            self.save_ignored()
            self.tree.delete(sel[0])

    def start_monitoring(self):
        self.refresh_manual()
        self.root.after(1800000, self.start_monitoring)

    def _fetch_and_update(self):
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit").sheet1
            rows = sheet.get_all_values()
            self.all_data_raw = rows # Cache for search
            self.root.after(0, lambda: self._process_data(rows))
        except Exception as e: self.log(f"خطأ: {e}")

    def translate_header(self, text):
        m = {
            "full name": {"ar": "الاسم الكامل", "en": "Full Name"}, 
            "الاسم الكامل": {"ar": "الاسم الكامل", "en": "Full Name"}, 
            "nationality": {"ar": "الجنسية", "en": "Nationality"}, 
            "الجنسية": {"ar": "الجنسية", "en": "Nationality"}, 
            "gender": {"ar": "الجنس", "en": "Gender"}, 
            "الجنس": {"ar": "الجنس", "en": "Gender"}, 
            "phone number": {"ar": "رقم الجوال", "en": "Phone Number"},
            "رقم الجوال": {"ar": "رقم الجوال", "en": "Phone Number"}, 
            "when is your contract end date?": {"ar": "تاريخ انتهاء العقد", "en": "Contract End Date"}, 
            "تاريخ انتهاء العقد": {"ar": "تاريخ انتهاء العقد", "en": "Contract End Date"}, 
            "your age": {"ar": "العمر", "en": "Age"}, 
            "العمر": {"ar": "العمر", "en": "Age"}, 
            "timestamp": {"ar": "طابع زمني", "en": "Timestamp"},
            "طابع زمني": {"ar": "طابع زمني", "en": "Timestamp"}, 
            "are you work": {"ar": "هل تعمل حالياً؟", "en": "Currently Working?"},
            "هل تعمل حالياً": {"ar": "هل تعمل حالياً؟", "en": "Currently Working?"}, 
            "do you have a valid residency": {"ar": "هل لديك إقامة سارية؟", "en": "Valid Residency?"},
            "إقامة سارية": {"ar": "هل لديك إقامة سارية؟", "en": "Valid Residency?"}, 
            "do you have a valid driving": {"ar": "هل لديك رخصة قيادة؟", "en": "Driving License?"},
            "رخصة قيادة": {"ar": "هل لديك رخصة قيادة؟", "en": "Driving License?"}, 
            "if you are huroob": {"ar": "كم عدد الهروب", "en": "Huroob Count"},
            "عدد الهروب": {"ar": "كم عدد الهروب", "en": "Huroob Count"}, 
            "will your employer": {"ar": "هل الكفيل يتنازل؟", "en": "Employer Transferable?"},
            "الكفيل يتنازل": {"ar": "هل الكفيل يتنازل؟", "en": "Employer Transferable?"}, 
            "are you in saudi": {"ar": "هل أنت في السعودية؟", "en": "In Saudi?"},
            "أنت في السعودية": {"ar": "هل أنت في السعودية؟", "en": "In Saudi?"}, 
            "which city": {"ar": "المدينة / المنطقة", "en": "City"},
            "المدينة": {"ar": "المدينة / المنطقة", "en": "City"}, 
            "how did you hear": {"ar": "كيف سمعت عنا؟", "en": "How Hear About Us"},
            "كيف سمعت عنا": {"ar": "كيف سمعت عنا؟", "en": "How Hear About Us"}, 
            "what is the nam": {"ar": "اسم الكفيل / المنشأة", "en": "Employer Name"},
            "اسم الكفيل": {"ar": "اسم الكفيل / المنشأة", "en": "Employer Name"}, 
            "do you speak a": {"ar": "هل تتحدث العربية؟", "en": "Speak Arabic?"},
            "تتحدث العربية": {"ar": "هل تتحدث العربية؟", "en": "Speak Arabic?"}, 
            "which job are y": {"ar": "الوظيفة المطلوبة", "en": "Required Job"},
            "الوظيفة المطلوبة": {"ar": "الوظيفة المطلوبة", "en": "Required Job"}, 
            "what other jobs": {"ar": "وظائف أخرى تتقنها", "en": "Other Skills"},
            "وظائف أخرى": {"ar": "وظائف أخرى تتقنها", "en": "Other Skills"}, 
            "how much expe": {"ar": "الخبرة", "en": "Experience"},
            "الخبرة": {"ar": "الخبرة", "en": "Experience"}, 
            "do you have c": {"ar": "هل لديك كرت صحي؟", "en": "Health Card?"},
            "كرت صحي": {"ar": "هل لديك كرت صحي؟", "en": "Health Card?"}, 
            "is the card bala": {"ar": "صلاحية كرت البلدية", "en": "Municipality Card Expiry"},
            "كرت البلدية": {"ar": "صلاحية كرت البلدية", "en": "Municipality Card Expiry"}, 
            "how many mont": {"ar": "عدد الأشهر", "en": "Months Count"},
            "عدد الأشهر": {"ar": "عدد الأشهر", "en": "Months Count"}, 
            "can you work o": {"ar": "هل تعمل وقت إضافي؟", "en": "Overtime?"},
            "وقت إضافي": {"ar": "هل تعمل وقت إضافي؟", "en": "Overtime?"}, 
            "are you ready to": {"ar": "هل أنت جاهز للعمل؟", "en": "Ready to Work?"},
            "جاهز للعمل": {"ar": "هل أنت جاهز للعمل؟", "en": "Ready to Work?"}, 
            "are you married": {"ar": "الحالة الاجتماعية", "en": "Marital Status"},
            "الحالة الاجتماعية": {"ar": "الحالة الاجتماعية", "en": "Marital Status"}, 
            "iqama id numbe": {"ar": "رقم الإقامة", "en": "Iqama ID"},
            "رقم الإقامة": {"ar": "رقم الإقامة", "en": "Iqama ID"}, 
            "what is the occ": {"ar": "المهنة في الإقامة", "en": "Iqama Profession"},
            "المهنة في الإقامة": {"ar": "المهنة في الإقامة", "en": "Iqama Profession"}, 
            "your iqama vali": {"ar": "صلاحية الإقامة", "en": "Iqama Expiry"},
            "صلاحية الإقامة": {"ar": "صلاحية الإقامة", "en": "Iqama Expiry"}, 
            "how many times": {"ar": "عدد مرات التنازل", "en": "Transfer Times"},
            "مرات التنازل": {"ar": "عدد مرات التنازل", "en": "Transfer Times"}, 
            "download cv": {"ar": "تحميل السيرة الذاتية", "en": "Download CV"},
            "السيرة الذاتية": {"ar": "تحميل السيرة الذاتية", "en": "Download CV"}, 
            "is your contract": {"ar": "هل العقد ساري؟", "en": "Contract Valid?"},
            "العقد ساري": {"ar": "هل العقد ساري؟", "en": "Contract Valid?"}, 
            "do you have an": {"ar": "هل لديك أي التزامات مالية تجاه كفيلك السابق", "en": "Financial Commitments?"},
            "التزامات مالية": {"ar": "هل لديك أي التزامات مالية تجاه كفيلك السابق", "en": "Financial Commitments?"}, 
            "do you have to": {"ar": "هل يجب عليك الإبلاغ عن هروب", "en": "Must Report Huroob?"},
            "الإبلاغ عن هروب": {"ar": "هل يجب عليك الإبلاغ عن هروب", "en": "Must Report Huroob?"}
        }
        t = text.lower().strip().replace(':', '')
        for k, v in m.items():
            if k in t: return v[self.lang]
        return text
    
    def normalize_text(self, text):
        # 100% Unified Normalization for both UI and Translator
        t = str(text).lower().strip().replace('\xa0', ' ')
        # Standard Normalization
        t = t.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه').replace('ى', 'ي')
        # Phonetic Folding (The "Aggressive" matching)
        t = t.replace('ض', 'ظ').replace('ظ', 'ظ').replace('ذ', 'ز').replace('ز', 'ز')
        t = t.replace('ث', 'س').replace('س', 'س').replace('ق', 'ج').replace('ك', 'ج').replace('ج', 'ج')
        return t

    def _process_data(self, rows):
        headers_raw = rows[0]
        headers = []
        seen = {}
        for i, h in enumerate(headers_raw):
            h = h.strip()
            if not h:
                h = f"Column_{i+1}"
            
            trans = self.translate_header(h)
            
            # Ensure uniqueness
            original_trans = trans
            count = 1
            while trans in seen:
                trans = f"{original_trans}.{count}"
                count += 1
            
            seen[trans] = True
            headers.append(trans)
        data = rows[1:]
        today = datetime.now().date()
        
        date_idx = -1
        for i, h in enumerate(headers_raw):
            norm_h = self.normalize_text(h)
            if any(k in norm_h for k in ["contract end", "تاريخ انتهاء العقد", "when is your contract", "انتهاء العقد"]):
                date_idx = i; break
        
        # Fallback if exact match failed, try broader keywords
        if date_idx == -1:
            for i, h in enumerate(headers_raw):
                norm_h = self.normalize_text(h)
                if "تاريخ" in norm_h and "عقد" in norm_h:
                    date_idx = i; break

        processed, alerts = [], []
        for row in data:
            key = "|".join([str(v) for v in row[0:6]])
            if key in self.ignored_ids: continue
            
            if date_idx != -1 and len(row) > date_idx:
                try:
                    dt = parser.parse(str(row[date_idx])).date()
                    days = (dt - today).days
                    if days in [1, 2, 7]:
                        msg = UI_TEXTS[self.lang]['days_left'].format(days=days) if days < 7 else UI_TEXTS[self.lang]['week_left']
                        processed.append(([msg] + row, 'danger' if days <= 2 else 'warning'))
                        alerts.append([row[0], row[1], row[2], row[3], msg]) # Simple popup data
                except: continue
        
        self._populate_tree(self.tree, [UI_TEXTS[self.lang]['alert_status']] + headers, processed)
        if alerts: self._show_alert_popup(alerts)

    def _populate_tree(self, tree, headers, rows):
        tree.delete(*tree.get_children())
        tree["columns"] = headers
        tree["show"] = "headings"
        for h in headers:
            tree.heading(h, text=h, anchor=tk.CENTER)
            # Widen columns for long headers and allow stretching
            w = 190
            if len(h) > 25: w = 350 # Dynamic width for long headers
            tree.column(h, width=w, minwidth=140, stretch=True, anchor=tk.CENTER)
        for r, tag in rows: tree.insert("", tk.END, values=r, tags=(tag,))

    def _show_alert_popup(self, alerts):
        if hasattr(self, 'popup') and self.popup.winfo_exists(): return
        self.popup = tk.Toplevel(self.root)
        self.popup.title(UI_TEXTS[self.lang]['alert_expiry_title'])
        self.center_window(self.popup, self.root, size=(800, 400))
        self.popup.configure(bg=ACCENT_COLOR)
        tk.Label(self.popup, text=UI_TEXTS[self.lang]['alert_expiry_header'], font=('Arial', 16, 'bold'), bg=ACCENT_COLOR, fg="white").pack(pady=10)
        f = tk.Frame(self.popup); f.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        t = ttk.Treeview(f, columns=("1","2","3","4","5"), show="headings", height=8); t.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hds = [UI_TEXTS[self.lang]['col_name'], UI_TEXTS[self.lang]['col_nat'], UI_TEXTS[self.lang]['col_gen'], UI_TEXTS[self.lang]['col_phone'], UI_TEXTS[self.lang]['col_status']]
        for i, h in enumerate(hds, 1): t.heading(str(i), text=h); t.column(str(i), width=120)
        for a in alerts: t.insert("", tk.END, values=a)
        tk.Button(self.popup, text=UI_TEXTS[self.lang]['close'], command=self.popup.destroy).pack(pady=10)

    # --- SEARCH MODULE ---
    def open_search_module(self):
        self.root.withdraw() # Hide main window
        sw = tk.Toplevel(self.root)
        
        def on_close():
            sw.destroy()
            self.root.deiconify()
            self.root.state('zoomed')
            
        sw.protocol("WM_DELETE_WINDOW", on_close)
        
        sw.title(" محرك البحث والطباعة الذكي")
        sw.geometry("1400x800")
        sw.state('zoomed')
        self.center_window(sw, self.root)
        sw.configure(bg="#ecf0f1") # Modern soft gray background

        # --- Header Section (Luxury Style) ---
        header = tk.Frame(sw, bg=SIDEBAR_COLOR, height=80)
        header.pack(fill=tk.X)
        
        # Branding Title
        title_frame = tk.Frame(header, bg=SIDEBAR_COLOR)
        title_frame.pack(side=tk.RIGHT, padx=30, pady=20)
        tk.Label(title_frame, text=UI_TEXTS[self.lang]['search_title'], fg="white", bg=SIDEBAR_COLOR, font=('Segoe UI', 18, 'bold')).pack(anchor='e')
        tk.Label(title_frame, text=UI_TEXTS[self.lang]['search_subtitle'], fg="#bdc3c7", bg=SIDEBAR_COLOR, font=('Segoe UI', 9)).pack(anchor='e')

        # Control Buttons (Header)
        btn_frame = tk.Frame(header, bg=SIDEBAR_COLOR)
        btn_frame.pack(side=tk.LEFT, padx=20)

        def btn_hover(btn, c_enter, c_leave):
            btn.bind("<Enter>", lambda e: btn.config(bg=c_enter))
            btn.bind("<Leave>", lambda e: btn.config(bg=c_leave))

        btn_exit_search = tk.Button(btn_frame, text=UI_TEXTS[self.lang]['exit'].split()[0], font=('Segoe UI', 11, 'bold'),
                                    bg="#c0392b", fg="white", cursor="hand2", width=12, relief="flat",
                                    command=self.exit_app)
        btn_exit_search.pack(side=tk.LEFT, padx=10)
        btn_hover(btn_exit_search, "#e74c3c", "#c0392b")

        btn_back = tk.Button(btn_frame, text=UI_TEXTS[self.lang]['back_to_menu'], font=('Segoe UI', 11, 'bold'), 
                             bg="#7f8c8d", fg="white", cursor="hand2", width=15, relief="flat",
                             command=on_close)
        btn_back.pack(side=tk.LEFT, padx=10)
        btn_hover(btn_back, "#95a5a6", "#7f8c8d")

        # --- Main Content Area ---
        main_scroll_frame = tk.Frame(sw, bg="#ecf0f1")
        main_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        
        # --- Filter Card (The "Luxury" Box) ---
        filter_card = tk.LabelFrame(main_scroll_frame, text=f"  {UI_TEXTS[self.lang]['search_criteria']}  ", font=('Segoe UI', 14, 'bold'),
                                  bg="white", fg=SIDEBAR_COLOR, bd=0, highlightbackground="#dcdde1", highlightthickness=1)
        filter_card.pack(fill=tk.X, ipadx=20, ipady=15)

        # 1. Smart Search Row (The Hero Input)
        search_row = tk.Frame(filter_card, bg="white")
        search_row.pack(fill=tk.X, pady=(10, 20), padx=20)
        
        tk.Label(search_row, text=UI_TEXTS[self.lang]['smart_search'], bg="white", fg=ACCENT_COLOR, font=('Segoe UI', 12, 'bold')).pack(side=tk.RIGHT if self.lang=='ar' else tk.LEFT, padx=10)
        
        self.smart_search = tk.Entry(search_row, font=('Segoe UI', 13), justify='right' if self.lang=='ar' else 'left', bg="#f8f9fa", relief="flat", highlightbackground="#bdc3c7", highlightthickness=1)
        self.smart_search.pack(side=tk.RIGHT if self.lang=='ar' else tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.add_context_menu(self.smart_search)
        
        tk.Label(search_row, text=UI_TEXTS[self.lang]['search_placeholder'], bg="white", fg="gray", font=('Segoe UI', 9)).pack(side=tk.RIGHT if self.lang=='ar' else tk.LEFT, padx=10)

        # 2. Filters Grid (Dates & Age)
        filters_grid = tk.Frame(filter_card, bg="white")
        filters_grid.pack(fill=tk.X, padx=20)

        # Helper to create styled date section
        def create_modern_date(parent, title, var_check):
            # Luxury Cream Background & Gold Title
            BOX_BG = "#fef9e7"
            TITLE_FG = "#b7950b"
            
            f = tk.LabelFrame(parent, text=f"  {title}  ", font=('Segoe UI', 11, 'bold'), bg=BOX_BG, fg=TITLE_FG)
            cb = tk.Checkbutton(f, text=UI_TEXTS[self.lang]['enable'], variable=var_check, bg=BOX_BG, activebackground=BOX_BG, font=('Segoe UI', 10), cursor="hand2")
            cb.pack(anchor='ne' if self.lang=='ar' else 'nw', padx=5)
            
            inner = tk.Frame(f, bg=BOX_BG); inner.pack(pady=5, padx=5)
            
            # Create boxes
            def d_box(lbl):
                b = tk.Frame(inner, bg=BOX_BG)
                b.pack(side=tk.RIGHT, padx=5)
                tk.Label(b, text=lbl, bg=BOX_BG, fg="gray", font=('Segoe UI', 9)).pack(anchor='e')
                de = DateEntry(b, width=12, background=SIDEBAR_COLOR, foreground="white", borderwidth=0, font=('Segoe UI', 10), 
                               date_pattern='dd-mm-yyyy', justify='center')
                de.pack()
                return de
            
            de_from = d_box(UI_TEXTS[self.lang]['from'])
            de_to = d_box(UI_TEXTS[self.lang]['to'])
            return f, de_from, de_to

        self.use_date_filter = tk.BooleanVar(value=False)
        self.use_contract_filter = tk.BooleanVar(value=False)
        self.use_age_filter = tk.BooleanVar(value=False)

        # Col 3: Timestamp (Rightmost)
        ts_frame, self.date_from_de, self.date_to_de = create_modern_date(filters_grid, UI_TEXTS[self.lang]['reg_date'], self.use_date_filter)
        ts_frame.pack(side=tk.RIGHT if self.lang=='ar' else tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        # Col 2: Contract Date
        cn_frame, self.contract_from_de, self.contract_to_de = create_modern_date(filters_grid, UI_TEXTS[self.lang]['contract_expiry'], self.use_contract_filter)
        cn_frame.pack(side=tk.RIGHT if self.lang=='ar' else tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        # Col 1: Age (Leftmost)
        # Luxury Cream Background & Gold Title
        BOX_BG = "#fef9e7"
        TITLE_FG = "#b7950b"
        
        age_frame = tk.LabelFrame(filters_grid, text=f"  {UI_TEXTS[self.lang]['age']}  ", font=('Segoe UI', 11, 'bold'), bg=BOX_BG, fg=TITLE_FG)
        age_frame.pack(side=tk.RIGHT if self.lang=='ar' else tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Checkbutton(age_frame, text=UI_TEXTS[self.lang]['enable'], variable=self.use_age_filter, bg=BOX_BG, activebackground=BOX_BG, font=('Segoe UI', 10), cursor="hand2").pack(anchor='ne' if self.lang=='ar' else 'nw', padx=5)
        
        af_inner = tk.Frame(age_frame, bg=BOX_BG); af_inner.pack(pady=12) # Align visually with dates
        
        # From (Right/Left)
        tk.Label(af_inner, text=UI_TEXTS[self.lang]['from'], bg=BOX_BG, fg="gray", font=('Segoe UI', 9)).pack(side=tk.RIGHT if self.lang=='ar' else tk.LEFT, padx=(5, 2))
        self.age_from = tk.Entry(af_inner, width=5, justify='center', font=('Segoe UI', 11), relief="solid", bd=1)
        self.age_from.pack(side=tk.RIGHT if self.lang=='ar' else tk.LEFT, padx=2)
        
        # To (Left/Right)
        tk.Label(af_inner, text=UI_TEXTS[self.lang]['to'], bg=BOX_BG, fg="gray", font=('Segoe UI', 9)).pack(side=tk.RIGHT if self.lang=='ar' else tk.LEFT, padx=(10, 2))
        self.age_to = tk.Entry(af_inner, width=5, justify='center', font=('Segoe UI', 11), relief="solid", bd=1)
        self.age_to.pack(side=tk.RIGHT if self.lang=='ar' else tk.LEFT, padx=2)

        self.add_context_menu(self.age_from)
        self.add_context_menu(self.age_to)

        # 3. Action Buttons Section
        actions_row = tk.Frame(filter_card, bg="white")
        actions_row.pack(fill=tk.X, pady=(20, 5))
        
        btn_print = tk.Button(actions_row, text=UI_TEXTS[self.lang]['print_report'], bg=SIDEBAR_COLOR, fg="white", 
                              font=('Segoe UI', 12, 'bold'), relief="flat", cursor="hand2", padx=30, pady=5,
                              command=self.print_results)
        btn_print.pack(side=tk.LEFT if self.lang=='en' else tk.RIGHT, padx=20)
        btn_hover(btn_print, "#34495e", SIDEBAR_COLOR)

        btn_search = tk.Button(actions_row, text=UI_TEXTS[self.lang]['search_now'], bg=SUCCESS_COLOR, fg="white", 
                               font=('Segoe UI', 12, 'bold'), relief="flat", cursor="hand2", padx=40, pady=5,
                               command=self.perform_search)
        btn_search.pack(side=tk.LEFT if self.lang=='en' else tk.RIGHT, padx=10) # Centered-ish relative to card
        btn_hover(btn_search, "#2ecc71", SUCCESS_COLOR)
        
        # --- Results Section ---
        
        # Status Bar
        self.search_status = tk.Label(main_scroll_frame, text=UI_TEXTS[self.lang]['ready'], bg="#ecf0f1", fg="#7f8c8d", font=('Segoe UI', 11))
        self.search_status.pack(pady=(20, 5), anchor='e' if self.lang=='ar' else 'w')

        # Treeview Container with Shadow Effect (Frame within Frame)
        res_container = tk.Frame(main_scroll_frame, bg="white", bd=0, highlightbackground="#dcdde1", highlightthickness=1)
        res_container.pack(fill=tk.BOTH, expand=True)

        style = ttk.Style()
        style.configure("Search.Treeview", background="white", foreground="#2c3e50", rowheight=40, font=('Segoe UI', 10))
        style.configure("Search.Treeview.Heading", font=('Segoe UI', 11, 'bold'), background="#ecf0f1", foreground=SIDEBAR_COLOR)
        style.map("Search.Treeview", background=[('selected', ACCENT_COLOR)])

        sy = ttk.Scrollbar(res_container); sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(res_container, orient="horizontal"); sx.pack(side=tk.BOTTOM, fill=tk.X)
        self.s_tree = ttk.Treeview(res_container, yscrollcommand=sy.set, xscrollcommand=sx.set, style="Search.Treeview")
        self.s_tree.pack(fill=tk.BOTH, expand=True)
        sy.config(command=self.s_tree.yview); sx.config(command=self.s_tree.xview)

    def add_context_menu(self, widget):
        # 1. Define robust clipboard functions
        def do_copy(event=None):
            try:
                if widget.selection_present():
                    text = widget.selection_get()
                    widget.clipboard_clear()
                    widget.clipboard_append(text)
                    widget.update() # Required to finalize clipboard
            except: pass
            return 'break'

        def do_cut(event=None):
            try:
                if widget.selection_present():
                    do_copy()
                    widget.delete("sel.first", "sel.last")
            except: pass
            return 'break'

        def do_paste(event=None):
            try:
                text = widget.clipboard_get()
                if text:
                    # If text is selected, replace it
                    if widget.selection_present():
                        widget.delete("sel.first", "sel.last")
                    widget.insert(tk.INSERT, text)
            except: pass
            return 'break'

        def do_select_all(event=None):
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
            return 'break'

        # 2. Key Bindings (Capture both Lower and Upper case)
        # Note: on some layouts or caps lock, keys might be sent differently.
        for key in ["<Control-c>", "<Control-C>", "<Control-Key-c>", "<Control-Key-C>"]:
            widget.bind(key, do_copy)
            
        for key in ["<Control-v>", "<Control-V>", "<Control-Key-v>", "<Control-Key-V>"]:
            widget.bind(key, do_paste)
            
        for key in ["<Control-x>", "<Control-X>", "<Control-Key-x>", "<Control-Key-X>"]:
            widget.bind(key, do_cut)
            
        for key in ["<Control-a>", "<Control-A>", "<Control-Key-a>", "<Control-Key-A>"]:
            widget.bind(key, do_select_all)

        # 3. Simple Undo (Ctrl+Z) - Single Step
        self._last_val = widget.get()
        def save_state(e):
            # Save state on any modifying key
            if e.keysym not in ['Control_L', 'Control_R', 'Alt_L', 'Shift_L', 'z', 'Z', 'c', 'v', 'x', 'a']:
                self._last_val = widget.get()
        
        def do_undo(event=None):
            try:
                current = widget.get()
                if current != self._last_val:
                    widget.delete(0, tk.END)
                    widget.insert(0, self._last_val)
            except: pass
            return 'break'

        widget.bind("<KeyPress>", save_state, add="+")
        for key in ["<Control-z>", "<Control-Z>"]:
            widget.bind(key, do_undo)

        # 4. Context Menu
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="نسخ (Ctrl+C)", command=do_copy)
        menu.add_command(label="لصق (Ctrl+V)", command=do_paste)
        menu.add_command(label="قص (Ctrl+X)", command=do_cut)
        menu.add_separator()
        menu.add_command(label="تحديد الكل (Ctrl+A)", command=do_select_all)

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)
            return "break"
        widget.bind("<Button-3>", show_menu)

    def clean_date_str(self, s):
        if not s: return ""
        # Convert Eastern Arabic numerals to Western
        arabic_to_western = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        s = str(s).translate(arabic_to_western)
        # Remove Arabic AM/PM markers
        s = s.replace('ص', '').replace('م', '')
        # Extract the date part (e.g., portions with / or -)
        parts = s.split()
        for p in parts:
            if '/' in p or '-' in p:
                return p
        return s

    def normalize_phone(self, text):
        """Removes non-digits, strips leading 966 or 0 to get the core number."""
        digits = "".join(filter(str.isdigit, str(text)))
        if not digits: return ""
        # Remove Saudi country code if present
        if digits.startswith("966"): digits = digits[3:]
        # Remove leading zero if present
        if digits.startswith("0"): digits = digits[1:]
        return digits

    def perform_search(self):
        if not self.all_data_raw: 
            messagebox.showinfo("تنبيه", "جارِ تحميل البيانات، يرجى الانتظار ثانية ثم المحاولة مرة أخرى.")
            return
            
        headers_raw = self.all_data_raw[0]
        data = self.all_data_raw[1:]
        
        # Look for columns
        d_idx, c_idx, a_idx, p_idx = -1, -1, -1, -1
        for i, h in enumerate(headers_raw):
            norm_h = self.normalize_text(h)
            if any(k in norm_h for k in ["timestamp", "طابع زمني", "تاريخ التسجيل", "تاريخ القيد"]): d_idx = i
            if any(k in norm_h for k in ["contract end", "تاريخ انتهاء العقد", "when is your contract", "انتهاء العقد"]): c_idx = i
            if any(k in norm_h for k in ["your age", "السن", "عمر", "age", "العمر"]): a_idx = i
            # Phone Column Detection
            if any(k in norm_h for k in ["phone number", "رقم الجوال", "mobile", "رقم الهاتف"]): p_idx = i
            
        # Fallback for Contract Date
        if c_idx == -1:
            for i, h in enumerate(headers_raw):
                norm_h = self.normalize_text(h)
                if "تاريخ" in norm_h and "عقد" in norm_h:
                    c_idx = i; break

        # Support both space and & for query splitting. 
        # Most users use spaces, but we keep & for backward compatibility.
        raw_query = self.smart_search.get().lower().strip()
        if '&' in raw_query:
            query_terms = [q.strip() for q in raw_query.split('&') if q.strip()]
        else:
            query_terms = [q.strip() for q in raw_query.split() if q.strip()]
        
        # Get dates for Timestamp filter
        d_f = self.date_from_de.get_date().strftime('%Y-%m-%d')
        d_t = self.date_to_de.get_date().strftime('%Y-%m-%d')
        
        # Get dates for Contract filter
        c_f = self.contract_from_de.get_date().strftime('%Y-%m-%d')
        c_t = self.contract_to_de.get_date().strftime('%Y-%m-%d')

        ag_f = self.age_from.get().strip()
        ag_t = self.age_to.get().strip()

        results = []
        for row in data:
            match = True
            
            # --- Smart Match Logic ---
            row_str = " ".join([str(v).lower() for v in row])
            
            for q in query_terms:
                term_found = False
                
                # 1. Normal Text Search
                if q in row_str: 
                    term_found = True
                
                # 2. Smart Phone Search
                if not term_found and sum(c.isdigit() for c in q) >= 5:
                    q_core = self.normalize_phone(q)
                    if q_core:
                        if p_idx != -1 and p_idx < len(row):
                            cell_core = self.normalize_phone(row[p_idx])
                            if q_core in cell_core: term_found = True
                        if not term_found:
                             for cell in row:
                                 if self.normalize_phone(cell) and q_core in self.normalize_phone(cell):
                                     term_found = True; break
                
                # 3. Translation Search (Phrasal Priority + Global Normalization)
                if not term_found:
                    # Try Whole Phrase First
                    full_translated = self.translator.translate(q)
                    keywords = []
                    if full_translated:
                        keywords.extend(full_translated.lower().split())
                    
                    # Also try individual words if it's a multi-word query
                    q_words = q.split()
                    if len(q_words) > 1:
                        for qw in q_words:
                            w_trans = self.translator.translate(qw)
                            if w_trans: keywords.extend(w_trans.lower().split())
                    
                    keywords.append(self.normalize_text(q))
                    
                    # Search ALL columns cell by cell (Ultra Accurate)
                    row_norm_str = self.normalize_text(" ".join([str(v) for v in row]))
                    for kw in keywords:
                        if len(kw) < 2: continue
                        if kw in row_norm_str:
                            term_found = True
                            break
                
                if not term_found:
                    match = False
                    break
            
            if not match: continue

            # Age filter (only if checkbox is checked)
            if self.use_age_filter.get() and (ag_f or ag_t):
                if a_idx != -1 and a_idx < len(row):
                    try:
                        age_val_raw = str(row[a_idx]).strip()
                        # Extract only digits from age (handles "25 سنة" or "25 years")
                        age_digits = "".join(filter(str.isdigit, age_val_raw))
                        if age_digits:
                            age = int(age_digits)
                            if ag_f and age < int(ag_f): match = False
                            if ag_t and age > int(ag_t): match = False
                        else: match = False
                    except: match = False
                else: 
                    # If column not found but filter enabled, we can't filter positively
                    # We'll skip for now to avoid false negatives if user expected results
                    pass 

            if not match: continue

            # Timestamp Date filter (only if checkbox is checked)
            if self.use_date_filter.get() and d_idx != -1 and d_idx < len(row):
                try:
                    cleaned_date = self.clean_date_str(row[d_idx])
                    if cleaned_date:
                        dt = parser.parse(cleaned_date, dayfirst=True).date()
                        if d_f and dt < parser.parse(d_f).date(): match = False
                        if d_t and dt > parser.parse(d_t).date(): match = False
                    else: match = False
                except: match = False
            if not match: continue

            # Contract Date filter (only if checkbox is checked)
            if self.use_contract_filter.get() and c_idx != -1 and c_idx < len(row):
                try:
                    cleaned_date = self.clean_date_str(row[c_idx])
                    if cleaned_date:
                        dt = parser.parse(cleaned_date, dayfirst=True).date()
                        if c_f and dt < parser.parse(c_f).date(): match = False
                        if c_t and dt > parser.parse(c_t).date(): match = False
                    else: match = False
                except: match = False
            
            if match:
                # Create a copy for display to enforce specific formatting
                row_display = list(row)
                
                # Enforce YYYY/MM/DD format for Contract Date
                if c_idx != -1 and c_idx < len(row):
                    try:
                        cleaned = self.clean_date_str(row[c_idx])
                        if cleaned:
                            # Use consistent 2026/02/21 format as requested
                            dt_obj = parser.parse(cleaned, dayfirst=True)
                            row_display[c_idx] = dt_obj.strftime('%Y/%m/%d')
                    except: pass
                    
                results.append(row_display)

        res_msg = "Results found" if self.lang == 'en' else "نتيجة تم العثور عليها"
        self.search_status.config(text=f"{len(results)} {res_msg}")

        headers = [self.translate_header(h) for h in headers_raw]
        self.s_tree.delete(*self.s_tree.get_children())
        self.s_tree["columns"] = headers
        for h in headers:
            self.s_tree.heading(h, text=h, anchor=tk.CENTER)
            w = 190
            if len(h) > 25: w = 350 # Dynamic width for long headers
            self.s_tree.column(h, width=w, minwidth=140, stretch=True, anchor=tk.CENTER)
        for r in results: self.s_tree.insert("", tk.END, values=r)

    def print_results(self):
        items = self.s_tree.get_children()
        if not items: return messagebox.showinfo("Alert" if self.lang=='en' else "تنبيه", UI_TEXTS[self.lang]['no_results'])
        report_name = f"search_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(report_name, "w", encoding="utf-8") as f:
            f.write(f"{'Search Report' if self.lang=='en' else 'تقرير البحث'} - {PROGRAMMER_NAME}\n")
            f.write("="*50 + "\n")
            for item in items:
                vals = self.s_tree.item(item)['values']
                f.write(" | ".join([str(v) for v in vals]) + "\n")
        messagebox.showinfo("Success" if self.lang=='en' else "نجاح", f"{UI_TEXTS[self.lang]['report_saved']}\n{report_name}")

# --- Translation & Search Helpers ---

class TranslationManager:
    def __init__(self):
        # Common Arabic to English mapping for recruitment & contracts
        raw_mapping = {
            # Job Titles (Hospitality & Food)
            "باريستا": "barista", "طباخ": "cook", "شيف": "chef", "نادل": "waiter", "نادلة": "waitress",
            "طعام": "food center server", "بوفيه": "buffet",
            
            # Medical & Healthcare
            "ممرض": "nurse", "ممرضه": "nurse", "طبيب": "doctor", "صيدلي": "pharmacist",
            
            # Domestic & Cleaning (Vast synonyms for max hits)
            "عامل": "worker labor helper assistant", "عاملة": "laborer helper servant housemaid maid", "عامله": "laborer helper servant housemaid maid",
            "شغاله": "housemaid cleaner maid servant laundry cleaning", "خادمه": "housemaid cleaner maid servant cleaning",
            "نظافه": "clean cleaning cleaner hygiene housemaid laundry maid servant labor laborer helper nadhafa",
            "نظافة": "clean cleaning cleaner hygiene housemaid laundry maid servant labor laborer helper nadhafa",
            "تنظيف": "clean cleaning cleaner laundry", "منظف": "clean cleaner cleaning",
            "عامل نظافه": "cleaner labor cleaning worker housemaid maid cleaning", "عامل نظافة": "cleaner labor cleaning worker housemaid maid cleaning",
            
            # Drivers & Logistics
            "سائق": "driver pilot transport car", "سواق": "driver car taxi", "توصيل": "delivery courier", "مندوب": "representative sales agent",
            
            # Technical & Construction
            "مهندس": "engineer engineering", "فني": "technician tech repair maintenance mechanic fanni", "كهربائي": "electrician electrical", "سباك": "plumber plumbing",
            "كاميرات": "camera cctv monitor security", "مبرمج كاميرا": "camera programmer tech",
            
            # Office & Administrative
            "محاسب": "accountant accounting accounts finance bookkeeper auditor muhasib", "مدير": "manager management supervisor leader", "سكرتير": "secretary admin", "استقبال": "receptionist reception",
            "موارد بشريه": "hr human resources recruitment", "أعمال مكتبية": "office admin work clerk desk secretary", "مكتبيه": "office admin clerk desk",
            
            # Sales & Beauty
            "بائع": "sales selling shop buyer dealer", "كاشير": "cashier counter teller", "كوافير": "hairdresser hair salon beauty", "مصففة شعر": "hairdresser hair beauty",
            "صالون": "salon beauty spa haircut makeup", "صالون نسائي": "ladies salon beauty",
            "بدكير": "pedicure foot nail spa beauty", "منكير": "manicure nail hand spa beauty", "بدكير ومنكير": "pedicure manicure nail beauty hand foot beauty",
            "بدكير منكير": "pedicure manicure nail beauty hand foot beauty spa", "مساج": "massage spa relaxation therapist massage",
            
            # Nationalities
            "هند": "india indian", "فلبين": "philippines filipino filipina",
            "مصر": "egypt egyptian", "باكستان": "pakistan pakistani",
            "نيبال": "nepal nepali", "بنجلاديش": "bangladesh bangladeshi",
            "سريلانكا": "sri lanka lankan", "كينيا": "kenya kenyan",
            "اوغندا": "uganda ugandan", "اثيوبيا": "ethiopia ethiopian",
            "اندونيسيا": "indonesia indonesian", "فيتنام": "vietnam vietnamese",
        }
        
        # Normalize all keys at startup for consistent lookup
        self.mapping = {}
        for k, v in raw_mapping.items():
            norm_k = self._norm_key(k)
            self.mapping[norm_k] = v

    def _norm_key(self, s):
        # Mirroring ContractMonitorApp result for consistency
        s = str(s).lower().strip().replace('\xa0', ' ')
        s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
        s = s.replace('ض', 'ظ').replace('ظ', 'ظ').replace('ذ', 'ز').replace('ز', 'ز')
        s = s.replace('ث', 'س').replace('س', 'س').replace('ق', 'ج').replace('ك', 'ج').replace('ج', 'ج')
        return s

    def translate(self, text):
        if not text: return ""
        norm_text = self._norm_key(text)
        
        # 1. Direct match (Normalized lookup)
        if norm_text in self.mapping:
            return self.mapping[norm_text]
        
        # 2. Global Replacement / Word based
        words = norm_text.split()
        translated_result = []
        for w in words:
            if w in self.mapping:
                translated_result.append(self.mapping[w])
            else:
                translated_result.append(w)
        
        # Return composite string
        return " ".join(translated_result)

# --- Authentication System ---

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")
IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image", "السعيد.jpg")

class AuthManager:
    def __init__(self):
        self.users = {}
        self.load_users()

    def load_users(self):
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get("users", {})
            except: self.users = {}
        else:
            # Default fallback if file missing
            self.users = {
                "admin": {
                    "password": hashlib.sha256("admin123".encode()).hexdigest(),
                    "role": "admin",
                    "can_manage_users": True # Admin always has access
                }
            }
            self.save_users()

    def save_users(self):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"users": self.users}, f, indent=4)

    def authenticate(self, username, password):
        if username in self.users:
            hashed = hashlib.sha256(password.encode()).hexdigest()
            if self.users[username]["password"] == hashed:
                return True
        return False

    def has_permission(self, username):
        """Checks if the user can access the Permissions screen."""
        if username in self.users:
            return self.users[username].get("can_manage_users", False)
        return False

    def add_user(self, username, password, lang='ar', can_manage_users=False):
        """Adds a new user to the system."""
        if username in self.users:
            return False, UI_TEXTS[lang]['user_exists']
        
        self.users[username] = {
            "password": hashlib.sha256(password.encode()).hexdigest(),
            "role": "user",
            "can_manage_users": can_manage_users
        }
        self.save_users()
        return True, UI_TEXTS[lang]['user_added']

    def change_password(self, username, new_password):
        if username in self.users:
            self.users[username]["password"] = hashlib.sha256(new_password.encode()).hexdigest()
            self.save_users()
            return True
        return False

    def delete_user(self, username):
        if username in self.users and username != "admin":
            del self.users[username]
            self.save_users()
            return True
        return False

class LoginWindow:
    def __init__(self, lang='ar'):
        self.lang = lang
        self.root = tk.Tk()
        self.root.title(UI_TEXTS[self.lang]['login_title'])
        if os.path.exists(ICON_PATH):
            try: self.root.iconbitmap(ICON_PATH)
            except: pass
        self.root.geometry("600x350")
        self.root.resizable(False, False)
        self.center_window()
        self.auth_manager = AuthManager()

        # Layout: Left (Image), Right (Login Form)
        # Left Side
        left_frame = tk.Frame(self.root, bg="#2c3e50", width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)

        try:
            pil_img = Image.open(IMAGE_PATH)
            pil_img = pil_img.resize((180, 220), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(pil_img)
            lbl_img = tk.Label(left_frame, image=self.photo, bg="#2c3e50")
            lbl_img.pack(pady=(40, 10))
        except Exception as e:
            tk.Label(left_frame, text=UI_TEXTS[self.lang]['img_not_found'], bg="#2c3e50", fg="white").pack(pady=50)

        tk.Label(left_frame, text="Programmed by\nAl-Saeed Al-Wazzan", font=('Segoe UI', 10, 'bold'), fg="#ecf0f1", bg="#2c3e50").pack(pady=10)

        # Right Side
        right_frame = tk.Frame(self.root, bg="white")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Language Toggle in Login
        def toggle_lang():
            self.lang = 'en' if self.lang == 'ar' else 'ar'
            self.root.destroy()
            LoginWindow(self.lang).run()

        btn_lang = tk.Button(right_frame, text=UI_TEXTS[self.lang]['lang_btn'], font=('Segoe UI', 9), bg="#f8f9fa", relief="flat", command=toggle_lang)
        btn_lang.pack(anchor='nw' if self.lang=='en' else 'ne', padx=10, pady=5)

        tk.Label(right_frame, text=UI_TEXTS[self.lang]['login_title'], font=('Segoe UI', 18, 'bold'), bg="white", fg="#2c3e50").pack(pady=(20, 20))

        # Username
        tk.Label(right_frame, text=UI_TEXTS[self.lang]['username'], font=('Segoe UI', 10), bg="white").pack(anchor='e' if self.lang=='ar' else 'w', padx=40)
        self.entry_user = tk.Entry(right_frame, font=('Segoe UI', 11), justify='center', bg="#ecf0f1", relief="flat")
        self.entry_user.pack(fill=tk.X, padx=40, pady=5, ipady=3)

        # Password
        tk.Label(right_frame, text=UI_TEXTS[self.lang]['password'], font=('Segoe UI', 10), bg="white").pack(anchor='e' if self.lang=='ar' else 'w', padx=40)
        self.entry_pass = tk.Entry(right_frame, show="•", font=('Segoe UI', 11), justify='center', bg="#ecf0f1", relief="flat")
        self.entry_pass.pack(fill=tk.X, padx=40, pady=5, ipady=3)
        self.entry_pass.bind('<Return>', lambda e: self.do_login())

        # Button
        btn_login = tk.Button(right_frame, text=UI_TEXTS[self.lang]['login_btn'], font=('Segoe UI', 11, 'bold'), bg="#3498db", fg="white", relief="flat", command=self.do_login)
        btn_login.pack(fill=tk.X, padx=40, pady=30, ipady=5)

    def center_window(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'+{x}+{y}')

    def do_login(self):
        user = self.entry_user.get().strip()
        pwd = self.entry_pass.get().strip()
        
        if self.auth_manager.authenticate(user, pwd):
            self.root.destroy()
            # Start Main App Directly
            root = tk.Tk()
            app = ContractMonitorApp(root, current_user=user)
            app.lang = self.lang
            app.apply_lang()
            root.mainloop()
        else:
            messagebox.showerror(UI_TEXTS[self.lang]['login_error_title'], UI_TEXTS[self.lang]['login_error_msg'])

    def run(self):
        self.root.mainloop()

class PermissionsWindow:
    def __init__(self, current_user, lang='ar'):
        self.current_user = current_user
        self.lang = lang
        self.root = tk.Tk()
        self.root.title(UI_TEXTS[self.lang]['perms_title'])
        if os.path.exists(ICON_PATH):
            try: self.root.iconbitmap(ICON_PATH)
            except: pass
        self.root.geometry("1200x850")
        self.center_window()
        self.auth_manager = AuthManager()

        # Header
        header = tk.Frame(self.root, bg="#2c3e50", height=80)
        header.pack(fill=tk.X)
        tk.Label(header, text=UI_TEXTS[self.lang]['perms_header'], font=('Segoe UI', 24, 'bold'), fg="white", bg="#2c3e50").pack(pady=15)

        # Main Content
        container = tk.Frame(self.root, bg="#ecf0f1")
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)

        # Top Section: Forms
        forms_frame = tk.Frame(container, bg="#ecf0f1")
        forms_frame.pack(fill=tk.X, pady=10)

        # LEFT: Add User Card
        left_card = tk.LabelFrame(forms_frame, text=f"  {UI_TEXTS[self.lang]['add_user']}  ", font=('Segoe UI', 12, 'bold'), bg="white", padx=20, pady=20)
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        tk.Label(left_card, text=UI_TEXTS[self.lang]['username'], font=('Segoe UI', 10), bg="white").pack(anchor='w', padx=10)
        self.entry_add_user = tk.Entry(left_card, font=('Segoe UI', 11), bg="#f8f9fa", relief="solid", bd=1)
        self.entry_add_user.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(left_card, text=UI_TEXTS[self.lang]['password'], font=('Segoe UI', 10), bg="white").pack(anchor='w', padx=10)
        self.entry_add_pass = tk.Entry(left_card, show="•", font=('Segoe UI', 11), bg="#f8f9fa", relief="solid", bd=1)
        self.entry_add_pass.pack(fill=tk.X, padx=10, pady=5)

        self.var_can_manage = tk.BooleanVar(value=False)
        tk.Checkbutton(left_card, text=UI_TEXTS[self.lang]['can_manage'], variable=self.var_can_manage, bg="white").pack(pady=5)

        tk.Button(left_card, text=UI_TEXTS[self.lang]['add_btn'], font=('Segoe UI', 11, 'bold'), bg="#8e44ad", fg="white", command=self.do_add_user).pack(fill=tk.X, padx=10, pady=10)

        # RIGHT: Change Pass / Info
        right_card = tk.LabelFrame(forms_frame, text=f"  {UI_TEXTS[self.lang]['change_pass']}  ", font=('Segoe UI', 12, 'bold'), bg="white", padx=20, pady=20)
        right_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        tk.Label(right_card, text=f"{UI_TEXTS[self.lang]['welcome']} {current_user}", font=('Segoe UI', 11), bg="white").pack(pady=5)
        
        tk.Label(right_card, text=UI_TEXTS[self.lang]['new_pass'], font=('Segoe UI', 10), bg="white").pack(anchor='w', padx=10)
        self.entry_new_pass = tk.Entry(right_card, show="•", font=('Segoe UI', 11), bg="#f8f9fa", relief="solid", bd=1)
        self.entry_new_pass.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(right_card, text=UI_TEXTS[self.lang]['save_btn'], font=('Segoe UI', 11, 'bold'), bg="#27ae60", fg="white", command=self.do_change_pass).pack(fill=tk.X, padx=10, pady=10)

        # BOTTOM: User Management Table
        list_frame = tk.LabelFrame(container, text="  قائمة المستخدمين المتاحين للتحكم  " if self.lang=='ar' else "  User Management List  ", 
                                   font=('Segoe UI', 12, 'bold'), bg="white", padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        style = ttk.Style()
        style.configure("Users.Treeview", background="white", foreground="black", rowheight=30, font=('Segoe UI', 10))
        style.configure("Users.Treeview.Heading", font=('Segoe UI', 11, 'bold'))

        self.tree = ttk.Treeview(list_frame, columns=("user", "role", "manage"), show="headings", style="Users.Treeview")
        self.tree.heading("user", text="اسم المستخدم" if self.lang=='ar' else "Username")
        self.tree.heading("role", text="نوع الحساب" if self.lang=='ar' else "Role")
        self.tree.heading("manage", text="دخول الصلاحيات" if self.lang=='ar' else "Can Manage")
        
        self.tree.column("user", width=200, anchor='center')
        self.tree.column("role", width=150, anchor='center')
        self.tree.column("manage", width=150, anchor='center')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sc = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        sc.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=sc.set)

        # Control Row for Table
        ctrl_frame = tk.Frame(container, bg="#ecf0f1")
        ctrl_frame.pack(fill=tk.X, pady=10)

        self.btn_delete_user = tk.Button(ctrl_frame, text="حذف المستخدم المختار" if self.lang=='ar' else "Delete Selected User", 
                                        font=('Segoe UI', 12, 'bold'), bg="#c0392b", fg="white", width=25, height=2,
                                        command=self.do_delete_selected_user)
        self.btn_delete_user.pack(side=tk.RIGHT if self.lang=='ar' else tk.LEFT, padx=10)

        tk.Button(ctrl_frame, text=UI_TEXTS[self.lang]['back_home'], font=('Segoe UI', 12, 'bold'), bg="#3498db", fg="white", width=25, height=2,
                  command=self.go_to_main).pack(side=tk.LEFT if self.lang=='ar' else tk.RIGHT, padx=10)

        self.refresh_user_list()
        self.root.mainloop() # CRITICAL FIX

    def center_window(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def refresh_user_list(self):
        self.tree.delete(*self.tree.get_children())
        users = self.auth_manager.users
        for u, data in users.items():
            role = data.get("role", "user")
            manage = "نعم" if data.get("can_manage_users") else "لا"
            if self.lang == 'en':
                manage = "Yes" if data.get("can_manage_users") else "No"
            self.tree.insert("", tk.END, values=(u, role, manage))

    def do_delete_selected_user(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(UI_TEXTS[self.lang]['warning_title'], 
                                   "الرجاء اختيار مستخدم من القائمة أولاً" if self.lang=='ar' else "Please select a user first")
            return
        
        user = self.tree.item(sel[0])['values'][0]
        if user == "admin":
            messagebox.showerror(UI_TEXTS[self.lang]['login_error_title'], 
                                 "لا يمكن حذف حساب المدير الرئيسي" if self.lang=='ar' else "Cannot delete admin")
            return
            
        if messagebox.askyesno(UI_TEXTS[self.lang]['confirm_delete_title'], 
                              f"هل أنت متأكد من حذف المستخدم {user}؟" if self.lang=='ar' else f"Are you sure you want to delete {user}?"):
            if self.auth_manager.delete_user(user):
                messagebox.showinfo(UI_TEXTS[self.lang]['success'], UI_TEXTS[self.lang]['user_deleted'])
                self.refresh_user_list()
            else:
                messagebox.showerror(UI_TEXTS[self.lang]['login_error_title'], "خطأ في الحذف")

    def do_add_user(self):
        user = self.entry_add_user.get().strip()
        pwd = self.entry_add_pass.get().strip()
        can_manage = self.var_can_manage.get()
        
        if not user or not pwd:
            messagebox.showwarning(UI_TEXTS[self.lang]['warning_title'], UI_TEXTS[self.lang]['fields_required'])
            return
            
        success, msg = self.auth_manager.add_user(user, pwd, self.lang, can_manage)
        if success:
            messagebox.showinfo(UI_TEXTS[self.lang]['success'], msg)
            self.entry_add_user.delete(0, tk.END)
            self.entry_add_pass.delete(0, tk.END)
            self.var_can_manage.set(False)
            self.refresh_user_list()
        else:
            messagebox.showerror(UI_TEXTS[self.lang]['login_error_title'], msg)

    def do_change_pass(self):
        new_p = self.entry_new_pass.get().strip()
        if not new_p:
            messagebox.showwarning(UI_TEXTS[self.lang]['warning_title'], UI_TEXTS[self.lang]['pass_empty'])
            return
        
        if self.auth_manager.change_password(self.current_user, new_p):
            messagebox.showinfo(UI_TEXTS[self.lang]['success'], UI_TEXTS[self.lang]['pass_changed'])
            self.entry_new_pass.delete(0, tk.END)
        else:
            messagebox.showerror(UI_TEXTS[self.lang]['login_error_title'], UI_TEXTS[self.lang]['pass_error'])

    def go_to_main(self):
        self.root.destroy()
        # Start Main App
        app_root = tk.Tk()
        app = ContractMonitorApp(app_root, current_user=self.current_user)
        app.lang = self.lang
        app.apply_lang()
        app_root.mainloop()

    def exit_app(self):
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    # Hide console window if running on Windows (Silent mode)
    if os.name == 'nt':
        try:
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except: pass
    LoginWindow().run()
