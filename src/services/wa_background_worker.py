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
sys.path.insert(0, BASE_DIR)  # ✅ Inserté TOUT EN HAUT avant les imports locaux

# ✅ IMPORT DES LIMITES ANTI-BAN DÉFINIES DANS whatsapp_service.py (même référentiel)
from src.services.whatsapp_service import ANTIBAN
# ✅ Utilisation des MEMES FICHIERS que whatsapp_ui.py via src/config
from src.config import WA_HISTORY_FILE as CONFIG_WA_HISTORY_FILE

WA_WORKER_JOB_FILE  = os.path.join(BASE_DIR, "wa_worker_job.json")    # الأوامر من Streamlit للعامل
WA_WORKER_STATE_FILE = os.path.join(BASE_DIR, "wa_worker_state.json") # حالة العامل لـ Streamlit
WA_WORKER_LOG_FILE   = os.path.join(BASE_DIR, "wa_worker_log.json")   # سجل الإرسال
# ✅ MÊME fichier historique que l'UI — PAS wa_history.json (mauvais nom!)
WA_HISTORY_FILE      = CONFIG_WA_HISTORY_FILE

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
    """محرك مكافحة حظر واتساب المتقدم 2026 — يقرأ حدود الأمان من ANTIBAN GLOBAL"""

    def __init__(self):
        self.sent_count_session = 0
        self.session_start = time.time()

    def get_delay(self, base_delay: int, batch_size: int, idx: int, batch_delay: int, start_from: int = 0) -> tuple[int, str]:
        """احسب التأخير الذكي لكل رسالة — باستخدام الحدود GLOBALES de ANTIBAN (même référentiel)"""
        # ============================================================
        # 🛡️ PLANCHER DE SÉCURITÉ (même si l'utilisateur force une valeur inférieure)
        # ============================================================
        MIN_SEC = ANTIBAN["MIN_INTER_MESSAGE_SEC"]        # 20 secondes minimum
        MIN_BATCH_MSG = ANTIBAN["MIN_MESSAGES_BEFORE_BREAK"]  # 5 messages minimum avant pause
        MIN_BATCH_SEC = ANTIBAN["MIN_BATCH_BREAK_SEC"]    # 300 secondes minimum entre pauses

        # Appliquer les planchers durs
        safe_base_delay = max(MIN_SEC, int(base_delay))
        safe_batch_size = max(MIN_BATCH_MSG, int(batch_size)) if batch_size > 0 else MIN_BATCH_MSG
        safe_batch_delay = max(MIN_BATCH_SEC, int(batch_delay))

        effective_batch = min(safe_batch_size, 20)
        effective_batch_delay = safe_batch_delay

        processed_in_job = idx - start_from
        is_batch_break = processed_in_job > 0 and processed_in_job % effective_batch == 0

        if is_batch_break:
            # استراحة طويلة بين الدفعات (تشبه البشر) + gauss
            delay = int(random.gauss(effective_batch_delay, effective_batch_delay * 0.15))
            delay = max(effective_batch_delay, delay)
            return delay, "batch_break"

        # 🛡️ 2026 Warm-Up Pace: البداية بحذر في أول 5 رسائل للحساب
        safe_base = safe_base_delay
        if processed_in_job < 5:
            safe_base = int(safe_base * random.uniform(1.6, 2.2))  # PLUS LENT au démarrage
        elif processed_in_job < 15:
            safe_base = int(safe_base * random.uniform(1.2, 1.6))  # Lent encore

        # تأخير أساسي مع ضوضاء غاوسية للطبيعية
        jitter = random.gauss(0, safe_base * 0.30)
        delay = int(safe_base + jitter)
        delay = max(MIN_SEC, delay)

        # استراحة تفكير مفاجئة كل 3-6 رسائل
        think_break_chance = 1.0 / random.randint(3, 6)
        if random.random() < think_break_chance:
            extra = int(random.uniform(12, 30))
            delay += extra
            return delay, "think_break"

        return delay, "normal"

    def should_stealth_break(self, idx: int) -> bool:
        """🛡️ قرار استراحة تمويهية كل 12-18 رسالة (moins souvent pour éviter pattern suspect)"""
        return idx > 0 and idx % random.randint(12, 18) == 0

    def get_stealth_break_duration(self) -> int:
        """مدة الاستراحة التمويهية — 4-8 دقائق (un peu plus long et réaliste)"""
        return int(random.uniform(240, 480))


def run_worker():
    """الحلقة الرئيسية للعامل"""
    print(f"[{time.strftime('%H:%M:%S')}] 🚀 Worker started (PID={os.getpid()})")
    update_state("idle")

    # ── استيراد الخدمة ──
    # (sys.path déjà inséré tout en haut du fichier)
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
                print(f"[{time.strftime('%H:%M:%S')}] 🛡️ Planchers appliqués: min {ANTIBAN['MIN_INTER_MESSAGE_SEC']}s inter-message, {ANTIBAN['DAILY_HARD_LIMIT_ESTABLISHED']} msg/jour max")
                update_state("starting", current_idx=start_from, total=total)

                # ── تشغيل المحرك إذا لم يكن يعمل ──
                if wa is None:
                    wa = WhatsAppService()

                # 🛡️ Worker headless mode:
                # - على بيئة السحابة (Linux): headless إلزامي
                # - على Windows المحلي: headless=False لاستعادة الجلسة بشكل صحيح
                is_cloud_env = ("/mount/" in BASE_DIR.replace("\\", "/")
                                or os.path.exists("/mount")
                                or (not os.environ.get("DISPLAY", "") and os.name != "nt"))
                run_headless = is_cloud_env  # Windows local = False, Cloud Linux = True
                driver_ok, driver_msg = wa.start_driver(headless=run_headless, force_clean=False)
                if not driver_ok:
                    # Retry avec la valeur opposée
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️  Headless={run_headless} échoué, retry avec {not run_headless}...")
                    if wa:
                        try: wa.close()
                        except: pass
                        wa = WhatsAppService()
                    driver_ok, driver_msg = wa.start_driver(headless=(not run_headless), force_clean=False)

                if not driver_ok:
                    update_state("error", error=f"فشل تشغيل المحرك: {driver_msg}")
                    append_log({
                        "idx": -1, "name": "SYSTEM", "phone": "-",
                        "status": f"فشل تشغيل المتصفح: {driver_msg}",
                        "ok": False,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
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
                anti_ban_triggered = False
                anti_ban_reason = ""

                update_state("sending", current_idx=start_from, total=total)

                for i in range(start_from, total):
                    # تحقق من أمر الإيقاف قبل كل رسالة
                    current_job = load_json(WA_WORKER_JOB_FILE, {})
                    if current_job.get("command") == "stop" or current_job.get("job_id") != job_id:
                        print(f"[{time.strftime('%H:%M:%S')}] 🛑 Interrupted at {i}/{total}")
                        update_state("stopped", current_idx=i, total=total)
                        save_json(WA_WORKER_JOB_FILE, {"command": "idle"})
                        break

                    # 🛡️ Si une protection anti-ban a déjà déclenché, on arrête TOUTE la campagne
                    if anti_ban_triggered:
                        update_state("error", error=f"🛑 أمان: {anti_ban_reason}")
                        append_log({
                            "idx": i, "name": name, "phone": "-",
                            "status": f"STOPPÉ - {anti_ban_reason}",
                            "ok": False,
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        continue

                    trg = targets[i]
                    phone = trg.get("phone", "")
                    name  = trg.get("name", "Client")
                    cv    = trg.get("cv", "")

                    # 🛡️ 2026 Pre-Send Phone Validation
                    clean_p = "".join(filter(str.isdigit, str(phone)))
                    if len(clean_p) < 8:
                        print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Skipped invalid phone: {phone}")
                        append_log({
                            "idx": i,
                            "name": name,
                            "phone": phone,
                            "status": "رقم قصير أو غير صالح",
                            "ok": False,
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        continue

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
                        wait_secs, break_type = anti_ban.get_delay(base_delay, batch_size, i, batch_delay, start_from=start_from)
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

                    # 🛡️ DÉTECTION D'UN BLOCAGE ANTI-BAN → arrêt de la campagne ENTIÈRE
                    if not ok and str(log_msg).startswith("🛑"):
                        anti_ban_triggered = True
                        anti_ban_reason = str(log_msg)
                        print(f"[{time.strftime('%H:%M:%S')}] 🚫 PROTECTION ANTI-BAN DÉCLENCHÉE → {anti_ban_reason}")
                        update_state("error", error=anti_ban_reason)
                        # On ne sort pas de la boucle, les itérations suivantes seront skipées

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
                    time.sleep(random.uniform(1.8, 4.0))

                else:
                    # انتهى الإرسال
                    if anti_ban_triggered:
                        # On garde le status error défini plus haut
                        pass
                    else:
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
