import queue
import threading
import time
import logging
from src.services.whatsapp_service import WhatsAppService

logger = logging.getLogger("MessageQueue")

class WhatsAppQueue:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WhatsAppQueue, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self.queue = queue.Queue()
        self.service = WhatsAppService()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        self._initialized = True

    def add_to_queue(self, task_type, **kwargs):
        self.queue.put({"type": task_type, "payload": kwargs})

    def _process_queue(self):
        while True:
            try:
                task = self.queue.get()
                if task["type"] == "text": self.service.send_text_message(**task["payload"])
                elif task["type"] == "template": self.service.send_template_message(**task["payload"])
                time.sleep(0.5)
                self.queue.task_done()
            except Exception as e:
                logger.error(f"Queue Error: {e}")
                time.sleep(1)
