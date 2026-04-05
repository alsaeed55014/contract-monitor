@echo off
echo ==================================================
echo   🚀 Pasha Emergency Upload - OVERWRITE MODE
echo ==================================================
echo.

set REPO_URL=https://github.com/alsaeed55014/contract-monitor.git

:: 0. Abort any stuck rebase
echo [1/4] Cleaning up stuck processes...
git rebase --abort >nul 2>nul
git merge --abort >nul 2>nul
git remote remove origin >nul 2>nul
git remote add origin %REPO_URL%

:: 1. Detect Local Branch
for /f "tokens=*" %%i in ('git branch --show-current') do set branch=%%i
if "%branch%"=="" set branch=master
echo Current Branch: %branch%

:: 2. Package
echo [2/4] Packaging local updates...
git add .
git commit -m "Emergency Update - Force Sync"

:: 3. Force Push (Overwrites GitHub with your current local files)
echo [3/4] Overwriting GitHub with your local files...
git push origin %branch%:main --force

echo.
if %errorlevel% == 0 (
    echo ==================================================
    echo   ✅ SUCCESS! Your project is now LIVE on GitHub.
    echo ==================================================
) else (
    echo ==================================================
    echo   ❌ FAILED! If it asks for password/login, please do it.
    echo ==================================================
)

echo.
echo Press any key to close this window...
pause
