#!/usr/bin/env python3
"""إعادة تشغيل خدمة الإشعارات"""
import os
import subprocess
import sys
import json
from pathlib import Path

# 1. إيقاف أي عملية سابقة
def kill_existing():
    try:
        cmd = 'wmic process where "name=\'python.exe\'" get CommandLine,ProcessId'
        output = subprocess.check_output(cmd, shell=True).decode(errors='ignore')
        for line in output.split('\n'):
            if 'antigravity_notification.py' in line:
                parts = line.split()
                for part in reversed(parts):
                    if part.isdigit():
                        print(f"إيقاف العملية {part}...")
                        os.system(f"taskkill /PID {part} /F >nul 2>&1")
                        break
    except Exception as e:
        print(f"تجاوز خطأ إيقاف العملية: {e}")

# 2. تحديث الحالة - إعادة ضبط العدادات
def reset_state():
    state_file = Path("state.json")
    if state_file.exists():
        with open(state_file, "w") as f:
            # إعادة تعيين العدادات - سيتم تحديثها عند بدء التشغيل
            json.dump({}, f)
        print("✅ تم إعادة ضبط ملف الحالة")

# 3. تشغيل الخدمة
def start_service():
    script_path = os.path.abspath("antigravity_notification.py")
    print(f"🚀 تشغيل خدمة الإشعارات...")
    print(f"📁 المسار: {script_path}")
    
    subprocess.Popen([sys.executable, script_path], 
                     creationflags=subprocess.CREATE_NO_WINDOW,
                     close_fds=True)
    print("✅ تم تشغيل الخدمة في الخلفية")

if __name__ == "__main__":
    print("=== إعادة تشغيل خدمة الإشعارات ===\n")
    kill_existing()
    reset_state()
    start_service()
    print("\n📌 سيتم التحقق من البيانات الجديدة خلال 30 ثانية")
    print("📋 سجل الأحداث: notification_service.log")
    input("\nاضغط Enter للخروج...")
