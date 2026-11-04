@echo off
echo ==================================================
echo   🚀 Pasha Final Sync - Simple Mode
echo ==================================================
echo.

set REPO_URL=https://github.com/alsaeed55014/contract-monitor.git

:: Connect
echo [1/3] Connecting to GitHub...
git remote remove origin >nul 2>nul
git remote add origin %REPO_URL%

:: Detect Branch
for /f "tokens=*" %%i in ('git branch --show-current') do set branch=%%i
if "%branch%"=="" set branch=master

:: Add & Commit
echo [2/3] Saving local updates...
git add .
git commit -m "Comprehensive Update - logic and security"

:: Push
echo [3/3] Sending to GitHub (Master to Main)...
git push origin %branch%:main --force

echo.
if %errorlevel% == 0 (
    echo ✅ DONE! Success.
) else (
    echo ❌ FAILED! If it asks for login, please do it.
)
pause
