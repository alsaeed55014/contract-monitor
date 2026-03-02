import tkinter as tk
from tkinter import messagebox
from src.config import COLORS, FONTS
from src.ui.components import SmartTable, LuxuryButton, CVModal
from src.data.db_client import DBClient
from src.core.contracts import ContractManager

class MainWindow:
    def __init__(self, root, user_data, on_logout, on_open_search, on_open_perms):
        self.root = root
        self.user = user_data
        self.on_logout = on_logout
        self.on_open_search = on_open_search
        self.on_open_perms = on_open_perms
        
        self.db = DBClient()
        self.root.title("السعيد الوزان - لوحة التحكم")
        self.root.geometry("1400x900")
        self.root.config(bg=COLORS["bg_main"])
        self.root.state('zoomed')

        # Layout
        self.create_sidebar()
        self.create_content()
        self.refresh_data()

    def create_sidebar(self):
        sidebar = tk.Frame(self.root, bg=COLORS["bg_secondary"], width=250)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # User Info
        tk.Label(sidebar, text=f" {self.user.get('full_name_en', 'User')}", 
                 bg=COLORS["bg_secondary"], fg=COLORS["accent"], font=FONTS["body_bold"]).pack(pady=(40, 10))
        
        tk.Frame(sidebar, height=2, bg=COLORS["accent"]).pack(fill=tk.X, padx=20, pady=20)

        # Nav Buttons
        LuxuryButton(sidebar, text=" Dashboard", width=20).pack(pady=5)
        LuxuryButton(sidebar, text=" Smart Search", command=self.on_open_search, width=20, bg=COLORS["bg_main"], fg=COLORS["white"]).pack(pady=5)
        
        if self.user.get("role") == "admin" or self.user.get("can_manage_users"):
            LuxuryButton(sidebar, text=" Permissions", command=self.on_open_perms, width=20, bg=COLORS["bg_main"], fg=COLORS["white"]).pack(pady=5)

        tk.Frame(sidebar, height=2, bg=COLORS["accent"]).pack(fill=tk.X, padx=20, pady=20)
        
        LuxuryButton(sidebar, text=" Refresh", command=self.refresh_data, width=20, bg=COLORS["success"], fg=COLORS["white"]).pack(pady=5)
        LuxuryButton(sidebar, text=" Logout", command=self.on_logout, width=20, bg=COLORS["danger"], fg=COLORS["white"]).pack(pady=5)

    def create_content(self):
        self.content = tk.Frame(self.root, bg=COLORS["bg_main"])
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=30, pady=30)

        # Stats Row
        self.stats_frame = tk.Frame(self.content, bg=COLORS["bg_main"])
        self.stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Section Header
        tk.Label(self.content, text=" Contract Monitor", font=FONTS["h1"], 
                 bg=COLORS["bg_main"], fg=COLORS["white"]).pack(anchor="w")

        # Container for Tables
        self.table_container = tk.Frame(self.content, bg=COLORS["bg_main"])
        self.table_container.pack(fill=tk.BOTH, expand=True)

    def render_stat_card(self, parent, title, value, color):
        f = tk.Frame(parent, bg=COLORS["bg_secondary"], padx=20, pady=20)
        f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(f, text=str(value), font=("Segoe UI", 32, "bold"), fg=color, bg=COLORS["bg_secondary"]).pack()
        tk.Label(f, text=title, font=FONTS["body"], fg=COLORS["text_dim"], bg=COLORS["bg_secondary"]).pack()

    def refresh_data(self):
        df = self.db.fetch_data()
        if df.empty:
            messagebox.showinfo("Info", "No data found or connection failed.")
            return

        # Process Data for Status
        # We need to identifying columns dynamically
        cols = df.columns.tolist()
        date_col = next((c for c in cols if "contract end" in c.lower() or "انتهاء العقد" in c.lower()), None)
        cv_col = next((c for c in cols if "cv" in c.lower() or "سيرة" in c.lower()), None)

        if not date_col:
            messagebox.showerror("Error", "Contract End Date column not found.")
            return

        urgent = []
        expired = []
        active = []

        for _, row in df.iterrows():
            date_val = row[date_col]
            status = ContractManager.calculate_status(date_val)
            
            # Prepare row for table
            # We add a "Status" column at start
            row_data = [status['label_en']] + row.tolist()
            
            item = {
                'values': row_data,
                'cv': row[cv_col] if cv_col else None
            }

            if status['status'] == 'urgent':
                urgent.append(item)
            elif status['status'] == 'expired':
                expired.append(item)
            elif status['status'] == 'active':
                active.append(item)

        # Update Stats
        for widget in self.stats_frame.winfo_children(): widget.destroy()
        self.render_stat_card(self.stats_frame, "Urgent (7 Days)", len(urgent), COLORS["danger"])
        self.render_stat_card(self.stats_frame, "Expired", len(expired), COLORS["text_dim"])
        self.render_stat_card(self.stats_frame, "Active", len(active), COLORS["success"])

        # Update Tables
        for widget in self.table_container.winfo_children(): widget.destroy()

        # Helper to render table section
        def render_section(title, items, color):
            if not items: return
            tk.Label(self.table_container, text=title, font=FONTS["h2"], 
                     bg=COLORS["bg_main"], fg=color).pack(anchor="w", pady=(20, 5))
            
            # Columns
            display_cols = ["Status"] + cols
            
            # Function to handle CV actions
            def handle_action(vals, action):
                # We need to find the CV link. It's in the row values.
                # But 'vals' is just the list of values.
                # We need to find the index of CV col.
                # display_cols has "Status" at index 0. So original headers are at i-1.
                
                # Check where cv_col is in cols
                if cv_col:
                    cv_idx = cols.index(cv_col)
                    # in vals, it is at cv_idx + 1 (because of Status col)
                    link = vals[cv_idx + 1]
                    
                    if not link:
                        messagebox.showinfo("Info", "No CV link available.")
                        return

                    if action == "preview":
                        CVModal(self.root, link)
                    elif action == "download":
                        # reuse modal logic or separate
                        CVModal(self.root, link).download()
                else:
                    messagebox.showinfo("Info", "CV Column not identified.")

            t = SmartTable(self.table_container, display_cols, on_action=handle_action)
            t.pack(fill=tk.BOTH, expand=True, pady=5)
            t.populate([i['values'] for i in items])

        render_section(" Urgent Contracts", urgent, COLORS["danger"])
        render_section(" Expired Contracts", expired, COLORS["text_dim"])
        render_section(" Active Contracts", active, COLORS["success"])
