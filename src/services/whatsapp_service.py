import requests
import os
import json
import logging
from datetime import datetime
from src.data.whatsapp_db import WhatsAppDB

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WhatsAppService")

class WhatsAppService:
    def __init__(self):
        self.access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
        self.version = os.environ.get("WHATSAPP_API_VERSION", "v18.0")
        self.base_url = f"https://graph.facebook.com/{self.version}/{self.phone_number_id}/messages"
        self.db = WhatsAppDB()

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def send_text_message(self, to_number, message, worker_id=None, full_name=None, created_by="System"):
        msg_uuid = self.db.log_message(worker_id, full_name, to_number, "text", message, created_by)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {"body": message}
        }
        try:
            response = requests.post(self.base_url, headers=self._get_headers(), json=payload, timeout=10)
            result = response.json()
            if response.status_code == 200:
                meta_id = result.get("messages", [{}])[0].get("id")
                self.db.update_message_meta(msg_uuid, meta_id)
                return True, meta_id
            else:
                error_msg = result.get("error", {}).get("message", "Unknown Error")
                self._update_failed_by_uuid(msg_uuid, error_msg)
                return False, error_msg
        except Exception as e:
            self._update_failed_by_uuid(msg_uuid, str(e))
            return False, str(e)

    def send_template_message(self, to_number, template_name, variables=None, language="ar", worker_id=None, full_name=None, created_by="System"):
        msg_uuid = self.db.log_message(worker_id, full_name, to_number, "template", f"Template: {template_name}", created_by)
        parameters = [{"type": "text", "text": str(v)} for v in variables] if variables else []
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": [{"type": "body", "parameters": parameters}]
            }
        }
        try:
            response = requests.post(self.base_url, headers=self._get_headers(), json=payload, timeout=10)
            result = response.json()
            if response.status_code == 200:
                meta_id = result.get("messages", [{}])[0].get("id")
                self.db.update_message_meta(msg_uuid, meta_id)
                return True, meta_id
            else:
                error_msg = result.get("error", {}).get("message", "Unknown Error")
                self._update_failed_by_uuid(msg_uuid, error_msg)
                return False, error_msg
        except Exception as e:
            self._update_failed_by_uuid(msg_uuid, str(e))
            return False, str(e)

    def _update_failed_by_uuid(self, msg_uuid, error_msg):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE whatsapp_messages SET status = "failed", error_message = ?, failed_at = ? WHERE id = ?', 
                       (error_msg, datetime.now(), msg_uuid))
        conn.commit()
        conn.close()

    def handle_webhook(self, data):
        try:
            statuses = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("statuses", [])
            for s in statuses:
                meta_id = s.get("id")
                status = s.get("status")
                error = s.get("errors", [{}])[0].get("title") if status == "failed" else None
                self.db.update_status_from_webhook(meta_id, status, error)
            return True
        except Exception: return False
