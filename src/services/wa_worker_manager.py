"""
wa_worker_manager.py
======================
مدير العامل الخلفي لواتساب - واجهة بين Streamlit والعملية الخلفية
"""
import os
import sys
import json
import time
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WA_WORKER_JOB_FILE   = os.path.join(BASE_DIR, "wa_worker_job.json")
WA_WORKER_STATE_FILE = os.path.join(BASE_DIR, "wa_worker_state.json")
WA_WORKER_LOG_FILE   = os.path.join(BASE_DIR, "wa_worker_log.json")
WA_WORKER_PID_FILE   = os.path.join(BASE_DIR, "wa_worker.pid")

def _load(path, default=None):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return default if default is not None else {}

def _save(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


class WAWorkerManager:
    """واجهة Streamlit لإدارة عملية الإرسال الخلفية"""

    def is_worker_alive(self) -> bool:
        """هل العملية الخلفية لا تزال تعمل؟"""
        pid_data = _load(WA_WORKER_PID_FILE, {})
        pid = pid_data.get("pid")
        if not pid:
            return False
        try:
            if os.name == "nt":
                # Windows
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                    capture_output=True, text=True, timeout=5
                )
                return str(pid) in result.stdout
            else:
                os.kill(pid, 0)
                return True
        except:
            return False

    def get_state(self) -> dict:
        """اقرأ حالة العامل الحالية"""
        return _load(WA_WORKER_STATE_FILE, {"status": "not_started"})

    def get_logs(self, last_n: int = 100) -> list:
        """اقرأ آخر N سجلات"""
        logs = _load(WA_WORKER_LOG_FILE, [])
        return logs[-last_n:]

    def start_worker(self) -> bool:
        """شغّل عملية العامل الخلفية إذا لم تكن تعمل"""
        if self.is_worker_alive():
            return True  # تعمل بالفعل

        worker_script = os.path.join(BASE_DIR, "src", "services", "wa_background_worker.py")
        python_exe = sys.executable

        try:
            # شغّل بدون نافذة (Windows: CREATE_NO_WINDOW)
            kwargs = {}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen(
                [python_exe, worker_script],
                cwd=BASE_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **kwargs
            )
            _save(WA_WORKER_PID_FILE, {"pid": proc.pid, "started_at": datetime.now().isoformat()})
            time.sleep(1.5)  # أعطه وقتاً للتهيئة
            return True
        except Exception as e:
            print(f"[WAWorkerManager] Failed to start worker: {e}")
            return False

    def stop_worker(self):
        """أوقف العملية الخلفية"""
        _save(WA_WORKER_JOB_FILE, {"command": "stop"})
        # انتظر قليلاً ثم اقتل العملية إذا لم تستجب
        time.sleep(3)
        pid_data = _load(WA_WORKER_PID_FILE, {})
        pid = pid_data.get("pid")
        if pid and self.is_worker_alive():
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], timeout=5,
                                   capture_output=True)
                else:
                    os.kill(pid, 9)
            except:
                pass
        _save(WA_WORKER_PID_FILE, {})

    def send_job(self, targets: list, messages: list, delay: int, batch_size: int,
                 batch_delay: int, is_smart: bool, custom_job: str,
                 attachment_path: str = None, msg_switch_threshold: int = 1,
                 start_from: int = 0):
        """أرسل وظيفة إرسال للعامل الخلفي"""
        import uuid
        job = {
            "command": "send",
            "job_id": str(uuid.uuid4()),
            "targets": targets,
            "messages": messages,
            "delay": delay,
            "batch_size": batch_size,
            "batch_delay": batch_delay,
            "is_smart": is_smart,
            "custom_job": custom_job,
            "attachment_path": attachment_path,
            "msg_switch_threshold": msg_switch_threshold,
            "start_from": start_from,
            "submitted_at": datetime.now().isoformat()
        }
        _save(WA_WORKER_JOB_FILE, job)
        return job["job_id"]

    def clear_logs(self):
        _save(WA_WORKER_LOG_FILE, [])

    def get_wa_status(self) -> str:
        """اقرأ حالة واتساب من العامل"""
        state = self.get_state()
        return state.get("status", "not_started")
