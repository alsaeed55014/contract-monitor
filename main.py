# main.py - Unified Launcher for Streamlit App
import os
import sys
import streamlit.web.cli as stcli

def main():
    port = os.environ.get('PORT', '8501')
    sys.argv = [
        "streamlit", 
        "run", 
        "app.py", 
        "--server.port", port, 
        "--server.address", "0.0.0.0",
        "--server.headless", "true"
    ]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
