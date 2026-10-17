
import re
import hashlib

# Cache for AI (machine) translations of worker values EN -> AR.
# Persists per-process; mirrored into st.session_state.translation_cache when available.
_AI_TVAL_CACHE = {}

_AI_TVAL_ERROR_SIGS = (
    "error 500", "server error", "that's an error", "that’s an error",
    "translation error", "<html", "<!doctype",
)

TRANSLATIONS = {
    # Login
    "welcome_back": {"ar": "أهلاً بك", "en": "WELCOME BACK"},
    "system_title": {"ar": "نظام مراقبة العقود", "en": "Contract Monitor System"},
    "username": {"ar": "اسم المستخدم", "en": "Username"},
    "password": {"ar": "كلمة المرور", "en": "Password"},
    "login_btn": {"ar": "دخول", "en": "LOGIN"},
    "invalid_creds": {"ar": "بيانات الدخول غير صحيحة", "en": "Invalid credentials"},
    "image_not_found": {"ar": "الصورة غير موجودة", "en": "Image not found"},
    "first_name_ar": {"ar": "الاسم الأول (بالعربي)", "en": "First Name (AR)"},
    "father_name_ar": {"ar": "اسم الأب (بالعربي)", "en": "Father's Name (AR)"},
    "first_name_en": {"ar": "الاسم الأول (إنجليزي)", "en": "First Name (EN)"},
    "father_name_en": {"ar": "اسم الأب (إنجليزي)", "en": "Father's Name (EN)"},
    "welcome_person": {"ar": "أهلاً بك يا {name}", "en": "Welcome, {name}"},
    
    # Sidebar
    "dashboard": {"ar": "الرئيسية", "en": "Dashboard"},
    "smart_search": {"ar": "البحث الذكي", "en": "Smart Search"},
    "cv_translator": {"ar": "ترجمة السير الذاتية", "en": "CV Translator"},
    "customer_requests": {"ar": "طلبات العملاء", "en": "Customer Requests"},
    "order_processing": {"ar": "معالجة الطلبات", "en": "Order Processing"},
    "permissions": {"ar": "الصلاحيات", "en": "Permissions"},
    "login_history": {"ar": "تاريخ الدخول", "en": "Login History"},
    "login_history_title": {"ar": "سجل تاريخ الدخول", "en": "Login History Log"},
    "last_login": {"ar": "آخر دخول", "en": "Last login"},
    "clear_history_btn": {"ar": "🗑️ مسح السجل", "en": "🗑️ Clear History"},
    "keep_history_btn": {"ar": "ترك البيانات كما هي بالسجل", "en": "Keep history as is"},
    "no_login_history": {"ar": "لا توجد سجلات دخول بعد", "en": "No login records yet"},
    "history_cleared": {"ar": "تم مسح سجل الدخول بنجاح ✅", "en": "Login history cleared successfully ✅"},
    "confirm_clear_history": {"ar": "هل أنت متأكد من مسح سجل الدخول نهائياً؟", "en": "Are you sure you want to permanently clear the login history?"},
    "whatsapp_marketing": {"ar": "واتساب ماركتنج (2026)", "en": "WhatsApp Marketing (2026)"},
    "duplicate_remover": {"ar": "حذف المكرر", "en": "Duplicate Remover"},
    "logout": {"ar": "تسجيل خروج", "en": "Logout"},
    "debug": {"ar": "فحص الأخطاء", "en": "Debug"},
    "test_db": {"ar": "فحص قاعدة البيانات", "en": "Test DB"},
    "programmer": {"ar": "Programmed by Alsaeed Alwazzan", "en": "Programmed by Alsaeed Alwazzan"},
    "welcome_toast": {"ar": "تم تسجيل الدخول بنجاح. أهلاً بك في نظام نايس!", "en": "Logged in successfully. Welcome to NICE System!"},
    "welcome_subtitle": {"ar": "برمجة السعيد الوزان", "en": "Programmed by Alsaeed Alwazzan"},
    
    # Dashboard
    "contract_dashboard": {"ar": "لوحة العقود", "en": "Contract Dashboard"},
    "no_data": {"ar": "لا توجد بيانات", "en": "No data found"},
    "urgent_7_days": {"ar": "عاجل (7 أيام)", "en": "Urgent (7 Days)"},
    "expired": {"ar": "العقود المنتهية", "en": "Expired Contracts"},
    "active": {"ar": "ساري", "en": "Active"},
    "urgent": {"ar": "عاجل", "en": "Urgent"},
    "cv_download": {"ar": "تحميل السيرة الذاتية", "en": "CV Download"},
    "download_pdf": {"ar": "تحميل PDF", "en": "Download PDF"},
    "tabs_urgent": {"ar": " عاجل", "en": " Urgent"},
    "tabs_expired": {"ar": " العقود المنتهية", "en": " Expired Contracts"},
    "tabs_active": {"ar": " ساري", "en": " Active"},

    # Search
    "smart_search_title": {"ar": "البحث الذكي (AI)", "en": "Smart Search"},
    "search_placeholder": {"ar": "مثال: سائق فلبيني، +96650...", "en": "e.g. Filipino Driver, +96650..."},
    "search_btn": {"ar": "بحث", "en": "Search"},
    "no_results": {"ar": "لا توجد نتائج", "en": "No results"},
    "advanced_filters": {"ar": "تصفية متقدمة", "en": "Advanced Filters"},
    "refresh_data_btn": {"ar": "تحديث البيانات من المصدر", "en": "Refresh Data from Source"},
    "preview_cv": {"ar": "معاينة", "en": "Preview"},
    "selected_worker": {"ar": "العامل المختار", "en": "Selected Worker"},
    "translate_cv_btn": {"ar": "ترجمة السيرة الذاتية لهذا العامل", "en": "Translate this Worker's CV"},
    "full_worker_info_btn": {"ar": "معلومات كاملة عن العامل", "en": "Full Worker Information"},
    "full_worker_info_title": {"ar": "البيانات الكاملة المسجلة للعامل", "en": "Complete Registered Worker Data"},
    "loading_cv": {"ar": "جاري جلب السيرة الذاتية...", "en": "Fetching CV..."},
    "close": {"ar": "إغلاق", "en": "Close"},

    # Translator
    "translator_title": {"ar": "ترجمة الملفات الاحترافية", "en": "Professional File Translator"},
    "translator_desc": {"ar": "ارفع ملف السيرة الذاتية (PDF) ليتم استخراج النص وترجمته للعربية.", "en": "Upload a CV (PDF) to translate it from English to Arabic automatically."},
    "translator_desc_new": {"ar": "ارفع ملفاتك (Word, PDF, صور, BDF) وسيتم ترجمتها تلقائياً مع الحفاظ على التنسيق الأصلي.", "en": "Upload your files (Word, PDF, Images, BDF) for automatic translation while preserving original formatting."},
    "upload_cv": {"ar": "رفع الملف", "en": "Upload CV"},
    "upload_file_label": {"ar": "📂 اسحب الملف هنا أو اضغط للاختيار", "en": "📂 Drag & drop file here or click to browse"},
    "translate_now": {"ar": "🚀 ابدأ الترجمة", "en": "🚀 Start Translation"},
    "extracting": {"ar": "جاري الاستخراج والترجمة...", "en": "Extracting & Translating..."},
    "original": {"ar": "النص الأصلي", "en": "Original Text"},
    "translated": {"ar": "النص المترجم", "en": "Translated Text"},
    "download_trans": {"ar": "⬇️ تحميل الملف المترجم", "en": "⬇️ Download Translated File"},
    "download_trans_txt": {"ar": "📄 تحميل كنص", "en": "📄 Download as Text"},
    "src_lang": {"ar": "لغة المصدر", "en": "Source Language"},
    "tgt_lang": {"ar": "لغة الهدف", "en": "Target Language"},
    "auto_detect": {"ar": "تلقائي (كشف تلقائي)", "en": "Auto Detect"},
    "translation_log": {"ar": "📋 سجل العمليات", "en": "📋 Operation Log"},
    "translation_progress": {"ar": "تقدم الترجمة", "en": "Translation Progress"},
    "file_detected": {"ar": "تم كشف نوع الملف", "en": "File type detected"},
    "supported_formats": {"ar": "الصيغ المدعومة", "en": "Supported Formats"},
    "translation_complete": {"ar": "✅ تمت الترجمة بنجاح!", "en": "✅ Translation completed successfully!"},
    "translation_failed": {"ar": "❌ فشلت الترجمة", "en": "❌ Translation failed"},
    "file_info": {"ar": "معلومات الملف", "en": "File Information"},
    "file_name": {"ar": "اسم الملف", "en": "File Name"},
    "file_size": {"ar": "حجم الملف", "en": "File Size"},
    "file_type": {"ar": "نوع الملف", "en": "File Type"},
    "no_file_uploaded": {"ar": "لم يتم رفع أي ملف بعد", "en": "No file uploaded yet"},
    "translating_wait": {"ar": "جارٍ الترجمة... يرجى الانتظار", "en": "Translating... Please wait"},

    # Permissions
    "permissions_title": {"ar": "إدارة الصلاحيات", "en": "Permissions Management"},
    "add_user": {"ar": "إضافة مستخدم جديد", "en": "Add New User"},
    "delete_user_btn": {"ar": "حذف المستخدم", "en": "Delete User"},
    "role": {"ar": "الصلاحية", "en": "Role"},
    "add_btn": {"ar": "إضافة", "en": "Add User"},
    "users_list": {"ar": "قائمة المستخدمين", "en": "Users List"},
    "edit_user": {"ar": "تعديل مستخدم", "en": "Edit User"},
    "select_user": {"ar": "اختر المستخدم", "en": "Select User"},
    "new_password": {"ar": "كلمة المرور الجديدة (اختياري)", "en": "New Password (Optional)"},
    "update_btn": {"ar": "تحديث البيانات", "en": "Update User"},
    "update_success": {"ar": "تم التحديث", "en": "Updated successfully"},
    "user_exists": {"ar": "المستخدم موجود مسبقاً", "en": "User already exists"},
    "user_added": {"ar": "تم الاضافة", "en": "User added successfully"},
    "image_error": {"ar": "خطأ في الصورة", "en": "Image Error"},
    
    # Common
    "error": {"ar": "خطأ", "en": "Error"},
    "success": {"ar": "نجاح", "en": "Success"},
    "delete_btn": {"ar": "🗑️ حذف السجل نهائياً", "en": "🗑️ Delete Record Permanently"},
    "confirm_delete_title": {"ar": "تأكيد الحذف النهائي", "en": "Confirm Permanent Deletion"},
    "confirm_delete_msg": {"ar": "تحذير: سيتم مسح بيانات هذا العامل نهائياً من ملف جوجل شيت. هل أنت متأكد؟", "en": "Warning: This worker's data will be permanently deleted from Google Sheets. Are you sure?"},
    "confirm_btn": {"ar": "نعم، احذف السجل", "en": "Yes, Delete Record"},
    "cancel_btn": {"ar": "إلغاء", "en": "Cancel"},
    "delete_success": {"ar": "تم حذف السجل من القاعدة بنجاح ✅", "en": "Record deleted from database successfully ✅"},
    "delete_error": {"ar": "عذراً، حدث خطأ أثناء الحذف. تأكد من صلاحيات الوصول.", "en": "Sorry, an error occurred during deletion. check permissions."},
    "deep_reset": {"ar": "🧼 تنظيف شامل (Deep Reset)", "en": "🧼 Deep Reset (Clear Cache)"},
    "fix_ids": {"ar": "🔄 إصلاح وتحديث المعرفات", "en": "🔄 Fix & Update IDs"},
    "deep_reset_desc": {"ar": "سيتم مسح كافة البيانات المؤقتة وإعادة التحميل من جوجل شيت.", "en": "Will clear all temporary data and reload from Google Sheets."},
    
    # Order Processing
    "order_processing_title": {"ar": "معالجة الطلبات", "en": "Order Processing"},
    "client_info": {"ar": "بيانات العميل", "en": "Client Information"},
    "company_name": {"ar": "اسم المنشأة", "en": "Company Name"},
    "responsible_name": {"ar": "اسم المسؤول", "en": "Responsible Person"},
    "mobile_number": {"ar": "رقم الجوال", "en": "Mobile Number"},
    "work_location": {"ar": "موقع العمل", "en": "Work Location"},
    "required_category": {"ar": "الفئة المطلوبة", "en": "Required Category"},
    "required_nationality": {"ar": "الجنسية المطلوبة", "en": "Required Nationality"},
    "work_nature": {"ar": "طبيعة العمل", "en": "Work Nature"},
    "num_employees": {"ar": "عدد الموظفين المطلوب", "en": "Number of Employees Required"},
    "expected_salary": {"ar": "الراتب المتوقع", "en": "Expected Salary"},
    "matching_workers": {"ar": "العمال المطابقون", "en": "Matching Workers"},
    "no_matching_workers": {"ar": "لا يوجد عمال مطابقين لهذا الطلب", "en": "No matching workers found for this request"},
    "select_customer": {"ar": "اختر العميل", "en": "Select Customer"},
    "worker_name": {"ar": "اسم العامل", "en": "Worker Name"},
    "worker_nationality": {"ar": "الجنسية", "en": "Nationality"},
    "worker_gender": {"ar": "الجنس", "en": "Gender"},
    "worker_job": {"ar": "الوظيفة", "en": "Job"},
    "worker_city": {"ar": "المدينة", "en": "City"},
    "worker_phone": {"ar": "رقم الهاتف", "en": "Phone"},
    "worker_age": {"ar": "العمر", "en": "Age"},
    "match_score": {"ar": "نسبة التطابق", "en": "Match Score"},
    "hide_client": {"ar": "إخفاء هذا العميل", "en": "Hide this client"},
    "total_matches": {"ar": "إجمالي النتائج", "en": "Total Matches"},
    "transfer_days_after": {"ar": "نقل الكفالة بعد (يوم)", "en": "Transfer Days After"},
    "working_hours": {"ar": "ساعات العمل", "en": "Working Hours"},
    "weekly_holiday": {"ar": "هل توجد إجازة أسبوعية؟", "en": "Is there a weekly day off?"},
    "additional_notes": {"ar": "ملاحظات إضافية", "en": "Additional Notes"},
    
    # User Roles & Confirmation
    "role_admin": {"ar": "مدير (Admin)", "en": "Admin"},
    "role_viewer": {"ar": "مشاهد (Viewer)", "en": "Viewer"},
    "confirm_delete_user": {"ar": "هل أنت متأكد من حذف هذا المستخدم؟", "en": "Are you sure you want to delete this user?"},
    "cannot_delete_admin": {"ar": "لا يمكن حذف حساب المدير الرئيسي", "en": "Cannot delete primary admin account"},
    "password_changed": {"ar": "تم تغيير كلمة المرور بنجاح", "en": "Password changed successfully"},
    "user_deleted": {"ar": "تم الحذف", "en": "User deleted successfully"},
    "select_user_edit": {"ar": "الرجاء اختيار مستخدم من القائمة للتعديل", "en": "Please select a user from the list to edit"},
    "transfer_all": {"ar": "الكل", "en": "All"},
    "transfer_1": {"ar": "1", "en": "1"},
    "transfer_2": {"ar": "2", "en": "2"},
    "transfer_3": {"ar": "3", "en": "3"},
    "transfer_more": {"ar": "4+", "en": "4+"},
    "transfer_count_label": {"ar": "عدد نقل الكفالة", "en": "Transfer Count"},
    "filter_dates_group": {"ar": "جدولة وتواريخ", "en": "Dates & Scheduling"},
    "filter_advanced_group": {"ar": "تصفية ذكية متقدمة", "en": "Advanced Smart Filters"},
    "age": {"ar": "العمر", "en": "age"},
    "contract_end": {"ar": "تاريخ انتهاء العقد", "en": "contract expiry date"},
    "registration_date": {"ar": "تاريخ التسجيل", "en": "registration date"},
    "no_huroob": {"ar": "بدون بلاغ هروب (No)", "en": "No Huroob (No)"},
    "yes_huroob_label": {"ar": "لديك بلاغ هروب (Yes)", "en": "Has Huroob (Yes)"},
    "not_working_no": {"ar": "No (هل يعمل حالياً؟)", "en": "No (Working Now?)"},
    "sponsor_transfer_yes": {"ar": "يقبل الكفيل النقل (Yes)", "en": "Sponsor Accepts Transfer (Yes)"},
    "expired_filter": {"ar": "العقود المنتهية", "en": "Expired Contracts"},
    "work_outside_city": {"ar": "يقبل العمل خارج مدينته (Yes)", "en": "Can work outside city (Yes)"},
    "domestic_worker_filter": {"ar": "عاملة منزلية", "en": "Domestic Worker"},
    # --- New Advanced Smart Filters (Ready to Work / Iqama Valid / Experience) ---
    "ready_to_work_filter": {"ar": "جاهز للعمل فوراً", "en": "Ready to Work Immediately"},
    "iqama_valid_filter": {"ar": "هل الإقامة سارية؟", "en": "Is Iqama Valid?"},
    "experience_field_filter": {"ar": "الخبرة في هذا المجال (بالسنوات)", "en": "Experience in this field (years)"},
    "filter_option_all": {"ar": "— الكل —", "en": "— All —"},
    "filter_option_yes": {"ar": "نعم (Yes)", "en": "Yes (نعم)"},
    "filter_option_no": {"ar": "لا (No)", "en": "No (لا)"},
    "country_label": {"ar": "دولة", "en": "country"},
    
    # Bengali Supply Module
    # Bengali Supply Module
    "bengali_supply_title": {"ar": "توريد عمال بنقال", "en": "Bengali Worker Supply"},
    "form_supplier_employer": {"ar": "النموذج الأول: بيانات المورد وصاحب العمل", "en": "Part 1: Supplier & Employer Data"},
    "form_worker_details": {"ar": "النموذج الثاني: بيانات العامل المختارة", "en": "Part 2: Worker Details Entry"},
    "supplier_name": {"ar": "اسم المورد", "en": "Supplier Name"},
    "supplier_phone": {"ar": "رقم هاتف المورد", "en": "Supplier Phone"},
    "employer_name": {"ar": "اسم صاحب العمل", "en": "Employer Name"},
    "cafe_name": {"ar": "اسم الكوفي", "en": "Coffee Shop Name"},
    "employer_mobile": {"ar": "رقم موبايل صاحب العمل", "en": "Employer Mobile"},
    "city": {"ar": "المدينة", "en": "City"},
    "worker_passport_iqama": {"ar": "رقم الباسبورد / الإقامة", "en": "Passport / Iqama Number"},
    "upload_multiple_imgs": {"ar": "ارفق صور متعددة", "en": "Attach Multiple Images"},
    "notes_files": {"ar": "ملاحظات الصور/الملفات", "en": "File Notes"},
    "general_notes": {"ar": "ملاحظات عامة", "en": "General Notes"},
    "save_success": {"ar": "تم الحفظ بنجاح!", "en": "Saved successfully!"},
    "save_error": {"ar": "حدث خطأ أثناء الحفظ", "en": "An error occurred during save"},
    "add_supplier_btn": {"ar": "إضافة مورد/صاحب عمل", "en": "Add Supplier/Employer"},
    "add_worker_btn": {"ar": "إضافة بيانات العامل", "en": "Add Worker Data"},
    "select_supplier": {"ar": "اختر المورد", "en": "Select Supplier"},
    "select_employer": {"ar": "اختر صاحب العمل", "en": "Select Employer"},
    "perm_bengali_supply": {"ar": "صلاحية نموذج توريد عمال بنقال", "en": "Bengali Supply Permission"},
    "perm_delete_global": {"ar": "صلاحية الحذف على مستوى البرنامج", "en": "Global Delete Permission"},
    "search_manage_title": {"ar": "🔍 البحث وإدارة السجلات", "en": "Search & Manage Records"},
    "delete_btn": {"ar": "حذف", "en": "Delete"},
    "search_placeholder_bengali": {"ar": "ابحث باسم العامل، المورد، أو العميل...", "en": "Search by worker, supplier, or employer name..."},
    "no_records_found": {"ar": "لم يتم العثور على سجلات", "en": "No records found"},

    # WhatsApp Luxury 2026
    "wa_title": {"ar": "جناح واتساب الفاخر 2026", "en": "WhatsApp Luxury Suite 2026"},
    "wa_subtitle": {"ar": "محرك الرسائل التنفيذي • آمن • مؤتمت", "en": "Executive Messaging Engine • Secure • Automated"},
    "wa_status_lbl": {"ar": "📡 الحالة", "en": "📡 Status"},
    "wa_stats_lbl": {"ar": "📊 إحصائيات الجلسة", "en": "📊 Session Statistics"},
    "wa_step1_lbl": {"ar": "📝 الخطوة 1: إدارة المستلمين", "en": "📝 Step 1: Manage Recipients"},
    "wa_step2_lbl": {"ar": "✉️ الخطوة 2: إنشاء الرسالة", "en": "✉️ Step 2: Compose Message"},
    "wa_step3_lbl": {"ar": "🚀 الخطوة 3: بدء الإرسال", "en": "🚀 Step 3: Deployment"},
    "wa_online": {"ar": "● متصل", "en": "● ONLINE"},
    "wa_offline": {"ar": "● غير متصل", "en": "● OFFLINE"},
    "wa_ready": {"ar": "● جاهز للمسح", "en": "● QR READY"},
    "wa_loading": {"ar": "● جاري التحميل...", "en": "● LOADING..."},
    "wa_launch_btn": {"ar": "تشغيل واتساب ويب", "en": "Launch WhatsApp Web"},
    "wa_refresh_qr": {"ar": "تحديث الرمز", "en": "Refresh QR"},
    "wa_disconnect": {"ar": "قطع الاتصال", "en": "Disconnect"},
    "wa_input_method": {"ar": "طريقة الإدخال", "en": "Input Method"},
    "wa_paste_opt": {"ar": "لصق نص / أرقام", "en": "Paste Text / Numbers"},
    "wa_upload_opt": {"ar": "رفع ملف (Excel/TXT)", "en": "Upload File (Excel/TXT)"},
    "wa_msg_body": {"ar": "نص الرسالة", "en": "Message Body"},
    "wa_delay_lbl": {"ar": "التأخير بين الرسائل (ثواني)", "en": "Delay between messages (Seconds)"},
    "wa_start_btn": {"ar": "🔥 بدء البث الذكي", "en": "🔥 START LUXURY BROADCAST"},
    "wa_stop_btn": {"ar": "⏹️ إيقاف البث", "en": "⏹️ STOP BROADCAST"},
    "wa_total_sent": {"ar": "إجمالي المرسل", "en": "Total Sent"},
    "wa_pending": {"ar": "المتبقي", "en": "Pending"},
    "wa_saudi": {"ar": "🇸🇦 السعودية", "en": "🇸🇦 Saudi"},
    "wa_philippines": {"ar": "🇵🇭 الفلبين", "en": "🇵🇭 Philippines"},
    "wa_invalid": {"ar": "❌ غير صالح", "en": "❌ Invalid"},
    "wa_show_cleaned": {"ar": "عرض الأرقام المنظفة", "en": "Show cleaned numbers"},
    "wa_export_report": {"ar": "تصدير التقرير (CSV)", "en": "Export Report (CSV)"},
    "wa_scan_msg": {"ar": "امسح الكود باستخدام الواتساب في جوالك", "en": "Scan with WhatsApp on your phone"},
    "wa_templates_title": {"ar": "📁 مكتبة القوالب", "en": "📁 Templates Library"},
    "wa_save_as_template": {"ar": "💾 حفظ كقالب جديد", "en": "💾 Save as New Template"},
    "wa_template_name": {"ar": "اسم القالب", "en": "Template Name"},
    "wa_manage_templates": {"ar": "⚙️ إدارة القوالب", "en": "⚙️ Manage Templates"},
    "wa_use_template": {"ar": "📥 استخدام هذا القالب", "en": "📥 Use this template"},
    "wa_delete_template": {"ar": "🗑️ حذف القالب", "en": "🗑️ Delete Template"},
    "wa_placeholders_guide": {"ar": "💡 يمكنك استخدام: {Name} للاسم، {CV} للسيرة، {Phone} للجوال، أو أي اسم عمود من ملف الإكسل بين أقواس {}.", "en": "💡 Use: {Name} for name, {CV} for CV, {Phone} for mobile, or any column name from Excel inside {} brackets."},


    "bengali_supply_title": {"ar": "نظام توريد العمالة البنغالية", "en": "Bengali Labor Supply System"},
    "form_supplier_employer": {"ar": "إضافة مورد وصاحب عمل", "en": "Add Supplier & Employer"},
    "form_worker_details": {"ar": "بيانات العامل / العدد", "en": "Worker Details / Count"},
    "search_manage_title": {"ar": "البحث والإدارة", "en": "Search & Manage"},
    "entry_method": {"ar": "طريقة الإدخال", "en": "Entry Method"},
    "by_details": {"ar": "بالبيانات (الاسم/الجواز)", "en": "By Details (Name/ID)"},
    "by_count": {"ar": "بالعدد الإجمالي (توريد كمية)", "en": "By Quantity (Batch Supply)"},
    "worker_count": {"ar": "عدد العمال", "en": "Number of Workers"},
    "select_supplier": {"ar": "اختر المورد", "en": "Select Supplier"},
    "select_employer": {"ar": "اختر صاحب العمل", "en": "Select Employer"},
    "supplier_name": {"ar": "اسم المورد", "en": "Supplier Name"},
    "supplier_phone": {"ar": "رقم هاتف المورد", "en": "Supplier Phone"},
    "add_supplier_btn": {"ar": "إضافة", "en": "Add"},
    "worker_name": {"ar": "اسم العامل", "en": "Worker Name"},
    "worker_phone": {"ar": "جوال العامل", "en": "Worker Mobile"},
    "worker_passport_iqama": {"ar": "رقم الهوية / الجواز", "en": "ID / Passport"},
    "upload_multiple_imgs": {"ar": "رفع ملفات (صور/PDF)", "en": "Upload Files (Images/PDF)"},
    "notes_files": {"ar": "ملاحظات المرفقات", "en": "Attachment Notes"},
    "general_notes": {"ar": "ملاحظات عامة", "en": "General Notes"},
    "add_worker_btn": {"ar": "إضافة البيانات / العدد", "en": "Add Data / Quantity"},
    "save_success": {"ar": "تم الحفظ بنجاح ✅", "en": "Saved Successfully ✅"},
    "edit_worker_title": {"ar": "تعديل بيانات العامل / العدد", "en": "Edit Worker / Count Details"},

    "employer_name": {"ar": "اسم صاحب العمل", "en": "Employer Name"},
    "employer_mobile": {"ar": "جوال صاحب العمل", "en": "Employer Mobile"},
    "cafe_name": {"ar": "اسم المقهى/المحل", "en": "Cafe/Shop Name"},
    "city": {"ar": "المدينة", "en": "City"},
    "workers_tab": {"ar": "إدارة العمال", "en": "Manage Workers"},
    "suppliers_tab": {"ar": "إدارة الموردين", "en": "Manage Suppliers"},
    "employers_tab": {"ar": "إدارة أصحاب العمل", "en": "Manage Employers"},
    "details_label": {"ar": "عرض التفاصيل", "en": "View Details"},

    "edit_btn": {"ar": "تعديل", "en": "Edit"},
    "return_btn": {"ar": "مرتجع", "en": "Return"},
    "delete_btn_sm": {"ar": "حذف", "en": "Delete"},

    "save_btn": {"ar": "حفظ", "en": "Save"},
    "insertion_date": {"ar": "تاريخ الإدخال", "en": "Insertion Date"},
    "day_label": {"ar": "اليوم", "en": "Day"},
    "days_passed_label": {"ar": "منذ (أيام)", "en": "Days Passed"},
    "today_label": {"ar": "اليوم", "en": "Today"},

    "columns": {
        "__sheet_row": {"ar": "معرف الصف", "en": "Row ID"},
        "طابع زمني": {"ar": "وقت التسجيل", "en": "Timestamp"},
        "Full Name:": {"ar": "الاسم الكامل", "en": "Full Name"},
        "Nationality": {"ar": "الجنسية", "en": "Nationality"},
        "Gender": {"ar": "الجنس", "en": "Gender"},
        "Phone Number": {"ar": "رقم الهاتف", "en": "Phone Number"},
        "Is your contract expired": {"ar": "هل العقد منتهي؟", "en": "Is your contract expired?"},
        "When is your contract end date?": {"ar": "تاريخ انتهاء العقد", "en": "Contract End Date"},
        "Experience in this field": {"ar": "الخبرة في هذا المجال", "en": "Experience in this field"},
        "الخبرة في هذا المجال ↓": {"ar": "الخبرة في هذا المجال", "en": "Experience in this field"},
        "الخبرة في هذا المجال": {"ar": "الخبرة في هذا المجال", "en": "Experience in this field"},
        "Experience (Other)": {"ar": "الخبرة (أخرى)", "en": "Experience (Other)"},
        "الخبرة (أخرى)": {"ar": "الخبرة (أخرى)", "en": "Experience (Other)"},
        "your Age:": {"ar": "العمر", "en": "Age"},
        "Are you working now?": {"ar": "هل تعمل حالياً؟", "en": "Are you working now?"},
        "Do you have any financial obligations towards your previous sponsor": {"ar": "هل لديك التزامات مالية للكفيل السابق؟", "en": "Financial Obligations"},
        "Do you have to report Huroob": {"ar": "هل لديك بلاغ هروب؟", "en": "Huroob Report"},
        "If you are Huroob, how many days or months have you been Huroob?": {"ar": "مدة الهروب", "en": "Huroob Duration"},
        "Will your employer accept to transfer your sponsorship": {"ar": "هل يقبل الكفيل النقل؟", "en": "Sponsorship Transfer"},
        "Are you in Saudi Arabia now": {"ar": "هل أنت في السعودية؟", "en": "In KSA?"},
        "Which city in Saudi Arabia are you in": {"ar": "المدينة", "en": "City"},
        "What is the name of the area where you live?": {"ar": "المنطقة/الحي", "en": "Area"},
        "Do you speak Arabic": {"ar": "هل تتحدث العربية؟", "en": "Speaks Arabic"},
        "Which job are you looking for": {"ar": "الوظيفة المطلوبة", "en": "Job Requested"},
        "How much experience do you have in this field?": {"ar": "الخبرة في هذا المجال", "en": "Experience"},
        "What other jobs can you do": {"ar": "مهارات أخرى", "en": "Other Skills"},
        "How much experience do you have in this field?_1": {"ar": "الخبرة (أخرى)", "en": "Experience (Other)"},
        "Do you have Card Baladiya": {"ar": "هل لديك كرت بلدية؟", "en": "Baladiya Card"},
        "Is the Card Baladiya  valid?": {"ar": "هل الكرت ساري؟", "en": "Card Valid?"},
        "how many months Card Baladiya valid": {"ar": "مدة صلاحية الكرت (أشهر)", "en": "Card Validity (Months)"},
        "how many months Card Baladiya expires": {"ar": "متى ينتهي الكرت (أشهر)", "en": "Card Expiry (Months)"},
        "Can you work outside your city": {"ar": "هل يمكنك العمل خارج مدينتك؟", "en": "Work Outside City"},
        "Are you ready to work immediately?": {"ar": "هل أنت جاهز للعمل فوراً؟", "en": "Ready Immediately"},
        "Are you married and do your children reside with you in Saudi Arabia?": {"ar": "الحالة الاجتماعية وهل العائلة معك؟", "en": "Marital Status & Family"},
        "Iqama ID number": {"ar": "رقم الإقامة", "en": "Iqama ID"},
        "What is the occupation listed on your Iqama": {"ar": "المهنة في الإقامة", "en": "Iqama Profession"},
        "your Iqama Valid": {"ar": "هل الإقامة سارية؟", "en": "Iqama Valid"},
        "If the Iqama is valid, how many months are left?": {"ar": "المدة المتبقية في الإقامة", "en": "Iqama Remaining"},
        "If the Iqama expired how many months ago?": {"ar": "مدة انتهاء الإقامة", "en": "Iqama Expired Since"},
        "How many times did you transfer your sponsorship": {"ar": "عدد مرات نقل الكفالة", "en": "Transfer Count"},
        "Download CV": {"ar": "تحميل السيرة الذاتية", "en": "Download CV"},
        "How did you know us?": {"ar": "كيف عرفت عنا؟", "en": "How did you know us?"},
        "__sheet_row_backup": {"ar": "نسخة المعرف", "en": "ID Backup"},
        "Remaining": {"ar": "المتبقى", "en": "Remaining"},
        "Status": {"ar": "الحالة (STATUS)", "en": "Status"},
        "Company or institution name | الشركة أو المؤسسة": {"ar": "اسم المنشأة / الشركة", "en": "Company Name"},
        "Responsible Name | اسم المسؤول": {"ar": "اسم المسؤول", "en": "Responsible Person"},
        "Mobile number | رقم الموبايل": {"ar": "رقم الجوال", "en": "Mobile Number"},
        "Specify the required category | ذكر الفئة المطلوبة": {"ar": "الفئة المطلوبة", "en": "Required Category"},
        "Required nationality | جنسية المطلوبة": {"ar": "الجنسية المطلوبة", "en": "Required Nationality"},
        "Required nationality | PH الجنسية المطلوبة": {"ar": "الجنسية المطلوبة", "en": "Required Nationality"},
        "Work location | موقع العمل": {"ar": "موقع العمل", "en": "Work Location"},
        "Nature of the worker's work | طبيعة عمل العامل": {"ar": "طبيعة العمل", "en": "Work Nature"},
        "Number of employees required | عدد الموظفين المطلوب": {"ar": "عدد الموظفين", "en": "Number of Employees"},
        "Transfer of sponsorship after how many days | نقل الكفالة بعد كم يوم": {"ar": "نقل الكفالة بعد (يوم)", "en": "Transfer Days After"},
        "Expected salary | الراتب المتوقع": {"ar": "الراتب المتوقع", "en": "Expected Salary"},
        "Working hours per day | عدد ساعات العمل": {"ar": "ساعات العمل", "en": "Working Hours"},
        "Is there a weekly day off | هل توجد إجازة أسبوعية؟": {"ar": "إجازة أسبوعية", "en": "Weekly Holiday"},
        "Additional notes (optional) | ملاحظات إضافية": {"ar": "ملاحظات إضافية", "en": "Additional Notes"},
        "العامل نقل الكفالة بعد كم يوم": {"ar": "نقل الكفالة بعد (يوم)", "en": "Transfer Days After"},
        "عدد ساعات العمل": {"ar": "ساعات العمل", "en": "Working Hours"},
        "هل توجد اجازة اسبوعي": {"ar": "إجازة أسبوعية", "en": "Weekly Holiday"},
        "ملاحظات اضافيه": {"ar": "ملاحظات إضافية", "en": "Additional Notes"},
        
        # Additional common column translations
        "Do you speak Arabic?": {"ar": "هل تتحدث العربية؟", "en": "Speaks Arabic"},
        "Do you speak Arabic": {"ar": "هل تتحدث العربية؟", "en": "Speaks Arabic"},
        "speaks arabic": {"ar": "هل تتحدث العربية؟", "en": "Speaks Arabic"},
        "Which job are you looking for?": {"ar": "الوظيفة المطلوبة", "en": "Job Requested"},
        "Which job are you looking for": {"ar": "الوظيفة المطلوبة", "en": "Job Requested"},
        "What other jobs can you do": {"ar": "مهارات أخرى", "en": "Other Skills"},
        "What other jobs can you do?": {"ar": "مهارات أخرى", "en": "Other Skills"},
        "What is the occupation listed on your Iqama": {"ar": "المهنة في الإقامة", "en": "Iqama Profession"},
        "What is the occupation listed on your Iqama?": {"ar": "المهنة في الإقامة", "en": "Iqama Profession"},
        "your Iqama Valid": {"ar": "هل الإقامة سارية؟", "en": "Iqama Valid"},
        "your Iqama Valid?": {"ar": "هل الإقامة سارية؟", "en": "Iqama Valid"},
        "If the Iqama is valid, how many months are left?": {"ar": "المدة المتبقية في الإقامة", "en": "Iqama Remaining"},
        "If the Iqama expired how many months ago?": {"ar": "مدة انتهاء الإقامة", "en": "Iqama Expired Since"},
        "How many times did you transfer your sponsorship": {"ar": "عدد مرات نقل الكفالة", "en": "Transfer Count"},
        "How many times did you transfer your sponsorship?": {"ar": "عدد مرات نقل الكفالة", "en": "Transfer Count"},
        "Are you ready to work immediately": {"ar": "هل أنت جاهز للعمل فوراً؟", "en": "Ready Immediately"},
        "Are you ready to work immediately?": {"ar": "هل أنت جاهز للعمل فوراً؟", "en": "Ready Immediately"},
        "ready to work immediately": {"ar": "جاهز للعمل فوراً", "en": "Ready Immediately"},
        "Can you work outside your city": {"ar": "هل يمكنك العمل خارج مدينتك؟", "en": "Work Outside City"},
        "Can you work outside your city?": {"ar": "هل يمكنك العمل خارج مدينتك؟", "en": "Work Outside City"},
        "Do you have Card Baladiya": {"ar": "هل لديك كرت بلدية؟", "en": "Baladiya Card"},
        "Do you have Card Baladiya?": {"ar": "هل لديك كرت بلدية؟", "en": "Baladiya Card"},
        "Is the Card Baladiya valid": {"ar": "هل الكرت ساري؟", "en": "Card Valid"},
        "Is the Card Baladiya valid?": {"ar": "هل الكرت ساري؟", "en": "Card Valid"},
        "how many months Card Baladiya valid": {"ar": "مدة صلاحية الكرت (أشهر)", "en": "Card Validity (Months)"},
        "how many months Card Baladiya expires": {"ar": "متى ينتهي الكرت (أشهر)", "en": "Card Expiry (Months)"},
        "Do you have to report Huroob": {"ar": "هل لديك بلاغ هروب؟", "en": "Huroob Report"},
        "Do you have to report Huroob?": {"ar": "هل لديك بلاغ هروب؟", "en": "Huroob Report"},
        "Will your employer accept to transfer your sponsorship": {"ar": "هل يقبل الكفيل النقل؟", "en": "Sponsorship Transfer"},
        "Will your employer accept to transfer your sponsorship?": {"ar": "هل يقبل الكفيل النقل؟", "en": "Sponsorship Transfer"},
        "Do you have any financial obligations towards your previous sponsor": {"ar": "هل لديك التزامات مالية للكفيل السابق؟", "en": "Financial Obligations"},
        "Do you have any financial obligations towards your previous sponsor?": {"ar": "هل لديك التزامات مالية للكفيل السابق؟", "en": "Financial Obligations"},
        "Are you married and do your children reside with you in Saudi Arabia": {"ar": "الحالة الاجتماعية وهل العائلة معك؟", "en": "Marital Status & Family"},
        "Are you married and do your children reside with you in Saudi Arabia?": {"ar": "الحالة الاجتماعية وهل العائلة معك؟", "en": "Marital Status & Family"},
        "Iqama ID number": {"ar": "رقم الإقامة", "en": "Iqama ID"},
        "Iqama ID number": {"ar": "رقم الإقامة", "en": "Iqama ID"},
        "Age": {"ar": "العمر", "en": "Age"},
        "your Age": {"ar": "العمر", "en": "Age"},
        "Are you working now": {"ar": "هل تعمل حالياً؟", "en": "Are you working now?"},
        "Are you working now?": {"ar": "هل تعمل حالياً؟", "en": "Are you working now?"},
        "Experience in this field": {"ar": "الخبرة في هذا المجال", "en": "Experience in this field"},
        "Experience in this field": {"ar": "الخبرة في هذا المجال", "en": "Experience in this field"},
        "How much experience do you have in this field": {"ar": "الخبرة في هذا المجال", "en": "Experience"},
        "How much experience do you have in this field?": {"ar": "الخبرة في هذا المجال", "en": "Experience"},
        "Experience (Other)": {"ar": "الخبرة (أخرى)", "en": "Experience (Other)"},
        "How much experience do you have in this field?_1": {"ar": "الخبرة (أخرى)", "en": "Experience (Other)"},
        "How much experience do you have in this field?_1": {"ar": "الخبرة (أخرى)", "en": "Experience (Other)"},
        "Is your contract expired": {"ar": "هل العقد منتهي؟", "en": "Is your contract expired?"},
        "Is your contract expired?": {"ar": "هل العقد منتهي؟", "en": "Is your contract expired?"},
        "When is your contract end date": {"ar": "تاريخ انتهاء العقد", "en": "Contract End Date"},
        "When is your contract end date?": {"ar": "تاريخ انتهاء العقد", "en": "Contract End Date"},
        "Are you in Saudi Arabia now": {"ar": "هل أنت في السعودية؟", "en": "In KSA?"},
        "Are you in Saudi Arabia now": {"ar": "هل أنت في السعودية؟", "en": "In KSA?"},
        "Which city in Saudi Arabia are you in": {"ar": "المدينة", "en": "City"},
        "Which city in Saudi Arabia are you in": {"ar": "المدينة", "en": "City"},
        "What is the name of the area where you live": {"ar": "المنطقة/الحي", "en": "Area"},
        "What is the name of the area where you live": {"ar": "المنطقة/الحي", "en": "Area"},
        "If you are Huroob, how many days or months have you been Huroob": {"ar": "مدة الهروب", "en": "Huroob Duration"},
        "If you are Huroob, how many days or months have you been Huroob": {"ar": "مدة الهروب", "en": "Huroob Duration"},
    }
}

# Value translations for data values (not column names)
VALUE_TRANSLATIONS = {
    # Yes/No - Common values
    "yes": {"ar": "نعم", "en": "Yes"},
    "no": {"ar": "لا", "en": "No"},
    "true": {"ar": "نعم", "en": "True"},
    "false": {"ar": "لا", "en": "False"},
    "y": {"ar": "نعم", "en": "Y"},
    "n": {"ar": "لا", "en": "N"},
    
    # Gender
    "male": {"ar": "ذكر", "en": "Male"},
    "female": {"ar": "أنثى", "en": "Female"},
    "m": {"ar": "ذكر", "en": "M"},
    "f": {"ar": "أنثى", "en": "F"},
    
    # Status/State
    "active": {"ar": "ساري", "en": "Active"},
    "expired": {"ar": "منتهي", "en": "Expired"},
    "valid": {"ar": "ساري", "en": "Valid"},
    "invalid": {"ar": "غير ساري", "en": "Invalid"},
    "urgent": {"ar": "عاجل", "en": "Urgent"},
    "pending": {"ar": "قيد الانتظار", "en": "Pending"},
    "completed": {"ar": "مكتمل", "en": "Completed"},
    "approved": {"ar": "موافق عليه", "en": "Approved"},
    "rejected": {"ar": "مرفوض", "en": "Rejected"},
    "available": {"ar": "متاح", "en": "Available"},
    "unavailable": {"ar": "غير متاح", "en": "Unavailable"},
    "ready": {"ar": "جاهز", "en": "Ready"},
    "not ready": {"ar": "غير جاهز", "en": "Not Ready"},
    
    # Common Arabic responses
    "نعم": {"ar": "نعم", "en": "Yes"},
    "لا": {"ar": "لا", "en": "No"},
    "ساري": {"ar": "ساري", "en": "Valid"},
    "منتهي": {"ar": "منتهي", "en": "Expired"},
    "عاجل": {"ar": "عاجل", "en": "Urgent"},
    
    # Marital status
    "single": {"ar": "أعزب/عزباء", "en": "Single"},
    "married": {"ar": "متزوج", "en": "Married"},
    "divorced": {"ar": "مطلق", "en": "Divorced"},
    "widowed": {"ar": "أرمل", "en": "Widowed"},
    "separated": {"ar": "منفصل", "en": "Separated"},
    
    # Religion
    "muslim": {"ar": "مسلم", "en": "Muslim"},
    "christian": {"ar": "مسيحي", "en": "Christian"},
    "hindu": {"ar": "هندوسي", "en": "Hindu"},
    "buddhist": {"ar": "بوذي", "en": "Buddhist"},
    "catholic": {"ar": "كاثوليكي", "en": "Catholic"},
    "protestant": {"ar": "بروتستانتي", "en": "Protestant"},
    "other": {"ar": "أخرى", "en": "Other"},
    
    # Working status
    "working": {"ar": "يعمل", "en": "Working"},
    "not working": {"ar": "لا يعمل", "en": "Not Working"},
    "currently working": {"ar": "يعمل حالياً", "en": "Currently Working"},
    "not currently working": {"ar": "لا يعمل حالياً", "en": "Not Currently Working"},
    "unemployed": {"ar": "عاطل", "en": "Unemployed"},
    "employed": {"ar": "موظف", "en": "Employed"},
    
    # Iqama status
    "iqama valid": {"ar": "الإقامة سارية", "en": "Iqama Valid"},
    "iqama expired": {"ar": "الإقامة منتهية", "en": "Iqama Expired"},
    "valid iqama": {"ar": "إقامة سارية", "en": "Valid Iqama"},
    "expired iqama": {"ar": "إقامة منتهية", "en": "Expired Iqama"},
    
    # Contract status
    "contract active": {"ar": "العقد ساري", "en": "Contract Active"},
    "contract expired": {"ar": "العقد منتهي", "en": "Contract Expired"},
    "contract not expired": {"ar": "العقد غير منتهي", "en": "Contract Not Expired"},
    
    # Transfer status
    "transfer accept": {"ar": "يقبل النقل", "en": "Accept Transfer"},
    "accept transfer": {"ar": "يقبل النقل", "en": "Accept Transfer"},
    "transfer not accept": {"ar": "لا يقبل النقل", "en": "Not Accept Transfer"},
    "sponsor accept": {"ar": "الكفيل يقبل", "en": "Sponsor Accepts"},
    "sponsor not accept": {"ar": "الكفيل لا يقبل", "en": "Sponsor Not Accept"},
    "first time": {"ar": "المرة الأولى", "en": "First Time"},
    "second time": {"ar": "المرة الثانية", "en": "Second Time"},
    "third time": {"ar": "المرة الثالثة", "en": "Third Time"},
    "more than 3": {"ar": "أكثر من 3", "en": "More Than 3"},
    
    # Work location
    "inside city": {"ar": "داخل المدينة", "en": "Inside City"},
    "outside city": {"ar": "خارج المدينة", "en": "Outside City"},
    "can work outside": {"ar": "يمكن العمل خارج", "en": "Can Work Outside"},
    "cannot work outside": {"ar": "لا يمكن العمل خارج", "en": "Cannot Work Outside"},
    
    # Obligations
    "financial obligations": {"ar": "التزامات مالية", "en": "Financial Obligations"},
    "has obligations": {"ar": "له التزامات", "en": "Has Obligations"},
    "no obligations": {"ar": "لا توجد التزامات", "en": "No Obligations"},
    
    # Huroob status
    "huroob": {"ar": "هروب", "en": "Huroob"},
    "has huroob": {"ar": "يوجد بلاغ هروب", "en": "Has Huroob"},
    "no huroob": {"ar": "لا يوجد بلاغ هروب", "en": "No Huroob"},
    
    # Common time-related
    "immediately": {"ar": "فوراً", "en": "Immediately"},
    "as soon as possible": {"ar": "في أسرع وقت", "en": "As Soon As Possible"},
    "within 1 week": {"ar": "خلال أسبوع", "en": "Within 1 Week"},
    "within 2 weeks": {"ar": "خلال أسبوعين", "en": "Within 2 Weeks"},
    "within 1 month": {"ar": "خلال شهر", "en": "Within 1 Month"},
    
    # Education level
    "high school": {"ar": "ثانوية عامة", "en": "High School"},
    "college": {"ar": "كلية", "en": "College"},
    "university": {"ar": "جامعة", "en": "University"},
    "bachelor": {"ar": "بكالوريوس", "en": "Bachelor"},
    "master": {"ar": "ماجستير", "en": "Master"},
    "phd": {"ar": "دكتوراه", "en": "PhD"},
    "diploma": {"ar": "دبلوم", "en": "Diploma"},
    "vocational": {"ar": "مهني", "en": "Vocational"},
    "elementary": {"ar": "ابتدائية", "en": "Elementary"},
    "primary": {"ar": "ابتدائية", "en": "Primary"},
    "secondary": {"ar": "ثانوية", "en": "Secondary"},
    
    # Common skills
    "cooking": {"ar": "طبخ", "en": "Cooking"},
    "cleaning": {"ar": "تنظيف", "en": "Cleaning"},
    "washing": {"ar": "غسيل", "en": "Washing"},
    "ironing": {"ar": "كي", "en": "Ironing"},
    "childcare": {"ar": "رعاية الأطفال", "en": "Childcare"},
    "elderly care": {"ar": "رعاية المسنين", "en": "Elderly Care"},
    "driving": {"ar": "قيادة", "en": "Driving"},
    "sewing": {"ar": "خياطة", "en": "Sewing"},
    "gardening": {"ar": "بستنة", "en": "Gardening"},
    "english": {"ar": "الإنجليزية", "en": "English"},
    "arabic": {"ar": "العربية", "en": "Arabic"},
    "hindi": {"ar": "الهندية", "en": "Hindi"},
    "tagalog": {"ar": "التغالوغية", "en": "Tagalog"},
    "basic": {"ar": "أساسي", "en": "Basic"},
    "intermediate": {"ar": "متوسط", "en": "Intermediate"},
    "advanced": {"ar": "متقدم", "en": "Advanced"},
    "fluent": {"ar": "طلاقة", "en": "Fluent"},
    "good": {"ar": "جيد", "en": "Good"},
    "fair": {"ar": "مقبول", "en": "Fair"},
    "poor": {"ar": "ضعيف", "en": "Poor"},
    
    # Common jobs/professions
    "driver": {"ar": "سائق", "en": "Driver"},
    "domestic helper": {"ar": "عاملة منزلية", "en": "Domestic Helper"},
    "housemaid": {"ar": "عاملة منزلية", "en": "Housemaid"},
    "nanny": {"ar": "مربية أطفال", "en": "Nanny"},
    "cook": {"ar": "طباخ", "en": "Cook"},
    "cleaner": {"ar": "نظافة", "en": "Cleaner"},
    "gardener": {"ar": "بستاني", "en": "Gardener"},
    "security": {"ar": "أمن", "en": "Security"},
    "electrician": {"ar": "كهربائي", "en": "Electrician"},
    "plumber": {"ar": "سباك", "en": "Plumber"},
    "carpenter": {"ar": "نجار", "en": "Carpenter"},
    "painter": {"ar": "دهان", "en": "Painter"},
    "mechanic": {"ar": "ميكانيكي", "en": "Mechanic"},
    "technician": {"ar": "فني", "en": "Technician"},
    "sales": {"ar": "مبيعات", "en": "Sales"},
    "accountant": {"ar": "محاسب", "en": "Accountant"},
    "receptionist": {"ar": "استقبال", "en": "Receptionist"},
    "waiter": {"ar": "نادل", "en": "Waiter"},
    "barista": {"ar": "باريستا", "en": "Barista"},
    "cashier": {"ar": "كاشير", "en": "Cashier"},
    "assistant": {"ar": "مساعد", "en": "Assistant"},
    "supervisor": {"ar": "مشرف", "en": "Supervisor"},
    "manager": {"ar": "مدير", "en": "Manager"},
    "general worker": {"ar": "عامل عام", "en": "General Worker"},
    "laborer": {"ar": "عامل", "en": "Laborer"},
    "construction": {"ar": "بناء", "en": "Construction"},
    "factory": {"ar": "مصنع", "en": "Factory"},
    "warehouse": {"ar": "مستودع", "en": "Warehouse"},
    
    # Card/baladiya
    "baladiya card": {"ar": "كرت البلدية", "en": "Baladiya Card"},
    "has card": {"ar": "يوجد كرت", "en": "Has Card"},
    "no card": {"ar": "لا يوجد كرت", "en": "No Card"},
    "card valid": {"ar": "الكرت ساري", "en": "Card Valid"},
    "card expired": {"ar": "الكرت منتهي", "en": "Card Expired"},
    
    # Common locations
    "riyadh": {"ar": "الرياض", "en": "Riyadh"},
    "jeddah": {"ar": "جدة", "en": "Jeddah"},
    "dammam": {"ar": "الدمام", "en": "Dammam"},
    "makkah": {"ar": "مكة", "en": "Makkah"},
    "madinah": {"ar": "المدينة", "en": "Madinah"},
    "tabuk": {"ar": "تبوك", "en": "Tabuk"},
    "abha": {"ar": "أبها", "en": "Abha"},
    "khobar": {"ar": "الخبر", "en": "Khobar"},
    
    # Nationalities (expanded)
    "filipino": {"ar": "فلبيني", "en": "Filipino"},
    "filipina": {"ar": "فلبينية", "en": "Filipina"},
    "indian": {"ar": "هندي", "en": "Indian"},
    "indonesian": {"ar": "إندونيسي", "en": "Indonesian"},
    "srilankan": {"ar": "سريلانكي", "en": "Sri Lankan"},
    "bangladeshi": {"ar": "بنغلاديشي", "en": "Bangladeshi"},
    "nepali": {"ar": "نيبالي", "en": "Nepali"},
    "pakistan": {"ar": "باكستاني", "en": "Pakistani"},
    "egyptian": {"ar": "مصري", "en": "Egyptian"},
    "syrian": {"ar": "سوري", "en": "Syrian"},
    "yemeni": {"ar": "يمني", "en": "Yemeni"},
    "sudanese": {"ar": "سوداني", "en": "Sudanese"},
    
    # Time periods
    "1 month": {"ar": "شهر واحد", "en": "1 Month"},
    "2 months": {"ar": "شهران", "en": "2 Months"},
    "3 months": {"ar": "3 أشهر", "en": "3 Months"},
    "6 months": {"ar": "6 أشهر", "en": "6 Months"},
    "1 year": {"ar": "سنة واحدة", "en": "1 Year"},
    "2 years": {"ar": "سنتان", "en": "2 Years"},
    "less than 1 year": {"ar": "أقل من سنة", "en": "Less Than 1 Year"},
    "more than 1 year": {"ar": "أكثر من سنة", "en": "More Than 1 Year"},
    "less than 6 months": {"ar": "أقل من 6 أشهر", "en": "Less Than 6 Months"},
    "more than 6 months": {"ar": "أكثر من 6 أشهر", "en": "More Than 6 Months"},
}

def t(key, lang="ar"):
    return TRANSLATIONS.get(key, {}).get(lang, key)

def t_col(col_name, lang="ar"):
    """Translates a column name using exact lookups from the `columns` dictionary."""
    if lang == 'en': return col_name
    
    col_str = str(col_name).strip()
    
    # 1. Try Exact Match
    res = TRANSLATIONS.get("columns", {}).get(col_str, {}).get("ar")
    if res: return res
    
    # 2. Try Case-Insensitive Match
    cols_map = {k.strip().lower(): v.get("ar") for k, v in TRANSLATIONS.get("columns", {}).items()}
    res_fuzzy = cols_map.get(col_str.lower())
    if res_fuzzy: return res_fuzzy
    
    # 3. Enhanced Partial Matches (Fallback)
    col_lower = col_str.lower()
    
    # Prioritize specific partials causing issues
    if "financial obligations" in col_lower: return "الالتزامات المالية"
    if "card baladiya" in col_lower: return "كرت البلدية"
    if "iqama" in col_lower: return "الإقامة"
    if "experience" in col_lower: return "الخبرة"
    if "huroob" in col_lower: return "الهروب"
    if "contract end" in col_lower: return "تاريخ انتهاء العقد"
    
    return col_name

def _tval_is_excluded_field(field_name):
    """Fields whose values must stay as-is (never machine-translated).

    - Full name stays in English per product requirement.
    - Links, phone numbers and ID numbers are not translatable text.
    """
    if not field_name:
        return False
    fl = str(field_name).lower()
    if any(k in fl for k in ["full name", "الاسم الكامل", "name:", "الاسم:", "worker name", "اسم العامل"]):
        return True
    if any(k in fl for k in ["cv", "سيرة", "link", "رابط", "url", "http", "drive"]):
        return True
    if any(k in fl for k in ["phone", "mobile", "جوال", "هاتف", "موبايل", "whatsapp"]):
        return True
    if any(k in fl for k in ["iqama id", "رقم الإقامة", "passport", "جواز", "id number"]):
        return True
    return False


def _should_ai_translate(val_str, field_name=None):
    """Decide whether an Arabic-UI value needs machine translation EN -> AR."""
    if not val_str:
        return False
    s = str(val_str).strip()
    if len(s) < 3:
        return False
    # Only values containing English letters need translation.
    # Pure Arabic / numbers / dates / phones are returned as-is.
    if not re.search(r'[a-zA-Z]', s):
        return False
    if _tval_is_excluded_field(field_name):
        return False
    low = s.lower()
    if any(e in low for e in _AI_TVAL_ERROR_SIGS):
        return False
    # URLs / emails are not translatable text.
    if s.startswith("http://") or s.startswith("https://") or "drive.google.com" in low:
        return False
    if "@" in s and "." in s and " " not in s:
        return False
    # Pure numbers / phones / dates / symbols.
    if re.match(r'^[\+\d\s\-\(\)\./:,#%*!=@&]+$', s):
        return False
    if not re.search(r'[a-zA-Z\u0600-\u06FF]', s):
        return False
    return True


def _ai_translate_en_to_ar(val_str):
    """Translate an English worker value to natural Arabic (cached).

    Uses the app's multi-engine TranslationService (Google first), so the
    result is a full-sentence natural translation, not word-by-word.
    Returns None on any failure so the caller can fall back to the original.
    """
    s = str(val_str).strip()
    if not s:
        return None
    cache_key = "ai_ar_" + hashlib.md5(s.encode("utf-8")).hexdigest()
    # 1. Streamlit session cache (survives reruns).
    try:
        import streamlit as st
        sess_cache = st.session_state.get("translation_cache", {})
        cached = sess_cache.get(cache_key)
        if cached and not any(e in str(cached).lower() for e in _AI_TVAL_ERROR_SIGS):
            return cached
    except Exception:
        pass
    # 2. Process-level cache.
    if cache_key in _AI_TVAL_CACHE:
        return _AI_TVAL_CACHE[cache_key]
    # 3. Machine translation.
    try:
        from src.core.file_translator import TranslationService
        svc = TranslationService(source_lang="en", target_lang="ar")
        res = svc.translate_text(s)
        if res:
            res = res.strip()
            if res and res.lower() != s.lower() \
                    and not any(e in res.lower() for e in _AI_TVAL_ERROR_SIGS):
                _AI_TVAL_CACHE[cache_key] = res
                try:
                    import streamlit as st
                    if "translation_cache" not in st.session_state:
                        st.session_state.translation_cache = {}
                    st.session_state.translation_cache[cache_key] = res
                except Exception:
                    pass
                return res
    except Exception:
        pass
    return None

def t_val(value, lang="ar", field_name=None):
    """
    Translates a data value to the target language.
    
    Args:
        value: The value to translate
        lang: Target language ('ar' or 'en')
        field_name: Optional field name for context-aware translation
    
    Returns:
        Translated value if translation exists, otherwise original value
    """
    if lang == 'en':
        return value
    
    if value is None:
        return value
    
    # Skip translation for pandas NA
    try:
        import pandas as pd
        if pd.isna(value):
            return value
    except ImportError:
        pass
    
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ["nan", "none", "null", "<na>", "nat"]:
        return value
    
    # Skip translation for full name fields (keep original)
    if field_name:
        field_lower = str(field_name).lower()
        # Don't translate full name fields
        if any(kw in field_lower for kw in ["full name", "الاسم الكامل", "name:", "الاسم:"]):
            return value
        # Don't translate URL fields
        if any(kw in field_lower for kw in ["cv", "سيرة", "link", "رابط", "url", "http"]):
            return value
    
    # Try exact match (case-insensitive)
    val_lower = val_str.lower()
    translation = VALUE_TRANSLATIONS.get(val_lower, {}).get("ar")
    if translation:
        return translation
    
    # Try partial match for values containing known words
    for key, trans in VALUE_TRANSLATIONS.items():
        if key in val_lower and val_lower.replace(key, "").strip() in ["", ",", " ", ".", "/", "-"]:
            # If the value is mostly the known word
            return trans.get("ar", val_str)
    
    # Special handling for field-specific translations
    if field_name:
        field_lower = str(field_name).lower()
        
        # Nationality handling (use existing system if available)
        if "nationality" in field_lower or "جنسية" in field_lower:
            try:
                from src.core.i18n import _get_nationality_code, get_country_display_name
                nat_code = _get_nationality_code(value)
                if nat_code:
                    return get_country_display_name(nat_code, 'ar')
            except Exception:
                pass

    # AI fallback: natural full-sentence translation EN -> AR for any
    # free-text English value the dictionary did not cover.
    # (Full name / links / phones / IDs are excluded in the helper.)
    if lang == "ar" and _should_ai_translate(val_str, field_name):
        ai_result = _ai_translate_en_to_ar(val_str)
        if ai_result:
            return ai_result

    return value
