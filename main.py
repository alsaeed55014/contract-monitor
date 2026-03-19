# This file acts as a bridge for Streamlit Cloud
import os
import subprocess
import sys

# Check if running in Streamlit environment
if 'STREAMLIT_SERVER_PORT' in os.environ or "/mount/src/" in os.path.abspath(__file__):
    # This is Streamlit Cloud, redirect to app.py
    import streamlit.web.cli as stcli
    if __name__ == "__main__":
        sys.argv = ["streamlit", "run", "app.py", "--server.port", os.environ.get('PORT', '8501'), "--server.address", "0.0.0.0"]
        sys.exit(stcli.main())
else:
    # This is LOCAL environment, run original Tkinter app
    import tkinter as tk
    from src.config import USERS_FILE
    from src.core.auth import AuthManager
    from src.ui.styles import StyleManager
    from src.ui.login import LoginScreen
    from src.ui.main_window import MainWindow

    class App:
        def __init__(self):
            self.root = tk.Tk()
            self.root.withdraw()
            self.auth_manager = AuthManager(USERS_FILE)
            StyleManager.setup_styles(self.root)
            self.start_notification_service()
            self.show_login()

        def start_notification_service(self):
            """Starts the notification service if not already running."""
            try:
                # Check if process is already running using wmic to see command line
                if os.name == 'nt':
                    cmd = 'wmic process where "name=\'python.exe\'" get CommandLine'
                    output = subprocess.check_output(cmd, shell=True).decode(errors='ignore')
                    if "antigravity_notification.py" not in output:
                        # Start it in background
                        script_path = os.path.abspath("antigravity_notification.py")
                        # Use pythonw if available to avoid console window, or use CREATE_NO_WINDOW
                        subprocess.Popen([sys.executable, script_path], 
                                       creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                                       close_fds=True)
            except Exception as e:
                print(f"Failed to start notification service: {e}")

        def show_login(self):
            self.login_window = tk.Toplevel(self.root)
            LoginScreen(self.login_window, self.auth_manager, self.on_login_success)

        def on_login_success(self, user_data):
            self.login_window.destroy()
            self.main_window = tk.Toplevel(self.root)
            MainWindow(self.main_window, user_data)

        def run(self):
            self.root.mainloop()

    if __name__ == "__main__":
        app = App()
        app.run()
