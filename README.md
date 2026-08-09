# WhatsApp Automation & Contract Monitor (2026 Edition)

This is a premium WhatsApp automation and candidate matching system built with Streamlit and Selenium.

## 🚀 Local Deployment (Windows)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the App**:
   ```bash
   streamlit run app.py
   ```

## ☁️ Cloud Deployment (GitHub/Streamlit Cloud)

1. **Push to GitHub**:
   - The `.gitignore` file will ensure your private WhatsApp sessions and login credentials are not uploaded.
   - The `requirements.txt` and `packages.txt` files are included for automatic environment setup on Streamlit Cloud.

2. **Streamlit Cloud Setup**:
   - Connect your repository to [Streamlit Cloud](https://share.streamlit.io/).
   - The system will automatically detect and install Chrome via `packages.txt`.

## 🛡️ Anti-Ban Security Features
- **Dynamic User-Agents**: Mimics different browsers.
- **Human-Like Interaction**: Random delays, mouse movements, and typing simulations.
- **Session Persistence**: Keeps you logged in safely across restarts (when using a persistent disk).

---
*Developed for Alsaeed Alwazzan*
