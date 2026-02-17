import sys
import os

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from src.config import USERS_FILE
from src.core.auth import AuthManager
from src.ui.styles import StyleManager
from src.ui.login import LoginScreen
from src.ui.main_window import MainWindow
from src.ui.search_window import SearchWindow
from src.ui.permissions_window import PermissionsWindow
import ctypes

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw() # Hide root permanently, we use Toplevels
        
        # Windows Tweaks for High DPI
        if os.name == 'nt':
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except: pass

        self.auth_manager = AuthManager(USERS_FILE)
        self.style_manager = StyleManager.setup_styles(self.root)
        
        self.show_login()

    def show_login(self):
        self.login_window = tk.Toplevel(self.root)
        self.login_window.protocol("WM_DELETE_WINDOW", self.exit_app)
        
        # Pass the Toplevel as the 'root' for the LoginScreen logic
        self.login_app = LoginScreen(self.login_window, self.auth_manager, self.on_login_success)

    def on_login_success(self, user_data):
        self.current_user = user_data
        self.login_window.destroy()
        
        self.main_window = tk.Toplevel(self.root)
        self.main_window.protocol("WM_DELETE_WINDOW", self.exit_app)
        
        self.dashboard = MainWindow(self.main_window, 
                                    self.current_user, 
                                    on_logout=self.logout,
                                    on_open_search=self.open_search,
                                    on_open_perms=self.open_perms)

    def open_search(self):
        # Pass main_window as parent
        SearchWindow(self.main_window)

    def open_perms(self):
        # Pass main_window as parent and auth manager
        PermissionsWindow(self.main_window, self.auth_manager)

    def logout(self):
        self.main_window.destroy()
        self.current_user = None
        self.show_login()

    def exit_app(self):
        self.root.destroy()
        sys.exit()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = App()
    app.run()
