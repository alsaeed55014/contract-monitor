@echo off
setlocal enabledelayedexpansion

:: ================================================================
::  سكربت رفع الملفات الآمنة إلى GitHub
::  الملف: upload_to_github.bat
::  المسار: C:\app\upload_to_github.bat
:: ================================================================

title رفع الملفات إلى GitHub - نظام السعيد الوزان
color 0A

echo.
echo ================================================================
echo   بدء عملية رفع الملفات إلى GitHub
echo ================================================================
echo.

:: التحقق من وجود Git
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [خطأ] لم يتم العثور على Git على هذا الجهاز.
    echo   يرجى تثبيت Git من: https://git-scm.com/
    echo.
    pause
    exit /b 1
)

:: الانتقال إلى مجلد البرنامج
cd /d "%~dp0"

:: التحقق من أننا في مجلد Git
if not exist ".git" (
    echo [خطأ] هذا المجلد ليس مستودع Git.
    echo   يرجى تهيئة المجلد أولاً أو clone من GitHub.
    echo.
    pause
    exit /b 1
)

echo [معلومات] تم العثور على Git ومستودع Git الحالي.
echo.

:: عرض حالة الملفات الحالية
echo [معلومات] فحص حالة الملفات...
git status --short

echo.
echo ================================================================
echo   تحذير: تأكد من أن الملفات الحساسة غير مرفوعة:
echo   - users.json (كلمات المرور)
echo   - login_history.json (سجلات الدخول)
echo   - whatsapp_history*.json (سجلات الواتساب)
echo   - credentials.json, service_account.json
echo   - node_modules/, whatsapp_session/, __pycache__/
echo ================================================================
echo.

:: السؤال عن رسالة commit
set /p commit_msg="أدخل رسالةcommit (أو اضغط Enter للاستخدام الافتراضي): "
if "%commit_msg%"=="" set commit_msg="تحديث: تحسين نظام تنظيف السير الذاتية وتتبع الدخول والخروج"

echo.
echo [معلومات] تنظيف الملفات المؤقتة وجلسات الواتساب من التتبع...
git rm -r --cached whatsapp_session node_modules legacy_attendance_php archive_legacy 2>nul

echo [معلومات] إضافة الملفات الآمنة إلى منطقة الاستعداد (Staging)...
git add .

echo.
echo [معلومات] إنشاء Commit...
git commit -m "%commit_msg%"

if %errorlevel% neq 0 (
    echo [تحذير] لم يتم إنشاء Commit (قد لا توجد تغييرات جديدة).
) else (
    echo [نجاح] تم إنشاء Commit بنجاح.
    echo.
    echo [معلومات] رفع التغييرات إلى GitHub...
    git push
    
    if %errorlevel% equ 0 (
        echo.
        echo ================================================================
        echo   [تم بنجاح] تم رفع جميع الملفات إلى GitHub!
        echo ================================================================
    ) else (
        echo.
        echo [خطأ] فشل في الرفع إلى GitHub.
        echo   تأكد من أن لديك صلاحيات الكتابة للمستودع.
        echo   وقد تحتاج إلى إعداد مصادقة (Personal Access Token).
    )
)

echo.
echo اكتمل العملية.
pause
endlocal