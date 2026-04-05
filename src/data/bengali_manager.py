<<<<<<< HEAD
import json
import os
import uuid
from src.config import BENGALI_DATA_FILE

class BengaliDataManager:
    def __init__(self):
        self.data = self.load_data()

    def load_data(self):
        default_structure = {"suppliers": [], "employers": [], "workers": []}
        if not os.path.exists(BENGALI_DATA_FILE):
            return default_structure
            
        try:
            with open(BENGALI_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return default_structure
                
                changed = False
                
                # Ensure keys exist and are lists
                for key in ["workers", "suppliers", "employers"]:
                    if key not in data or not isinstance(data[key], list):
                        data[key] = []
                        changed = True
                
                # Filter out non-dict items and ensure IDs
                # Workers
                valid_workers = []
                for w in data["workers"]:
                    if isinstance(w, dict):
                        if "worker_uuid" not in w:
                            w["worker_uuid"] = str(uuid.uuid4())[:12]
                            changed = True
                        valid_workers.append(w)
                    else:
                        changed = True
                data["workers"] = valid_workers
                
                # Suppliers
                valid_suppliers = []
                for s in data["suppliers"]:
                    if isinstance(s, dict):
                        if "id" not in s:
                            s["id"] = str(uuid.uuid4())[:12]
                            changed = True
                        valid_suppliers.append(s)
                    else:
                        changed = True
                data["suppliers"] = valid_suppliers
                
                # Employers
                valid_employers = []
                for e in data["employers"]:
                    if isinstance(e, dict):
                        if "id" not in e:
                            e["id"] = str(uuid.uuid4())[:12]
                            changed = True
                        valid_employers.append(e)
                    else:
                        changed = True
                data["employers"] = valid_employers

                if changed:
                    self.data = data # Temporary assign for save_data
                    self.save_data()
                return data
        except Exception as ex:
            print(f"[ERROR] Failed to load bengali data: {ex}")
            return default_structure

    def save_data(self):
        try:
            with open(BENGALI_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[WARNING] Could not save bengali data to file: {e}")

    def add_supplier(self, supplier):
        """Add ONLY a supplier."""
        if not isinstance(supplier, dict): return False
        
        s_id = str(uuid.uuid4())[:12]
        s_entry = {
            "id": s_id, 
            "name": supplier.get("name", ""), 
            "phone": supplier.get("phone", ""),
            "notes": supplier.get("notes", "")
        }
        
        # Ensure suppliers list exists
        if "suppliers" not in self.data:
            self.data["suppliers"] = []
            
        # Check by name so we don't have duplicates
        exists = any(s.get("name") == s_entry["name"] for s in self.data["suppliers"] if isinstance(s, dict))
        if not exists:
            self.data["suppliers"].append(s_entry)
            self.save_data()
        return True

    def add_employer(self, employer):
        """Add ONLY an employer."""
        if not isinstance(employer, dict): return False
        
        e_id = str(uuid.uuid4())[:12]
        e_entry = {
            "id": e_id,
            "name": employer.get("name", ""), 
            "cafe": employer.get("cafe", ""), 
            "mobile": employer.get("mobile", ""), 
            "city": employer.get("city", ""),
            "notes": employer.get("notes", "")
        }
        
        if "employers" not in self.data:
            self.data["employers"] = []
            
        exists = any(e.get("name") == e_entry["name"] for e in self.data["employers"] if isinstance(e, dict))
        if not exists:
            self.data["employers"].append(e_entry)
            self.save_data()
        return True

    def add_worker(self, worker_data):
        if not isinstance(worker_data, dict): return False
        
        if "worker_uuid" not in worker_data:
            worker_data["worker_uuid"] = str(uuid.uuid4())[:12]
            
        if "workers" not in self.data:
            self.data["workers"] = []
            
        self.data["workers"].append(worker_data)
        self.save_data()
        return True

    def update_worker(self, worker_uuid, new_data):
        if not isinstance(new_data, dict): return False
        for i, w in enumerate(self.data.get("workers", [])):
            if isinstance(w, dict) and w.get("worker_uuid") == worker_uuid:
                new_data["worker_uuid"] = worker_uuid
                new_data["timestamp"] = new_data.get("timestamp", w.get("timestamp"))
                self.data["workers"][i] = new_data
                self.save_data()
                return True
        return False

    def update_supplier(self, sup_id, new_data):
        if not isinstance(new_data, dict): return False
        for i, s in enumerate(self.data.get("suppliers", [])):
            if isinstance(s, dict) and s.get("id") == sup_id:
                new_data["id"] = sup_id
                self.data["suppliers"][i] = new_data
                self.save_data()
                return True
        return False

    def delete_supplier(self, sup_id):
        initial_count = len(self.data.get("suppliers", []))
        self.data["suppliers"] = [s for s in self.data.get("suppliers", []) if isinstance(s, dict) and s.get("id") != sup_id]
        if len(self.data["suppliers"]) < initial_count:
            self.save_data()
            return True
        return False

    def update_employer(self, emp_id, new_data):
        if not isinstance(new_data, dict): return False
        for i, e in enumerate(self.data.get("employers", [])):
            if isinstance(e, dict) and e.get("id") == emp_id:
                new_data["id"] = emp_id
                self.data["employers"][i] = new_data
                self.save_data()
                return True
        return False

    def delete_employer(self, emp_id):
        initial_count = len(self.data.get("employers", []))
        self.data["employers"] = [e for e in self.data.get("employers", []) if isinstance(e, dict) and e.get("id") != emp_id]
        if len(self.data["employers"]) < initial_count:
            self.save_data()
            return True
        return False

    def get_workers(self):
        return self.data.get("workers", [])

    def delete_worker(self, worker_uuid):
        initial_count = len(self.data.get("workers", []))
        self.data["workers"] = [w for w in self.data.get("workers", []) if isinstance(w, dict) and w.get("worker_uuid") != worker_uuid]
        if len(self.data["workers"]) < initial_count:
            self.save_data()
            return True
        return False

    def get_suppliers(self):
        return self.data.get("suppliers", [])


    def get_employers(self):
        return self.data.get("employers", [])

    def return_worker(self, worker_uuid, amount=1):
        """Decrements headcount for batch entries or deletes individual entries."""
        for i, w in enumerate(self.data.get("workers", [])):
            if isinstance(w, dict) and w.get("worker_uuid") == worker_uuid:
                if "headcount" in w:
                    try:
                        current = int(w["headcount"])
                        new_val = current - amount
                        if new_val <= 0:
                            self.data["workers"].pop(i)
                        else:
                            w["headcount"] = new_val
                    except:
                        self.data["workers"].pop(i)
                else:
                    # Individual worker return
                    self.data["workers"].pop(i)
                
                self.save_data()
                return True
        return False

=======
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

    def add_supplier(self, supplier):
        """Add ONLY a supplier."""
        s_entry = {"name": supplier["name"], "phone": supplier["phone"]}
        if s_entry not in self.data["suppliers"]:
            self.data["suppliers"].append(s_entry)
            self.save_data()
        return True

    def add_employer(self, employer):
        """Add ONLY an employer."""
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
>>>>>>> 947f1af (update)
