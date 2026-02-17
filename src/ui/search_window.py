import tkinter as tk
from tkinter import ttk, messagebox
from src.config import COLORS, FONTS
from src.ui.components import SmartTable, LuxuryButton, ModernEntry, CVModal
from src.core.search import SmartSearchEngine
from src.data.db_client import DBClient

class SearchWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Smart AI Search")
        self.geometry("1400x900")
        self.config(bg=COLORS["bg_main"])
        self.state('zoomed')
        
        self.db = DBClient()
        self.engine = SmartSearchEngine(self.db.fetch_data())
        
        self.create_header()
        self.create_filters()
        self.create_results_area()

    def create_header(self):
        header = tk.Frame(self, bg=COLORS["bg_secondary"], height=100)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🔍 Advanced Smart Search", font=FONTS["h1"], 
                 bg=COLORS["bg_secondary"], fg=COLORS["white"]).pack(side=tk.LEFT, padx=30, pady=20)
        
        LuxuryButton(header, text="Close", command=self.destroy, bg=COLORS["danger"], width=10).pack(side=tk.RIGHT, padx=30)

    def create_filters(self):
        filter_frame = tk.Frame(self, bg=COLORS["bg_main"], pady=20)
        filter_frame.pack(fill=tk.X, padx=30)
        
        # Search Bar
        tk.Label(filter_frame, text="Smart Search (Name, Job, Nationality, Phone...)", 
                 bg=COLORS["bg_main"], fg=COLORS["text_dim"], font=FONTS["body"]).pack(anchor="w")
        
        self.search_entry = ModernEntry(filter_frame)
        self.search_entry.pack(fill=tk.X, pady=(5, 20), ipady=10)
        self.search_entry.bind('<Return>', self.perform_search)
        
        # Search Button
        LuxuryButton(filter_frame, text="🚀 SEARCH NOW", command=self.perform_search, width=30).pack()

    def create_results_area(self):
        self.results_frame = tk.Frame(self, bg=COLORS["bg_main"])
        self.results_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        self.status_label = tk.Label(self.results_frame, text="Ready to search...", 
                                     bg=COLORS["bg_main"], fg=COLORS["text_dim"], font=FONTS["body"])
        self.status_label.pack(anchor="w", pady=(0, 10))

    def perform_search(self, event=None):
        query = self.search_entry.get()
        if not query:
            return

        self.status_label.config(text="Searching... ⏳")
        self.update_idletasks()
        
        try:
            results_df = self.engine.search(query)
            
            # Clear previous results
            for widget in self.results_frame.winfo_children():
                if isinstance(widget, SmartTable):
                    widget.destroy()

            if results_df.empty:
                self.status_label.config(text="No results found.")
            else:
                self.status_label.config(text=f"Found {len(results_df)} results ✅")
                
                # Render Table
                cols = results_df.columns.tolist()
                
                # Identify CV col for actions
                cv_col = next((c for c in cols if "cv" in c.lower() or "سيرة" in c.lower()), None)
                
                def handle_action(vals, action):
                    if cv_col:
                        idx = cols.index(cv_col)
                        link = vals[idx]
                        if action == "preview":
                             CVModal(self, link)
                        elif action == "download":
                             CVModal(self, link).download()

                table = SmartTable(self.results_frame, cols, on_action=handle_action)
                table.pack(fill=tk.BOTH, expand=True)
                
                # Convert DF to list of lists
                rows = results_df.values.tolist()
                table.populate(rows)

        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            print(e)
