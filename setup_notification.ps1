# --------- setup_notification.ps1 ---------
# تجاوز سياسة التنفيذ
Set-ExecutionPolicy Bypass -Scope Process -Force

# تحديد مسار المشروع
$ProjectPath = "c:\Users\ا\Desktop\non2"
$ScriptFile = Join-Path $ProjectPath "antigravity_notification.py"
$RequirementsFile = Join-Path $ProjectPath "requirements.txt"

# -------------------------
# 1️⃣ تثبيت المكتبات المطلوبة
# -------------------------
$packages = @("win10toast","gspread","oauth2client")

# إنشاء requirements.txt إذا لم يكن موجود
if (-Not (Test-Path $RequirementsFile)) {
    New-Item -ItemType File -Path $RequirementsFile -Force
}

foreach ($pkg in $packages) {
    if (-Not (Get-Content $RequirementsFile | Select-String $pkg)) {
        Add-Content $RequirementsFile $pkg
    }
    Write-Output "تثبيت $pkg ..."
    pip install $pkg
}

# -------------------------
# 2️⃣ التأكد من وجود السكربت
# -------------------------
if (-Not (Test-Path $ScriptFile)) {
    Write-Output "تحذير: السكربت $ScriptFile غير موجود. يرجى التأكد من وجوده."
}

# -------------------------
# 3️⃣ إعداد Task Scheduler لتشغيل السكربت عند تسجيل الدخول
# -------------------------
$TaskName = "Antigravity Notification"
$PythonPath = (Get-Command python).Source  # الحصول على المسار الكامل لـ Python

# حذف المهمة إذا كانت موجودة مسبقًا
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# إنشاء مهمة جديدة
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptFile`"" -WorkingDirectory $ProjectPath
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden -ExecutionTimeLimit 0
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings

Write-Output "تم إنشاء Task Scheduler بنجاح. سيعمل البرنامج الآن في الخلفية عند فتح الجهاز."
