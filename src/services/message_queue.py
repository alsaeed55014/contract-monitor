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
        
        # Anti-Ban / Rate Limiting Settings
        self.interval = 1.0           # Default 1 second between messages
        self.batch_size = 0            # Send 0 means no batch limit
        self.break_duration = 0        # Sleep X seconds after batch
        self.sent_since_break = 0
        
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        self._initialized = True

    def set_limits(self, interval, batch_size, break_duration):
        """Updates the rate limiting settings dynamically."""
        self.interval = float(interval)
        self.batch_size = int(batch_size)
        self.break_duration = int(break_duration)
        self.sent_since_break = 0 # Reset counter on new settings
        logger.info(f"Updated Queue Settings: Interval={interval}s, Batch={batch_size}, Break={break_duration}s")

    def add_to_queue(self, task_type, **kwargs):
        self.queue.put({"type": task_type, "payload": kwargs})

    def _process_queue(self):
        while True:
            try:
                task = self.queue.get()
                
                # 1. Proccess Task
                if task["type"] == "text": 
                    self.service.send_text_message(**task["payload"])
                elif task["type"] == "template": 
                    self.service.send_template_message(**task["payload"])
                
                self.sent_since_break += 1
                self.queue.task_done()

                # 2. Handle Batch Break
                if self.batch_size > 0 and self.sent_since_break >= self.batch_size:
                    logger.info(f"Batch limit reached ({self.batch_size}). Taking a break for {self.break_duration}s")
                    time.sleep(self.break_duration)
                    self.sent_since_break = 0
                else:
                    # 3. Handle Normal Interval
                    time.sleep(self.interval)

            except Exception as e:
                logger.error(f"Queue Error: {e}")
                time.sleep(2)
