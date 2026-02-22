import json
import os

BENGALI_DATA_FILE = "bengali_data.json"

class BengaliDataManager:
    def __init__(self):
        self.data = self.load_data()

    def load_data(self):
        if os.path.exists(BENGALI_DATA_FILE):
            try:
                with open(BENGALI_DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"suppliers": [], "employers": [], "workers": []}
        return {"suppliers": [], "employers": [], "workers": []}

    def save_data(self):
        with open(BENGALI_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def add_supplier_employer(self, supplier, employer):
        # Add supplier if unique
        s_entry = {"name": supplier["name"], "phone": supplier["phone"]}
        if s_entry not in self.data["suppliers"]:
            self.data["suppliers"].append(s_entry)
        
        # Add employer if unique
        e_entry = {
            "name": employer["name"], 
            "cafe": employer["cafe"], 
            "mobile": employer["mobile"], 
            "city": employer["city"]
        }
        if e_entry not in self.data["employers"]:
            self.data["employers"].append(e_entry)
        
        self.save_data()
        return True

    def add_worker(self, worker_data):
        import uuid
        if "id" not in worker_data or not worker_data["id"]:
            worker_data["worker_uuid"] = str(uuid.uuid4())[:8]
        else:
            worker_data["worker_uuid"] = str(uuid.uuid4())[:8]
            
        self.data["workers"].append(worker_data)
        self.save_data()
        return True

    def get_workers(self):
        return self.data.get("workers", [])

    def delete_worker(self, worker_uuid):
        initial_count = len(self.data["workers"])
        self.data["workers"] = [w for w in self.data["workers"] if w.get("worker_uuid") != worker_uuid]
        if len(self.data["workers"]) < initial_count:
            self.save_data()
            return True
        return False

    def get_suppliers(self):
        return self.data["suppliers"]

    def get_employers(self):
        return self.data["employers"]
