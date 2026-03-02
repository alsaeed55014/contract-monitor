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
        """Sends a direct text message via Cloud API."""
        # 1. Log to DB as pending
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
                logger.info(f"Message sent successfully: {meta_id}")
                return True, meta_id
            else:
                error_msg = result.get("error", {}).get("message", "Unknown Error")
                self.db.update_status_from_webhook(None, "failed", error=error_msg) # Note: we don't have meta_id yet
                # Patch for failed request without meta_id:
                self._update_failed_by_uuid(msg_uuid, error_msg)
                logger.error(f"Failed to send message: {error_msg}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Exception in send_text_message: {e}")
            self._update_failed_by_uuid(msg_uuid, str(e))
            return False, str(e)

    def send_template_message(self, to_number, template_name, variables=None, language="ar", worker_id=None, full_name=None, created_by="System"):
        """Sends a template message with dynamic variables."""
        msg_uuid = self.db.log_message(worker_id, full_name, to_number, "template", f"Template: {template_name}", created_by)
        
        parameters = []
        if variables:
            for var in variables:
                parameters.append({"type": "text", "text": str(var)})

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": [{
                    "type": "body",
                    "parameters": parameters
                }]
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
        """Processes incoming webhook events (Statuses)."""
        try:
            entries = data.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    statuses = value.get("statuses", [])
                    for status_obj in statuses:
                        meta_id = status_obj.get("id")
                        status = status_obj.get("status")
                        
                        error = None
                        if status == "failed":
                            errors = status_obj.get("errors", [{}])
                            error = errors[0].get("title", "Unknown Webhook Error")
                        
                        self.db.update_status_from_webhook(meta_id, status, error)
                        logger.info(f"Updated status for {meta_id} to {status}")
            return True
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return False
