import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from src.config import COLORS, FONTS

class LuxuryButton(tk.Button):
    def __init__(self, master, text, command=None, bg=COLORS["accent"], fg=COLORS["black"], width=None):
        super().__init__(master, text=text, command=command, 
                         bg=bg, fg=fg, 
                         font=FONTS["body_bold"], 
                         relief="flat", 
                         cursor="hand2",
                         width=width,
                         activebackground=COLORS["white"],
                         activeforeground=COLORS["black"],
                         bd=0, padx=20, pady=10)
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.default_bg = bg
        self.default_fg = fg

    def on_enter(self, e):
        self.config(bg=COLORS["white"], fg=COLORS["black"])

    def on_leave(self, e):
        self.config(bg=self.default_bg, fg=self.default_fg)

class ModernEntry(tk.Entry):
    def __init__(self, master, show=None, justify='left', placeholder=""):
        super().__init__(master, show=show, justify=justify,
                         font=FONTS["body"],
                         bg="#252525",
                         fg=COLORS["white"],
                         insertbackground=COLORS["accent"],
                         relief="flat",
                         highlightthickness=1,
                         highlightbackground="#444",
                         highlightcolor=COLORS["accent"],
                         bd=0)
        
        self.placeholder = placeholder
        if placeholder:
             self.insert(0, placeholder)
             self.config(fg=COLORS["text_dim"])
             self.bind("<FocusIn>", self._clear_placeholder)
             self.bind("<FocusOut>", self._add_placeholder)

    def _clear_placeholder(self, e):
        if self.get() == self.placeholder:
            self.delete(0, tk.END)
            self.config(fg=COLORS["white"])

    def _add_placeholder(self, e):
        if not self.get():
            self.insert(0, self.placeholder)
            self.config(fg=COLORS["text_dim"])

class CVModal:
    def __init__(self, parent, cv_link, title="CV Preview"):
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.geometry("600x400")
        self.top.config(bg=COLORS["bg_secondary"])
        
        x = parent.winfo_rootx() + 50
        y = parent.winfo_rooty() + 50
        self.top.geometry(f"+{x}+{y}")
        
        tk.Label(self.top, text=" CV Preview", font=FONTS["h2"], 
                 bg=COLORS["bg_secondary"], fg=COLORS["accent"]).pack(pady=20)
        
        tk.Label(self.top, text=f"File: {cv_link[:50]}...", font=FONTS["small"], 
                 bg=COLORS["bg_secondary"], fg=COLORS["text_dim"]).pack(pady=10)

        btn_frame = tk.Frame(self.top, bg=COLORS["bg_secondary"])
        btn_frame.pack(pady=40)
        
        self.cv_link = cv_link
        
        LuxuryButton(btn_frame, text="⬇️ Download", command=self.download).pack(side=tk.LEFT, padx=10)
        LuxuryButton(btn_frame, text=" Open Browser", command=self.open_browser).pack(side=tk.LEFT, padx=10)
        
    def download(self):
        if "drive.google.com" in self.cv_link:
            dl_link = self.cv_link.replace("/view", "export=download").replace("/open", "export=download")
            webbrowser.open(dl_link)
        else:
            webbrowser.open(self.cv_link)

    def open_browser(self):
        webbrowser.open(self.cv_link)

class SmartTable(tk.Frame):
    def __init__(self, master, columns, on_action=None):
        super().__init__(master, bg=COLORS["white"])
        self.columns = columns
        self.on_action = on_action # Callback(row_values, action_type)
        
        self.vsb = ttk.Scrollbar(self, orient="vertical")
        self.hsb = ttk.Scrollbar(self, orient="horizontal")
        
        self.tree = ttk.Treeview(self, 
                                 columns=columns, 
                                 show="headings", 
                                 yscrollcommand=self.vsb.set, 
                                 xscrollcommand=self.hsb.set)
        
        self.vsb.config(command=self.tree.yview)
        self.hsb.config(command=self.tree.xview)
        
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, minwidth=100)
            
        self.tree.bind("<Double-1>", self.on_click)

    def populate(self, rows):
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def get_selected(self):
        sel = self.tree.selection()
        if sel:
            return self.tree.item(sel[0])['values']
        return None

    def on_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            col = self.tree.identify_column(event.x)
            # col is like #1, #2. 
            col_idx = int(col.replace("#", "")) - 1
            
            sel = self.tree.selection()
            if not sel: return
            row_values = self.tree.item(sel[0])['values']
            
            # Identify if column triggers action
            col_name = self.columns[col_idx]
            
            # Check if it's the CV column
            if "CV" in col_name or "سيرة" in col_name:
                # We can trigger a menu or strict action
                # For this implementation, let's open a small popup menu
                m = tk.Menu(self.tree, tearoff=0)
                m.add_command(label="️ Preview CV", command=lambda: self.on_action(row_values, "preview"))
                m.add_command(label="⬇️ Download CV", command=lambda: self.on_action(row_values, "download"))
                m.tk_popup(event.x_root, event.y_root)
