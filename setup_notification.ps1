# --------- setup_notification.ps1 ---------
# Set Execution Policy for the current process
Set-ExecutionPolicy Bypass -Scope Process -Force

# Use PSScriptRoot for robustness with non-ASCII paths
$ProjectPath = $PSScriptRoot
if (-Not $ProjectPath) { $ProjectPath = Get-Location }

$ScriptFile = Join-Path $ProjectPath "antigravity_notification.py"
$RequirementsFile = Join-Path $ProjectPath "requirements.txt"

Write-Output "Project Path: $ProjectPath"

# -------------------------
# 1️⃣ Install required packages
# -------------------------
$packages = @("gspread", "oauth2client", "pandas", "openpyxl")

foreach ($pkg in $packages) {
    Write-Output "Installing $pkg ..."
    & pip install $pkg
}

# -------------------------
# 2️⃣ Verify script exists
# -------------------------
if (-Not (Test-Path $ScriptFile)) {
    Write-Error "Error: Script $ScriptFile not found."
    exit 1
}

# -------------------------
# 3️⃣ Setup Task Scheduler (User Level)
# -------------------------
$TaskName = "AntigravityNotification"
$PythonPath = (Get-Command python).Source

# Check if task exists and remove it
$existingTask = schtasks /query /tn $TaskName /error 0 2>$null
if ($null -ne $existingTask) {
    schtasks /delete /tn $TaskName /f
}

# Create new task using schtasks.exe (often more reliable for encoding)
# /sc ONLOGON: Run at logon
# /tr: Task run command
# /it: Interactive (needed for toast notifications)
$taskCommand = "`"$PythonPath`" `"$ScriptFile`""
schtasks /create /tn $TaskName /tr "$taskCommand" /sc ONLOGON /it /f

if ($LASTEXITCODE -eq 0) {
    Write-Output "Task created successfully. It will run at next logon."
} else {
    Write-Error "Failed to create task. You might need to run this as Administrator."
}
