import json
import os
from src.config import BENGALI_DATA_FILE

class BengaliDataManager:
    def __init__(self):
        self.data = self.load_data()

    def load_data(self):
        if os.path.exists(BENGALI_DATA_FILE):
            try:
                with open(BENGALI_DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Ensure all workers have UUIDs
                    import uuid
                    if "workers" in data:
                        changed = False
                        for w in data["workers"]:
                            if "worker_uuid" not in w:
                                w["worker_uuid"] = str(uuid.uuid4())[:8]
                                changed = True
                        if changed:
                            # Save back to normalize
                            with open(BENGALI_DATA_FILE, "w", encoding="utf-8") as fw:
                                json.dump(data, fw, ensure_ascii=False, indent=4)
                    return data
            except Exception:
                return {"suppliers": [], "employers": [], "workers": []}
        return {"suppliers": [], "employers": [], "workers": []}

    def save_data(self):
        try:
            with open(BENGALI_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[WARNING] Could not save bengali data to file: {e}")
            # Data stays in memory even if file write fails

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
