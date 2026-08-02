"""
wa_background_worker.py
========================
عامل إرسال واتساب في الخلفية - يعمل كعملية مستقلة
يعمل حتى لو أُغلق المتصفح أو انقطع الاتصال
يتواصل مع Streamlit عبر ملفات JSON (shared state)
"""

import os
import sys
import json
import time
import random
import signal
import traceback
from datetime import datetime

# ─── مسارات الملفات المشتركة ───────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WA_WORKER_JOB_FILE  = os.path.join(BASE_DIR, "wa_worker_job.json")    # الأوامر من Streamlit للعامل
WA_WORKER_STATE_FILE = os.path.join(BASE_DIR, "wa_worker_state.json") # حالة العامل لـ Streamlit
WA_WORKER_LOG_FILE   = os.path.join(BASE_DIR, "wa_worker_log.json")   # سجل الإرسال
WA_HISTORY_FILE      = os.path.join(BASE_DIR, "wa_history.json")      # سجل الأرقام المرسلة

def load_json(path, default=None):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return default if default is not None else {}

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def update_state(status, current_idx=None, total=None, current_name=None, current_phone=None, error=None):
    state = load_json(WA_WORKER_STATE_FILE, {})
    state.update({
        "status": status,
        "updated_at": datetime.now().isoformat(),
        "pid": os.getpid()
    })
    if current_idx is not None: state["current_idx"] = current_idx
    if total is not None:       state["total"] = total
    if current_name is not None: state["current_name"] = current_name
    if current_phone is not None: state["current_phone"] = current_phone
    if error is not None:        state["error"] = error
    save_json(WA_WORKER_STATE_FILE, state)

def append_log(entry: dict):
    logs = load_json(WA_WORKER_LOG_FILE, [])
    logs.append(entry)
    save_json(WA_WORKER_LOG_FILE, logs[-500:])  # احتفظ بآخر 500 سجل فقط

def load_history():
    data = load_json(WA_HISTORY_FILE, [])
    return set(data) if isinstance(data, list) else set()

def save_history(history_set):
    save_json(WA_HISTORY_FILE, list(history_set))

# ─── نظام مكافحة الحظر المتقدم ─────────────────────────────────

class AntiBanEngine:
    """محرك مكافحة حظر واتساب 2026"""

    def __init__(self):
        self.sent_count_session = 0
        self.session_start = time.time()

    def get_delay(self, base_delay: int, batch_size: int, idx: int, batch_delay: int) -> tuple[int, str]:
        """احسب التأخير الذكي لكل رسالة"""
        is_batch_break = batch_size > 0 and idx > 0 and idx % batch_size == 0

        if is_batch_break:
            # استراحة طويلة بين الدفعات (تشبه البشر)
            delay = int(random.gauss(batch_delay, batch_delay * 0.2))
            delay = max(batch_delay // 2, delay)
            return delay, "batch_break"

        # تأخير أساسي مع ضوضاء غاوسية للطبيعية
        jitter = random.gauss(0, base_delay * 0.3)
        delay = int(base_delay + jitter)
        delay = max(5, delay)  # لا يقل عن 5 ثواني

        # استراحة تفكير مفاجئة كل 3-7 رسائل
        think_break_chance = 1.0 / random.randint(3, 7)
        if random.random() < think_break_chance:
            extra = int(random.uniform(8, 20))
            delay += extra
            return delay, "think_break"

        return delay, "normal"

    def should_stealth_break(self, idx: int) -> bool:
        """تقرر إذا كانت استراحة تمويهية مطلوبة"""
        return idx > 0 and idx % random.randint(15, 25) == 0

    def get_stealth_break_duration(self) -> int:
        """مدة الاستراحة التمويهية (تشبه الإنسان الذي توقف مؤقتاً)"""
        return int(random.uniform(120, 300))  # 2-5 دقائق


def run_worker():
    """الحلقة الرئيسية للعامل"""
    print(f"[{time.strftime('%H:%M:%S')}] 🚀 Worker started (PID={os.getpid()})")
    update_state("idle")

    # ── استيراد الخدمة ──
    sys.path.insert(0, BASE_DIR)
    from src.services.whatsapp_service import WhatsAppService

    wa = None
    anti_ban = AntiBanEngine()
    history = load_history()
    last_job_id = None

    while True:
        try:
            job = load_json(WA_WORKER_JOB_FILE, {})

            # ── التحقق من وجود أمر إيقاف ──
            if job.get("command") == "stop":
                print(f"[{time.strftime('%H:%M:%S')}] 🛑 Stop command received")
                update_state("stopped")
                if wa:
                    wa.close()
                    wa = None
                # امسح الأمر
                save_json(WA_WORKER_JOB_FILE, {"command": "idle"})
                time.sleep(2)
                continue

            # ── التحقق من وجود وظيفة إرسال ──
            if job.get("command") == "send" and job.get("job_id") != last_job_id:
                job_id     = job.get("job_id")
                targets    = job.get("targets", [])
                messages   = job.get("messages", [""])
                base_delay = int(job.get("delay", 60))
                batch_size = int(job.get("batch_size", 10))
                batch_delay = int(job.get("batch_delay", 600))
                is_smart   = job.get("is_smart", False)
                custom_job = job.get("custom_job", "")
                attachment = job.get("attachment_path", None)
                switch_threshold = int(job.get("msg_switch_threshold", 1))
                start_from = int(job.get("start_from", 0))

                last_job_id = job_id
                total = len(targets)

                print(f"[{time.strftime('%H:%M:%S')}] 📨 New job: {total} targets, delay={base_delay}s")
                update_state("starting", current_idx=start_from, total=total)

                # ── تشغيل المحرك إذا لم يكن يعمل ──
                if wa is None:
                    wa = WhatsAppService()

                driver_ok, driver_msg = wa.start_driver(headless=False, force_clean=False)
                if not driver_ok:
                    update_state("error", error=f"فشل تشغيل المحرك: {driver_msg}")
                    save_json(WA_WORKER_JOB_FILE, {"command": "idle"})
                    time.sleep(5)
                    continue

                # ── انتظر الاتصال (إذا لم يكن متصلاً) ──
                status = wa.get_status()
                if status != "Connected":
                    update_state("awaiting_login")
                    # انتظر حتى 5 دقائق
                    for _ in range(300):
                        time.sleep(1)
                        job = load_json(WA_WORKER_JOB_FILE, {})
                        if job.get("command") == "stop":
                            break
                        status = wa.get_status()
                        if status == "Connected":
                            break
                    if wa.get_status() != "Connected":
                        update_state("error", error="لم يتم الاتصال بواتساب خلال 5 دقائق")
                        continue

                # ── حلقة الإرسال ──
                msg_idx = 0
                msg_sent_count = 0
                anti_ban = AntiBanEngine()
                history = load_history()

                update_state("sending", current_idx=start_from, total=total)

                for i in range(start_from, total):
                    # تحقق من أمر الإيقاف قبل كل رسالة
                    current_job = load_json(WA_WORKER_JOB_FILE, {})
                    if current_job.get("command") == "stop" or current_job.get("job_id") != job_id:
                        print(f"[{time.strftime('%H:%M:%S')}] 🛑 Interrupted at {i}/{total}")
                        update_state("stopped", current_idx=i, total=total)
                        save_json(WA_WORKER_JOB_FILE, {"command": "idle"})
                        break

                    trg = targets[i]
                    phone = trg.get("phone", "")
                    name  = trg.get("name", "Client")
                    cv    = trg.get("cv", "")

                    update_state("sending", current_idx=i, total=total,
                                 current_name=name, current_phone=phone)

                    # ── توليد الرسالة ──
                    if is_smart:
                        from src.ui.whatsapp_ui import generate_smart_message
                        final_msg = generate_smart_message(name, cv, custom_job=custom_job)
                    else:
                        msg_body = messages[msg_idx % len(messages)]
                        import re
                        final_msg = msg_body
                        for k, v in trg.items():
                            final_msg = final_msg.replace("{" + str(k) + "}", str(v))
                        final_msg = final_msg.replace("{Name}", name).replace("{name}", name)
                        final_msg = final_msg.replace("{CV}", cv).replace("{cv}", cv)
                        final_msg = re.sub(r'\n{3,}', '\n\n', final_msg).strip()

                    # ── إرسال التأخير (ما عدا الأولى) ──
                    if i > start_from:
                        wait_secs, break_type = anti_ban.get_delay(base_delay, batch_size, i, batch_delay)
                        print(f"[{time.strftime('%H:%M:%S')}] ⏳ Waiting {wait_secs}s ({break_type})")

                        # حدّث الحالة مع العد التنازلي
                        for remaining in range(wait_secs, 0, -1):
                            chk_job = load_json(WA_WORKER_JOB_FILE, {})
                            if chk_job.get("command") == "stop" or chk_job.get("job_id") != job_id:
                                print(f"[{time.strftime('%H:%M:%S')}] 🛑 Stop during delay")
                                update_state("stopped", current_idx=i, total=total)
                                save_json(WA_WORKER_JOB_FILE, {"command": "idle"})
                                break

                            # احتفظ بـ Chrome نشطاً
                            if remaining % 10 == 0:
                                wa.keep_alive()

                            state_data = load_json(WA_WORKER_STATE_FILE, {})
                            state_data.update({
                                "countdown": remaining,
                                "countdown_type": break_type,
                                "updated_at": datetime.now().isoformat()
                            })
                            save_json(WA_WORKER_STATE_FILE, state_data)
                            time.sleep(1)
                        else:
                            # استراحة تمويهية كبيرة كل N رسالة
                            if anti_ban.should_stealth_break(i):
                                stealth_dur = anti_ban.get_stealth_break_duration()
                                print(f"[{time.strftime('%H:%M:%S')}] 🛡️ Stealth break: {stealth_dur}s")
                                for remaining in range(stealth_dur, 0, -1):
                                    chk_job = load_json(WA_WORKER_JOB_FILE, {})
                                    if chk_job.get("command") == "stop":
                                        break
                                    if remaining % 10 == 0:
                                        wa.keep_alive()
                                    s = load_json(WA_WORKER_STATE_FILE, {})
                                    s.update({"countdown": remaining, "countdown_type": "stealth_break",
                                              "updated_at": datetime.now().isoformat()})
                                    save_json(WA_WORKER_STATE_FILE, s)
                                    time.sleep(1)

                    # ── أرسل الرسالة ──
                    print(f"[{time.strftime('%H:%M:%S')}] 📤 Sending to {name} ({phone})")
                    ok, log_msg = wa.send_message(phone, final_msg, attachment_path=attachment)

                    entry = {
                        "idx": i,
                        "name": name,
                        "phone": phone,
                        "status": log_msg if ok else f"فشل ({log_msg})",
                        "ok": ok,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    append_log(entry)

                    if ok:
                        history.add(phone)
                        save_history(history)
                        anti_ban.sent_count_session += 1
                        msg_sent_count += 1
                        if msg_sent_count >= switch_threshold:
                            msg_sent_count = 0
                            msg_idx = min(msg_idx + 1, len(messages) - 1)
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] ❌ Failed: {log_msg}")

                    # اثنين ثانية استراحة صغيرة بعد الإرسال دائماً
                    time.sleep(random.uniform(1.5, 3.5))

                else:
                    # انتهى الإرسال
                    update_state("done", current_idx=total, total=total)
                    print(f"[{time.strftime('%H:%M:%S')}] ✅ All {total} targets processed")
                    save_json(WA_WORKER_JOB_FILE, {"command": "idle"})
                    continue

            # ── وضع الخمول ──
            state = load_json(WA_WORKER_STATE_FILE, {})
            if state.get("status") not in ["idle", "stopped", "done", "error", "awaiting_login"]:
                update_state("idle")

            # keep alive للمحرك إذا كان مفتوحاً
            if wa:
                wa.keep_alive()

            time.sleep(2)

        except KeyboardInterrupt:
            print(f"[{time.strftime('%H:%M:%S')}] Worker terminated by user")
            update_state("stopped")
            if wa:
                wa.close()
            break
        except Exception as e:
            err = traceback.format_exc()
            print(f"[{time.strftime('%H:%M:%S')}] ❌ Worker error: {e}")
            update_state("error", error=str(e)[:200])
            time.sleep(5)


if __name__ == "__main__":
    run_worker()
