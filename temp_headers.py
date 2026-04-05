import sys
import os
sys.path.insert(0, r"c:\Users\ا\Desktop\non2")
from src.data.db_client import DBClient

db = DBClient()
df = db.fetch_data()
with open("temp_headers.txt", "w", encoding="utf-8") as f:
    f.write("Workers (Main) Headers:\n")
    f.write(str(list(df.columns) if not df.empty else "No headers"))
    
    f.write("\n\nCustomer Requests Headers:\n")
    req_df = db.fetch_customer_requests()
    f.write(str(list(req_df.columns) if not req_df.empty else "No headers"))
