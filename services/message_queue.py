import queue
import threading
import time
import logging
from services.whatsapp_service import WhatsAppService

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
        logger.info("WhatsApp background worker started.")

    def add_to_queue(self, task_type, **kwargs):
        """Adds a message task to the queue."""
        self.queue.put({"type": task_type, "payload": kwargs})
        logger.info(f"Task added to queue: {task_type}")

    def _process_queue(self):
        while True:
            try:
                task = self.queue.get()
                task_type = task["type"]
                payload = task["payload"]

                logger.info(f"Processing background task: {task_type}")

                if task_type == "text":
                    self.service.send_text_message(**payload)
                elif task_type == "template":
                    self.service.send_template_message(**payload)

                # Rate limiting implementation (e.g., 2 messages per second for SaaS safety)
                time.sleep(0.5)
                self.queue.task_done()

            except Exception as e:
                logger.error(f"Error in background worker: {e}")
                time.sleep(1) # Wait before retry
