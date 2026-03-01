import sqlite3
import uuid
from datetime import datetime
import os

DB_PATH = os.path.join(os.getcwd(), "whatsapp_tracking.db")

class WhatsAppDB:
    def __init__(self):
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whatsapp_messages (
                id TEXT PRIMARY KEY,
                worker_id TEXT,
                full_name TEXT,
                phone_normalized TEXT,
                message_type TEXT,
                message_content TEXT,
                meta_message_id TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                sent_at TIMESTAMP,
                delivered_at TIMESTAMP,
                read_at TIMESTAMP,
                failed_at TIMESTAMP,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def log_message(self, worker_id, full_name, phone, msg_type, content, created_by, meta_id=None):
        msg_uuid = str(uuid.uuid4())
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO whatsapp_messages 
            (id, worker_id, full_name, phone_normalized, message_type, message_content, meta_message_id, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (msg_uuid, worker_id, full_name, phone, msg_type, content, meta_id, created_by))
        conn.commit()
        conn.close()
        return msg_uuid

    def update_message_meta(self, msg_uuid, meta_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE whatsapp_messages SET meta_message_id = ?, status = "sent", sent_at = ? WHERE id = ?', 
                       (meta_id, datetime.now(), msg_uuid))
        conn.commit()
        conn.close()

    def update_status_from_webhook(self, meta_id, status, error=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        timestamp_col = {
            'delivered': 'delivered_at',
            'read': 'read_at',
            'failed': 'failed_at',
            'sent': 'sent_at'
        }.get(status)

        query = f'UPDATE whatsapp_messages SET status = ?'
        params = [status]
        
        if timestamp_col:
            query += f', {timestamp_col} = ?'
            params.append(datetime.now())
        
        if error:
            query += ', error_message = ?'
            params.append(str(error))

        query += ' WHERE meta_message_id = ?'
        params.append(meta_id)
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()

    def get_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT status, COUNT(*) as count FROM whatsapp_messages GROUP BY status')
        stats = {row['status']: row['count'] for row in cursor.fetchall()}
        conn.close()
        return stats

    def get_recent_messages(self, limit=50):
        conn = self.get_connection()
        df_query = "SELECT * FROM whatsapp_messages ORDER BY created_at DESC LIMIT ?"
        import pandas as pd
        df = pd.read_sql_query(df_query, conn, params=(limit,))
        conn.close()
        return df
